"""THỰC NGHIỆM: so sánh 4 cấu hình trên tất cả module trong targets/.

    A: Baseline — sinh test một lần
    B: Agent + phản hồi coverage
    C: Agent + coverage + mutation
    D: C + bộ nhớ tự học

Thực nghiệm gồm 2 BƯỚC TÁCH RIÊNG:

1) SINH (gọi LLM, tốn request) — chạy agent cấu hình C và D, mỗi lần chạy lưu một log JSON trong logs/
   (tên có nhãn eval_C / eval_D). Thiết kế "ghép cặp" để tiết kiệm lần gọi LLM:
     - A = bộ test ban đầu của lần chạy C (cùng prompt, cùng một lần gọi LLM)        -> snapshot "initial"
     - B = trạng thái của C đúng lúc phase coverage kết thúc (B sẽ dừng đúng ở đó)  -> snapshot "coverage_done"
   D chạy riêng: bộ nhớ bắt đầu RỖNG ở mỗi lần lặp, các module chạy lần lượt để bộ nhớ tích luỹ dần.
   Lần chạy bị dừng vì lỗi LLM (hết quota, mất mạng) KHÔNG được tính -> lần sau chạy lại.
   => Chạy lại lệnh sẽ chỉ chạy phần còn thiếu (chạy tiếp được qua nhiều ngày khi bị giới hạn request).

2) CHẤM (không gọi LLM) — đọc log, chấm lại MỌI cấu hình bằng cùng một thước đo:
     - line/branch coverage (runner)
     - mutation score trên các mutant mà LLM CHƯA TỪNG THẤY trong prompt của C/D ("held-out",
       giống tách tập train/test trong học máy) -> không bị thổi phồng vì agent đã được "mớm" đúng các mutant đó.
       Cột mutation_all: điểm trên mọi mutant (để so sánh, thấy mức chênh).
     - phát hiện bug: có test FAIL/SUSPECTED trên code có bug nhưng PASS trên bản đã sửa (evaluation/fixed_targets)
   Kết quả: results/runs.csv (từng lần), results/results.csv (trung bình theo cấu hình), biểu đồ PNG.

Ví dụ:
    python evaluate.py --quick                 # thử nhanh: module grading, 1 lần
    python evaluate.py --runs 3                # đầy đủ: 5 module x 3 lần (tiếp tục phần còn thiếu)
    python evaluate.py --measure-only          # không gọi LLM: chỉ chấm lại từ log + vẽ biểu đồ
    python evaluate.py --reset --runs 3        # làm lại từ đầu (log cũ được chuyển vào logs/archive_*)
"""
import argparse
import csv
import json
import re
import shutil
import time
from pathlib import Path

import testgen  # noqa: F401  (cấu hình UTF-8 cho console Windows)
from testgen import code_utils as cu
from testgen.agent import LOGS_DIR, AgentConfig, TestGenAgent
from testgen.config import ROOT_DIR
from testgen.llm_client import LLMClient
from testgen.memory import Memory
from testgen.mutation import run_mutation_testing
from testgen.runner import run_tests

TARGETS_DIR = ROOT_DIR / "targets"
FIXED_DIR = ROOT_DIR / "evaluation" / "fixed_targets"
RESULTS_DIR = ROOT_DIR / "results"
MODULES = ["calculator", "text_utils", "grading", "safe_parser", "shopping_cart"]  # dễ -> khó
CONFIG_NAMES = {
    "A": "A: Baseline",
    "B": "B: Agent + coverage",
    "C": "C: B + mutation",
    "D": "D: C + memory",
}
FIELDS = ["config", "module", "run", "line_coverage", "branch_coverage", "mutation_score", "mutation_all",
          "mutants_heldout", "iterations", "llm_calls", "seconds", "cost_usd", "tests_total", "tests_failing",
          "suspected", "suspected_tp", "suspected_fp", "has_bug", "bug_detected", "stop_reason",
          "provider", "model", "log"]


# ============================================================================ BƯỚC 1: SINH
def eval_logs(module: str, label: str) -> list:
    """Các log hợp lệ (không bị dừng vì lỗi LLM) của một module + cấu hình, xếp theo thời gian."""
    logs = []
    for path in sorted(LOGS_DIR.glob(f"{module}_{label}_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data["stop_reason"].startswith("Lỗi gọi LLM"):
            logs.append(path)
    return logs


def generate(args):
    for run in range(1, args.runs + 1):
        memory = Memory(RESULTS_DIR / "memory" / f"memory_run{run}.json")  # bộ nhớ riêng cho mỗi lần lặp
        for module in args.modules:
            path = TARGETS_DIR / f"{module}.py"
            for label, use_memory in (("eval_C", False), ("eval_D", True)):
                if len(eval_logs(module, label)) >= run:
                    continue  # đã có log hợp lệ cho lần chạy này
                print(f"\n===== Lần {run} | {module} | {label} =====", flush=True)
                config = AgentConfig(max_iterations=args.max_iters, use_mutation=True, use_memory=use_memory,
                                     max_mutants=args.max_mutants, label=label)
                summary = TestGenAgent(path, LLMClient(), config, memory=memory if use_memory else None).run()
                if summary["stop_reason"].startswith("Lỗi gọi LLM"):
                    print("  !! Lỗi gọi LLM -> lần chạy này không được tính, hãy chạy lại lệnh sau.")
                    return


# ============================================================================ BƯỚC 2: CHẤM
def shown_mutants(log: dict) -> set:
    """Id các mutant đã được đưa vào prompt cho LLM trong một lần chạy."""
    ids = set()
    for it in log["iterations"]:
        if it["action"] != "kill_mutants":
            continue
        if "shown_mutant_ids" in it:
            ids.update(it["shown_mutant_ids"])
        else:  # log cũ: prompt chứa 6 mutant sống đầu tiên
            for text in it["survived_mutants"][:6]:
                match = re.search(r"Mutant #(\d+)", text)
                if match:
                    ids.add(int(match.group(1)))
    return ids


def measure(module: str, test_code: str, exclude: set, measure_mutants: int) -> dict:
    """Chấm một bộ test bằng cùng một thước đo cho mọi cấu hình."""
    module_path = TARGETS_DIR / f"{module}.py"
    fixed_path = FIXED_DIR / f"{module}.py"
    res = run_tests(module_path, test_code)
    held = run_mutation_testing(module_path, test_code, max_mutants=measure_mutants, seed=0,
                                skip_failing=True, exclude_ids=exclude)
    full = run_mutation_testing(module_path, test_code, max_mutants=measure_mutants, seed=0, skip_failing=True)

    has_bug = module_path.read_text(encoding="utf-8") != fixed_path.read_text(encoding="utf-8")
    outcomes_buggy = {t.name: t.outcome for t in res.tests}
    outcomes_fixed = {t.name: t.outcome for t in run_tests(fixed_path, test_code, with_coverage=False).tests}
    # Test "bắt được bug": fail (hoặc bị gắn nhãn nghi bug) trên code lỗi, nhưng pass trên code đúng
    catching = {cu.base_test_name(n) for n, o in outcomes_buggy.items()
                if o in ("failed", "error", "xfailed") and outcomes_fixed.get(n) == "passed"}
    suspected = cu.suspected_tests(test_code)
    suspected_tp = [n for n in suspected if n in catching]
    return {
        "line_coverage": 0.0 if res.collection_error else res.line_coverage,
        "branch_coverage": 0.0 if res.collection_error else res.branch_coverage,
        "mutation_score": 0.0 if held.error else held.score,
        "mutation_all": 0.0 if full.error else full.score,
        "mutants_heldout": held.total,
        "tests_total": res.total,
        "tests_failing": res.failed + res.errors,
        "suspected": len(suspected),
        "suspected_tp": len(suspected_tp),
        "suspected_fp": len(suspected) - len(suspected_tp),
        "has_bug": int(has_bug),
        "bug_detected": int(has_bug and bool(catching)),
    }


def measure_all(args) -> list:
    """Chấm MỌI log thực nghiệm đang có (của mọi module), không phụ thuộc lần sinh vừa rồi."""
    rows = []
    for module in MODULES:
        logs_c, logs_d = eval_logs(module, "eval_C"), eval_logs(module, "eval_D")
        for run in range(1, max(len(logs_c), len(logs_d)) + 1):
            c = json.loads(logs_c[run - 1].read_text(encoding="utf-8")) if run <= len(logs_c) else None
            d = json.loads(logs_d[run - 1].read_text(encoding="utf-8")) if run <= len(logs_d) else None
            # Loại khỏi tập chấm mọi mutant C hoặc D đã thấy -> 4 cấu hình được chấm trên CÙNG một tập mutant
            exclude = (shown_mutants(c) if c else set()) | (shown_mutants(d) if d else set())
            print(f"Chấm {module} lần {run} (loại {len(exclude)} mutant LLM đã thấy)...", flush=True)
            jobs = []
            if c:
                snaps = c.get("snapshots", {})
                final_c = {"code": c["final_test_code"], "iterations": c["final"]["num_iterations"],
                           "llm_calls": c["stats"]["llm_calls"], "seconds": c["stats"]["total_seconds"],
                           "cost_usd": c["stats"]["cost_usd"]}
                initial = snaps.get("initial", final_c)
                cov_done = snaps.get("coverage_done", final_c)
                jobs += [("A", initial, "sinh một lần", c, logs_c[run - 1]),
                         ("B", cov_done, "hết phase coverage" if "coverage_done" in snaps else c["stop_reason"],
                          c, logs_c[run - 1]),
                         ("C", final_c, c["stop_reason"], c, logs_c[run - 1])]
            if d:
                final_d = {"code": d["final_test_code"], "iterations": d["final"]["num_iterations"],
                           "llm_calls": d["stats"]["llm_calls"], "seconds": d["stats"]["total_seconds"],
                           "cost_usd": d["stats"]["cost_usd"]}
                jobs.append(("D", final_d, d["stop_reason"], d, logs_d[run - 1]))
            for config, state, reason, log, log_path in jobs:
                row = {"config": config, "module": module, "run": run,
                       **measure(module, state["code"], exclude, args.measure_mutants),
                       "iterations": state["iterations"], "llm_calls": state["llm_calls"],
                       "seconds": state["seconds"], "cost_usd": state["cost_usd"], "stop_reason": reason,
                       "provider": log["llm"]["provider"], "model": log["llm"]["model"], "log": log_path.name}
                rows.append(row)
                print(f"  {config}: line {row['line_coverage']}% branch {row['branch_coverage']}% | mutation "
                      f"held-out {row['mutation_score']}% (tất cả {row['mutation_all']}%) | LLM {row['llm_calls']} "
                      f"lần | bug {row['bug_detected']} | nghi bug {row['suspected']} (đúng {row['suspected_tp']})",
                      flush=True)
    return rows


# ============================================================================ TỔNG HỢP & BIỂU ĐỒ
def mean(values):
    values = [float(v) for v in values]
    return round(sum(values) / len(values), 2) if values else 0.0


def summarize(rows: list) -> list:
    """Trung bình theo cấu hình (trên mọi module và mọi lần chạy)."""
    summary = []
    for config in CONFIG_NAMES:
        group = [r for r in rows if r["config"] == config]
        if not group:
            continue
        bug_rows = [r for r in group if int(r["has_bug"]) == 1]
        summary.append({
            "config": CONFIG_NAMES[config],
            "n_rows": len(group),
            "n_runs": len({r["run"] for r in group}),
            "line_coverage": mean(r["line_coverage"] for r in group),
            "branch_coverage": mean(r["branch_coverage"] for r in group),
            "mutation_score": mean(r["mutation_score"] for r in group),
            "mutation_all": mean(r["mutation_all"] for r in group),
            "iterations": mean(r["iterations"] for r in group),
            "llm_calls": mean(r["llm_calls"] for r in group),
            "seconds": mean(r["seconds"] for r in group),
            "cost_usd": mean(r["cost_usd"] for r in group),
            "tests_total": mean(r["tests_total"] for r in group),
            "tests_failing": mean(r["tests_failing"] for r in group),
            "suspected_tp": sum(int(r["suspected_tp"]) for r in group),
            "suspected_fp": sum(int(r["suspected_fp"]) for r in group),
            "bug_detection_rate": round(mean(r["bug_detected"] for r in bug_rows) * 100, 1) if bug_rows else 0.0,
            # Bug được agent GẮN NHÃN đúng (có test SUSPECTED_BUG pass trên bản sửa) — không chỉ "có test fail"
            "bug_flagged_rate": round(mean(int(r["suspected_tp"]) > 0 for r in bug_rows) * 100, 1) if bug_rows else 0.0,
        })
    return summary


def summarize_by_module(rows: list) -> list:
    out = []
    for module in MODULES:
        for config in CONFIG_NAMES:
            group = [r for r in rows if r["config"] == config and r["module"] == module]
            if group:
                out.append({"module": module, "config": config, "n_runs": len(group),
                            "line_coverage": mean(r["line_coverage"] for r in group),
                            "branch_coverage": mean(r["branch_coverage"] for r in group),
                            "mutation_score": mean(r["mutation_score"] for r in group),
                            "mutation_all": mean(r["mutation_all"] for r in group),
                            "llm_calls": mean(r["llm_calls"] for r in group),
                            "bug_detected": mean(r["bug_detected"] for r in group)})
    return out


def write_csv(path: Path, rows: list, fields=None):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(summary: list, by_module: list):
    """Vẽ biểu đồ PNG (matplotlib) vào results/."""
    import matplotlib
    matplotlib.use("Agg")  # vẽ ra file, không cần cửa sổ
    import matplotlib.pyplot as plt

    labels = [s["config"].split(":")[0] for s in summary]
    palette = {"A": "#9aa5b1", "B": "#4c8bf5", "C": "#f5a524", "D": "#2bb673"}
    colors = [palette[label] for label in labels]
    xs = list(range(len(summary)))
    width = 0.38

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    ax = axes[0][0]
    ax.bar([x - width / 2 for x in xs], [s["line_coverage"] for s in summary], width, label="Line", color="#4c8bf5")
    ax.bar([x + width / 2 for x in xs], [s["branch_coverage"] for s in summary], width, label="Branch",
           color="#f5a524")
    ax.set_xticks(xs, labels)
    ax.set_ylim(0, 110)
    ax.set_title("Coverage trung bình (%)")
    ax.legend(loc="lower right")

    ax = axes[0][1]
    ax.bar([x - width / 2 for x in xs], [s["mutation_score"] for s in summary], width, color=colors,
           label="Mutant LLM chưa thấy (held-out)")
    ax.bar([x + width / 2 for x in xs], [s["mutation_all"] for s in summary], width, color=colors, alpha=0.45,
           hatch="//", label="Tất cả mutant")
    ax.set_xticks(xs, labels)
    ax.set_ylim(0, 110)
    ax.set_title("Mutation score trung bình (%)")
    ax.legend(loc="lower right", fontsize=8)

    ax = axes[1][0]
    ax.bar(labels, [s["llm_calls"] for s in summary], color=colors)
    ax.set_title("Số lần gọi LLM trung bình / module (cột)\nThời gian trung bình, giây (đường)")
    ax2 = ax.twinx()
    ax2.plot(labels, [s["seconds"] for s in summary], "ko--")
    ax2.set_ylim(0, max(s["seconds"] for s in summary) * 1.3 + 1)

    ax = axes[1][1]
    ax.bar([x - width / 2 for x in xs], [s["bug_detection_rate"] for s in summary], width, color=colors,
           alpha=0.45, hatch="//", label="Có test fail do bug")
    ax.bar([x + width / 2 for x in xs], [s["bug_flagged_rate"] for s in summary], width, color=colors,
           label="Được gắn nhãn SUSPECTED_BUG đúng")
    ax.set_xticks(xs, labels)
    ax.set_ylim(0, 110)
    ax.set_title("Bug cài sẵn (%)")
    ax.legend(loc="lower right", fontsize=8)

    for a in axes.flat:
        for bar in a.patches:
            h = bar.get_height()
            a.annotate(f"{h:.0f}" if h >= 10 else f"{h:.1f}", (bar.get_x() + bar.get_width() / 2, h),
                       ha="center", va="bottom", fontsize=8)
    n_runs = max(s["n_runs"] for s in summary)
    n_modules = len({r["module"] for r in by_module})
    fig.suptitle(f"So sánh 4 cấu hình — {n_modules} module × {n_runs} lần chạy")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "summary.png", dpi=130)
    plt.close(fig)

    # Mutation score (held-out) theo từng module
    modules = [m for m in MODULES if any(r["module"] == m for r in by_module)]
    configs = [c for c in CONFIG_NAMES if any(r["config"] == c for r in by_module)]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    w = 0.8 / max(1, len(configs))
    for i, config in enumerate(configs):
        values = [next((r["mutation_score"] for r in by_module if r["module"] == m and r["config"] == config), 0)
                  for m in modules]
        ax.bar([x + i * w for x in range(len(modules))], values, w, label=CONFIG_NAMES[config],
               color=palette[config])
    ax.set_xticks([x + w * (len(configs) - 1) / 2 for x in range(len(modules))], modules)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Mutation score held-out (%)")
    ax.set_title("Mutation score theo module (trên mutant LLM chưa thấy)")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "mutation_by_module.png", dpi=130)
    plt.close(fig)


def report(rows: list):
    if not rows:
        print("Chưa có log thực nghiệm (logs/*_eval_C_*.json). Hãy chạy: python evaluate.py --quick")
        return
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary, by_module = summarize(rows), summarize_by_module(rows)
    write_csv(RESULTS_DIR / "runs.csv", rows, FIELDS)
    write_csv(RESULTS_DIR / "results.csv", summary)
    write_csv(RESULTS_DIR / "results_by_module.csv", by_module)
    plot(summary, by_module)
    print("\n===== TỔNG HỢP (results/results.csv) =====")
    for s in summary:
        print(json.dumps(s, ensure_ascii=False))
    print("Biểu đồ: results/summary.png, results/mutation_by_module.png")


def reset():
    """Làm lại từ đầu: chuyển log thực nghiệm cũ vào logs/archive_<thời gian>/, xoá bộ nhớ và kết quả cũ."""
    archive = LOGS_DIR / time.strftime("archive_%Y%m%d-%H%M%S")
    for path in LOGS_DIR.glob("*_eval_*.json"):
        archive.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), archive / path.name)
    shutil.rmtree(RESULTS_DIR / "memory", ignore_errors=True)
    for name in ("runs.csv", "results.csv", "results_by_module.csv"):
        (RESULTS_DIR / name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Thực nghiệm so sánh 4 cấu hình A/B/C/D")
    parser.add_argument("--modules", nargs="+", default=MODULES, choices=MODULES)
    parser.add_argument("--runs", type=int, default=3, help="số lần lặp mỗi cấu hình")
    parser.add_argument("--max-iters", type=int, default=6)
    parser.add_argument("--max-mutants", type=int, default=20, help="số mutant agent dùng trong vòng lặp")
    parser.add_argument("--measure-mutants", type=int, default=40, help="số mutant tối đa dùng để CHẤM")
    parser.add_argument("--quick", action="store_true", help="thử nhanh: chỉ module grading, 1 lần")
    parser.add_argument("--measure-only", action="store_true", help="không gọi LLM, chỉ chấm lại từ log")
    parser.add_argument("--reset", action="store_true", help="làm lại từ đầu (lưu trữ log thực nghiệm cũ)")
    args = parser.parse_args()

    if args.quick:
        args.modules, args.runs = ["grading"], 1
    if args.reset:
        reset()
    if not args.measure_only:
        generate(args)
    report(measure_all(args))


if __name__ == "__main__":
    main()
