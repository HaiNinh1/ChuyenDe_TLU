"""THỰC NGHIỆM: so sánh 4 cấu hình trên tất cả module trong targets/.

    A: Baseline — sinh test một lần
    B: Agent + phản hồi coverage
    C: Agent + coverage + mutation
    D: C + bộ nhớ tự học

Thiết kế "ghép cặp" (mặc định) để tiết kiệm lần gọi LLM:
    Mỗi lần chạy C sinh ra luôn kết quả của A và B, vì:
    - A = bộ test ban đầu của C (cùng prompt, cùng một lần gọi LLM)          -> snapshot "initial"
    - B = trạng thái của C ngay khi phase coverage kết thúc (B sẽ dừng ở đó) -> snapshot "coverage_done"
    D chạy riêng: bộ nhớ bắt đầu RỖNG ở mỗi lần lặp, các module chạy lần lượt để bộ nhớ tích luỹ dần.
    Dùng --independent để chạy A, B, C tách biệt (tốn gấp ~2 lần gọi LLM).

Mọi cấu hình được CHẤM LẠI giống nhau sau khi chạy (công bằng):
    - line/branch coverage (runner)
    - mutation score trên CÙNG tập mutant (seed cố định, tối đa --measure-mutants mutant; bỏ qua test đang fail)
    - phát hiện bug: có test FAIL/SUSPECTED trên code có bug nhưng PASS trên bản đã sửa (evaluation/fixed_targets)

Kết quả được GHI NỐI TIẾP vào results/runs.csv -> chạy lại lệnh sẽ bỏ qua những gì đã có (chạy tiếp được qua
nhiều ngày nếu bị giới hạn số request). Sau đó tổng hợp ra results/results.csv và các biểu đồ PNG.

Ví dụ:
    python evaluate.py --quick                     # thử nhanh: 1 module, 1 lần
    python evaluate.py --runs 3                    # đầy đủ: 5 module x 3 lần
    python evaluate.py --modules grading text_utils --runs 1
    python evaluate.py --report-only               # chỉ tổng hợp + vẽ lại biểu đồ từ runs.csv
"""
import argparse
import csv
import json
import time
from pathlib import Path

import testgen  # noqa: F401  (cấu hình UTF-8 cho console Windows)
from testgen import code_utils as cu
from testgen.agent import AgentConfig, TestGenAgent
from testgen.config import ROOT_DIR
from testgen.generator import generate_tests
from testgen.llm_client import LLMClient
from testgen.memory import Memory
from testgen.mutation import run_mutation_testing
from testgen.runner import run_tests

TARGETS_DIR = ROOT_DIR / "targets"
FIXED_DIR = ROOT_DIR / "evaluation" / "fixed_targets"
RESULTS_DIR = ROOT_DIR / "results"
RUNS_CSV = RESULTS_DIR / "runs.csv"
MODULES = ["calculator", "text_utils", "grading", "safe_parser", "shopping_cart"]  # dễ -> khó
CONFIG_NAMES = {
    "A": "A: Baseline",
    "B": "B: Agent + coverage",
    "C": "C: B + mutation",
    "D": "D: C + memory",
}

FIELDS = ["config", "module", "run", "line_coverage", "branch_coverage", "mutation_score", "iterations",
          "llm_calls", "seconds", "cost_usd", "tests_total", "tests_failing", "suspected", "suspected_tp",
          "suspected_fp", "has_bug", "bug_detected", "stop_reason", "provider", "model", "timestamp"]


# ---------------------------------------------------------------------------- CHẤM ĐIỂM
def measure(module: str, test_code: str, measure_mutants: int) -> dict:
    """Chấm một bộ test bằng cùng một thước đo cho mọi cấu hình."""
    module_path = TARGETS_DIR / f"{module}.py"
    fixed_path = FIXED_DIR / f"{module}.py"
    res = run_tests(module_path, test_code)
    mres = run_mutation_testing(module_path, test_code, max_mutants=measure_mutants, seed=0, skip_failing=True)

    has_bug = module_path.read_text(encoding="utf-8") != fixed_path.read_text(encoding="utf-8")
    outcomes_buggy = {t.name: t.outcome for t in res.tests}
    outcomes_fixed = {t.name: t.outcome for t in run_tests(fixed_path, test_code, with_coverage=False).tests}
    # Test "bắt được bug": fail (hoặc bị gắn nhãn nghi bug) trên code lỗi, nhưng pass trên code đúng
    catching = [n for n, o in outcomes_buggy.items()
                if o in ("failed", "error", "xfailed") and outcomes_fixed.get(n) == "passed"]
    suspected = cu.suspected_tests(test_code)
    suspected_tp = [n for n in suspected
                    if any(cu.base_test_name(c) == n for c in catching)]
    return {
        "line_coverage": res.line_coverage if not res.collection_error else 0.0,
        "branch_coverage": res.branch_coverage if not res.collection_error else 0.0,
        "mutation_score": mres.score if not mres.error else 0.0,
        "tests_total": res.total,
        "tests_failing": res.failed + res.errors,
        "suspected": len(suspected),
        "suspected_tp": len(suspected_tp),
        "suspected_fp": len(suspected) - len(suspected_tp),
        "has_bug": int(has_bug),
        "bug_detected": int(has_bug and bool(catching)),
    }


def make_row(config, module, run, test_code, info, stop_reason, client, measure_mutants):
    row = {"config": config, "module": module, "run": run, **measure(module, test_code, measure_mutants)}
    row.update({
        "iterations": info.get("iterations", 0), "llm_calls": info.get("llm_calls", 0),
        "seconds": info.get("seconds", 0), "cost_usd": info.get("cost_usd", 0), "stop_reason": stop_reason,
        "provider": client.settings.provider, "model": client.settings.model,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    return row


def final_info(summary: dict) -> dict:
    return {"iterations": summary["final"]["num_iterations"], "llm_calls": summary["stats"]["llm_calls"],
            "seconds": summary["stats"]["total_seconds"], "cost_usd": summary["stats"]["cost_usd"]}


# ---------------------------------------------------------------------------- CHẠY
def agent_config(label, args, mutation, memory) -> AgentConfig:
    return AgentConfig(max_iterations=args.max_iters, use_mutation=mutation, use_memory=memory,
                       max_mutants=args.max_mutants, label=label)


def run_experiment(args):
    done = {(r["config"], r["module"], int(r["run"])) for r in read_rows()}
    for run in range(1, args.runs + 1):
        memory = Memory(RESULTS_DIR / "memory" / f"memory_run{run}.json")  # bộ nhớ riêng cho mỗi lần lặp
        for module in args.modules:
            path = TARGETS_DIR / f"{module}.py"
            todo = [c for c in args.configs if (c, module, run) not in done]
            if not todo:
                continue
            print(f"\n===== Lần {run} | module {module} | cấu hình cần chạy: {todo} =====")

            if args.independent:
                if "A" in todo:
                    client = LLMClient()
                    start = time.time()
                    code = generate_tests(path, client)
                    info = {"iterations": 0, "llm_calls": client.call_count,
                            "seconds": round(time.time() - start, 1), "cost_usd": client.stats()["cost_usd"]}
                    save(make_row("A", module, run, code, info, "sinh một lần", client, args.measure_mutants))
                if "B" in todo:
                    client = LLMClient()
                    s = TestGenAgent(path, client, agent_config("eval_B", args, False, False)).run()
                    save(make_row("B", module, run, s["final_test_code"], final_info(s), s["stop_reason"],
                                  client, args.measure_mutants))
                if "C" in todo:
                    client = LLMClient()
                    s = TestGenAgent(path, client, agent_config("eval_C", args, True, False)).run()
                    save(make_row("C", module, run, s["final_test_code"], final_info(s), s["stop_reason"],
                                  client, args.measure_mutants))
            elif {"A", "B", "C"} & set(todo):
                # Một lần chạy C -> suy ra A và B từ các snapshot
                client = LLMClient()
                s = TestGenAgent(path, client, agent_config("eval_C", args, True, False)).run()
                snaps = s.get("snapshots", {})
                final_state = {"code": s["final_test_code"], **final_info(s)}
                initial = snaps.get("initial", final_state)
                cov_done = snaps.get("coverage_done", final_state)
                if "A" in todo:
                    save(make_row("A", module, run, initial["code"], initial, "sinh một lần", client,
                                  args.measure_mutants))
                if "B" in todo:
                    reason = "hết phase coverage" if "coverage_done" in snaps else s["stop_reason"]
                    save(make_row("B", module, run, cov_done["code"], cov_done, reason, client, args.measure_mutants))
                if "C" in todo:
                    save(make_row("C", module, run, s["final_test_code"], final_info(s), s["stop_reason"],
                                  client, args.measure_mutants))

            if "D" in todo:
                client = LLMClient()
                s = TestGenAgent(path, client, agent_config("eval_D", args, True, True), memory=memory).run()
                save(make_row("D", module, run, s["final_test_code"], final_info(s), s["stop_reason"],
                              client, args.measure_mutants))


# ---------------------------------------------------------------------------- LƯU & TỔNG HỢP
def read_rows() -> list:
    if not RUNS_CSV.exists():
        return []
    with RUNS_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save(row: dict):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not RUNS_CSV.exists()
    with RUNS_CSV.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDS})
    print(f"  -> {row['config']} | {row['module']} | line {row['line_coverage']}% branch {row['branch_coverage']}% "
          f"mutation {row['mutation_score']}% | LLM {row['llm_calls']} lần | bug {row['bug_detected']} "
          f"| nghi bug {row['suspected']} (đúng {row['suspected_tp']})")


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
        bug_rows = [r for r in group if r["has_bug"] == "1"]
        summary.append({
            "config": CONFIG_NAMES[config],
            "n_runs": len(group),
            "line_coverage": mean(r["line_coverage"] for r in group),
            "branch_coverage": mean(r["branch_coverage"] for r in group),
            "mutation_score": mean(r["mutation_score"] for r in group),
            "iterations": mean(r["iterations"] for r in group),
            "llm_calls": mean(r["llm_calls"] for r in group),
            "seconds": mean(r["seconds"] for r in group),
            "cost_usd": mean(r["cost_usd"] for r in group),
            "tests_failing": mean(r["tests_failing"] for r in group),
            "suspected_tp": sum(int(r["suspected_tp"]) for r in group),
            "suspected_fp": sum(int(r["suspected_fp"]) for r in group),
            "bug_detection_rate": mean(r["bug_detected"] for r in bug_rows) * 100 if bug_rows else 0.0,
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
                            "llm_calls": mean(r["llm_calls"] for r in group),
                            "bug_detected": mean(r["bug_detected"] for r in group)})
    return out


def write_csv(path: Path, rows: list):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(summary: list, by_module: list):
    """Vẽ biểu đồ PNG (matplotlib) vào results/."""
    import matplotlib
    matplotlib.use("Agg")  # vẽ ra file, không cần cửa sổ
    import matplotlib.pyplot as plt

    labels = [s["config"].split(":")[0] for s in summary]
    colors = ["#9aa5b1", "#4c8bf5", "#f5a524", "#2bb673"][:len(summary)]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    ax = axes[0][0]
    width = 0.38
    xs = range(len(summary))
    ax.bar([x - width / 2 for x in xs], [s["line_coverage"] for s in summary], width, label="Line", color="#4c8bf5")
    ax.bar([x + width / 2 for x in xs], [s["branch_coverage"] for s in summary], width, label="Branch", color="#f5a524")
    ax.set_xticks(list(xs), labels)
    ax.set_ylim(0, 105)
    ax.set_title("Coverage trung bình (%)")
    ax.legend(loc="lower right")

    ax = axes[0][1]
    ax.bar(labels, [s["mutation_score"] for s in summary], color=colors)
    ax.set_ylim(0, 105)
    ax.set_title("Mutation score trung bình (%)")

    ax = axes[1][0]
    ax.bar(labels, [s["llm_calls"] for s in summary], color=colors)
    ax.set_title("Số lần gọi LLM trung bình / module")
    ax2 = ax.twinx()
    ax2.plot(labels, [s["seconds"] for s in summary], "ko--", label="Thời gian (s)")
    ax2.set_ylabel("giây")
    ax2.legend(loc="upper left")

    ax = axes[1][1]
    ax.bar(labels, [s["bug_detection_rate"] for s in summary], color=colors)
    ax.set_ylim(0, 105)
    ax.set_title("Tỉ lệ phát hiện bug cài sẵn (%)")

    for a in axes.flat:
        for bar in a.patches:
            a.annotate(f"{bar.get_height():.0f}" if bar.get_height() >= 10 else f"{bar.get_height():.1f}",
                       (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                       ha="center", va="bottom", fontsize=8)
    n = summary[0]["n_runs"] if summary else 0
    fig.suptitle(f"So sánh 4 cấu hình (mỗi cấu hình {n} lượt module×lần chạy)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "summary.png", dpi=130)
    plt.close(fig)

    # Mutation score theo từng module
    modules = [m for m in MODULES if any(r["module"] == m for r in by_module)]
    configs = [c for c in CONFIG_NAMES if any(r["config"] == c for r in by_module)]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    width = 0.8 / max(1, len(configs))
    for i, config in enumerate(configs):
        values = [next((r["mutation_score"] for r in by_module if r["module"] == m and r["config"] == config), 0)
                  for m in modules]
        ax.bar([x + i * width for x in range(len(modules))], values, width, label=CONFIG_NAMES[config],
               color=["#9aa5b1", "#4c8bf5", "#f5a524", "#2bb673"][i % 4])
    ax.set_xticks([x + width * (len(configs) - 1) / 2 for x in range(len(modules))], modules)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Mutation score (%)")
    ax.set_title("Mutation score theo module")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "mutation_by_module.png", dpi=130)
    plt.close(fig)


def report():
    rows = read_rows()
    if not rows:
        print("Chưa có dữ liệu trong results/runs.csv")
        return
    summary, by_module = summarize(rows), summarize_by_module(rows)
    write_csv(RESULTS_DIR / "results.csv", summary)
    write_csv(RESULTS_DIR / "results_by_module.csv", by_module)
    plot(summary, by_module)
    print("\n===== TỔNG HỢP (results/results.csv) =====")
    for s in summary:
        print(json.dumps(s, ensure_ascii=False))
    print("Biểu đồ: results/summary.png, results/mutation_by_module.png")


def main():
    parser = argparse.ArgumentParser(description="Thực nghiệm so sánh 4 cấu hình A/B/C/D")
    parser.add_argument("--modules", nargs="+", default=MODULES, choices=MODULES)
    parser.add_argument("--configs", nargs="+", default=list(CONFIG_NAMES), choices=list(CONFIG_NAMES))
    parser.add_argument("--runs", type=int, default=3, help="số lần lặp mỗi cấu hình")
    parser.add_argument("--max-iters", type=int, default=6)
    parser.add_argument("--max-mutants", type=int, default=20, help="số mutant agent dùng trong vòng lặp")
    parser.add_argument("--measure-mutants", type=int, default=30, help="số mutant dùng để CHẤM (cố định seed)")
    parser.add_argument("--independent", action="store_true", help="chạy A, B, C tách biệt (tốn gọi LLM hơn)")
    parser.add_argument("--quick", action="store_true", help="thử nhanh: chỉ module grading, 1 lần")
    parser.add_argument("--report-only", action="store_true", help="chỉ tổng hợp + vẽ biểu đồ")
    parser.add_argument("--reset", action="store_true", help="xoá results/runs.csv cũ trước khi chạy")
    args = parser.parse_args()

    if args.quick:
        args.modules, args.runs = ["grading"], 1
    if args.reset and RUNS_CSV.exists():
        RUNS_CSV.unlink()
    if not args.report_only:
        run_experiment(args)
    report()


if __name__ == "__main__":
    main()
