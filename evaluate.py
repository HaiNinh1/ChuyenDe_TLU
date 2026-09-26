"""THỰC NGHIỆM: so sánh 4 cấu hình trên các module mục tiêu của CẢ HAI ngôn ngữ (Python, JavaScript/TypeScript).

    A: Baseline — sinh test một lần
    B: Agent + phản hồi coverage
    C: Agent + coverage + mutation
    D: C + bộ nhớ tự học

Thực nghiệm gồm 2 BƯỚC TÁCH RIÊNG:

1) SINH (gọi LLM, tốn request) — chạy agent cấu hình C và D, mỗi lần chạy lưu một log JSON trong logs/
   (tên có nhãn eval_C / eval_D). Thiết kế "ghép cặp" để tiết kiệm lần gọi LLM:
     - A = bộ test ban đầu của lần chạy C (cùng prompt, cùng một lần gọi LLM)        -> snapshot "initial"
     - B = trạng thái của C đúng lúc phase coverage kết thúc (B sẽ dừng đúng ở đó)  -> snapshot "coverage_done"
   D chạy riêng: bộ nhớ bắt đầu RỖNG ở mỗi lần lặp, các module chạy lần lượt để bộ nhớ tích luỹ dần
   (bộ nhớ chia theo ngôn ngữ: module JS chỉ nhận kinh nghiệm JS).
   Lần chạy bị dừng vì lỗi LLM (hết quota, mất mạng) KHÔNG được tính -> lần sau chạy lại.
   => Chạy lại lệnh sẽ chỉ chạy phần còn thiếu (chạy tiếp được qua nhiều ngày khi bị giới hạn request).

2) CHẤM (không gọi LLM) — đọc log, chấm lại MỌI cấu hình bằng cùng một thước đo (qua adapter của ngôn ngữ):
     - line/branch coverage (Python: coverage.py, JS/TS: Istanbul)
     - mutation score trên các mutant mà LLM CHƯA TỪNG THẤY trong prompt của C/D ("held-out",
       giống tách tập train/test trong học máy) -> không bị thổi phồng vì agent đã được "mớm" đúng các mutant đó.
       Cột mutation_all: điểm trên mọi mutant (để so sánh, thấy mức chênh).
     - phát hiện bug: có test FAIL/SUSPECTED trên code có bug nhưng PASS trên bản đã sửa (evaluation/fixed_targets)
   Kết quả: results/runs.csv (từng lần), results/results.csv (trung bình theo ngôn ngữ + cấu hình),
   biểu đồ PNG cho từng ngôn ngữ và một biểu đồ so sánh hai ngôn ngữ.

Ví dụ:
    python evaluate.py --quick                          # thử nhanh: 1 module mỗi ngôn ngữ, 1 lần (~15 request)
    python evaluate.py --runs 3                         # đầy đủ: 5 module Python + 4 module JS, 3 lần
    python evaluate.py --languages javascript --runs 1  # chỉ JavaScript, 1 lần
    python evaluate.py --modules shipping grading       # chỉ vài module (tiết kiệm API)
    python evaluate.py --measure-only                   # không gọi LLM: chỉ chấm lại từ log + vẽ biểu đồ
    python evaluate.py --reset --runs 3                 # làm lại từ đầu (log cũ được chuyển vào logs/archive_*)
"""
import argparse
import csv
import json
import re
import shutil
import time
from pathlib import Path

import testgen  # noqa: F401  (cấu hình UTF-8 cho console Windows)
from adapters import get_adapter, supported_extensions
from testgen.agent import LOGS_DIR, AgentConfig, TestGenAgent
from testgen.config import ROOT_DIR
from testgen.llm_client import LLMClient
from testgen.memory import Memory

TARGETS_DIR = ROOT_DIR / "targets"
FIXED_DIR = ROOT_DIR / "evaluation" / "fixed_targets"
RESULTS_DIR = ROOT_DIR / "results"
# Module mục tiêu của từng ngôn ngữ (dễ -> khó); thư mục con trong targets/ trùng tên ngôn ngữ
LANGUAGES = {
    "python": ["calculator", "text_utils", "grading", "safe_parser", "shopping_cart"],
    "javascript": ["string_tools", "shipping", "duration_parser", "bank_account"],
}
QUICK_MODULES = {"python": ["grading"], "javascript": ["shipping"]}   # --quick: mỗi ngôn ngữ 1 module có bug
LANGUAGE_NAMES = {"python": "Python", "javascript": "JavaScript/TS"}
CONFIG_NAMES = {
    "A": "A: Baseline",
    "B": "B: Agent + coverage",
    "C": "C: B + mutation",
    "D": "D: C + memory",
}
FIELDS = ["language", "config", "module", "run", "line_coverage", "branch_coverage", "mutation_score",
          "mutation_all", "mutants_heldout", "iterations", "llm_calls", "seconds", "cost_usd", "tests_total",
          "tests_failing", "suspected", "suspected_tp", "suspected_fp", "has_bug", "bug_detected", "stop_reason",
          "provider", "model", "log"]


def module_file(language: str, module: str, fixed: bool = False) -> Path:
    """Đường dẫn file mã nguồn của module (đuôi .py / .js / .ts tuỳ file thật có trong thư mục)."""
    folder = (FIXED_DIR if fixed else TARGETS_DIR) / language
    for path in sorted(folder.glob(f"{module}.*")):
        if path.suffix in supported_extensions() and ".test." not in path.name:
            return path
    raise FileNotFoundError(f"Không tìm thấy module {module} trong {folder}")


def language_of(module: str) -> str:
    return next(lang for lang, modules in LANGUAGES.items() if module in modules)


# ============================================================================ BƯỚC 1: SINH
def eval_logs(module: str, label: str, language: str = None) -> list:
    """Các log hợp lệ (không bị dừng vì lỗi LLM) của một module + cấu hình, xếp theo thời gian."""
    language = language or language_of(module)
    logs = []
    for path in sorted(LOGS_DIR.glob(f"{module}_{label}_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("language", "python") != language:   # log trước refactor không có "language" -> Python
            continue
        if not data["stop_reason"].startswith("Lỗi gọi LLM"):
            logs.append(path)
    return logs


def language_ready(language: str) -> bool:
    """Máy đã cài công cụ của ngôn ngữ chưa. Chưa -> cảnh báo và BỎ QUA ngôn ngữ đó (không làm hỏng ngôn ngữ khác)."""
    env = get_adapter(language).check_environment()
    if not env.ok:
        print(f"!! Bỏ qua {LANGUAGE_NAMES[language]}: {env.message()}", flush=True)
    return env.ok


def selected(args) -> list:
    """Danh sách (ngôn ngữ, module) cần SINH theo tham số dòng lệnh."""
    pairs = []
    for language in [lang for lang in args.languages if language_ready(lang)]:
        for module in LANGUAGES[language]:
            if module in args.modules:
                pairs.append((language, module))
    return pairs


def generate(args):
    for run in range(1, args.runs + 1):
        memory = Memory(RESULTS_DIR / "memory" / f"memory_run{run}.json")  # bộ nhớ riêng cho mỗi lần lặp
        for language, module in selected(args):
            path = module_file(language, module)
            for label, use_memory in (("eval_C", False), ("eval_D", True)):
                if len(eval_logs(module, label, language)) >= run:
                    continue  # đã có log hợp lệ cho lần chạy này
                print(f"\n===== Lần {run} | {language} | {module} | {label} =====", flush=True)
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


def measure(module: str, test_code: str, exclude: set, measure_mutants: int, language: str = None) -> dict:
    """Chấm một bộ test bằng cùng một thước đo cho mọi cấu hình (công cụ đo do adapter của ngôn ngữ quyết định)."""
    language = language or language_of(module)
    module_path = module_file(language, module)
    fixed_path = module_file(language, module, fixed=True)
    adapter = get_adapter(language)
    res = adapter.run_tests(module_path, test_code)
    held = adapter.run_mutation(module_path, test_code, max_mutants=measure_mutants, seed=0,
                                skip_failing=True, exclude_ids=exclude)
    full = adapter.run_mutation(module_path, test_code, max_mutants=measure_mutants, seed=0, skip_failing=True)

    has_bug = module_path.read_text(encoding="utf-8") != fixed_path.read_text(encoding="utf-8")
    outcomes_buggy = {t.name: t.outcome for t in res.tests}
    # Trên bản ĐÃ SỬA: bỏ nhãn "dự kiến fail" (JS: test.failing -> test; Python: xfail không cần bỏ)
    outcomes_fixed = {t.name: t.outcome for t in adapter.run_tests(fixed_path, adapter.unmark_suspected(test_code),
                                                                    with_coverage=False).tests}
    # Test "bắt được bug": fail (hoặc bị gắn nhãn nghi bug) trên code lỗi, nhưng pass trên code đúng
    catching = {adapter.base_test_name(n) for n, o in outcomes_buggy.items()
                if o in ("failed", "error", "xfailed") and outcomes_fixed.get(n) == "passed"}
    suspected = adapter.suspected_tests(test_code)
    suspected_tp = [n for n in suspected if n in catching]
    def mutation_value(m):
        # Công cụ mutation không khả dụng -> để TRỐNG (không phải 0%), không tính vào trung bình.
        # Bộ test hỏng / không pass trên code gốc -> 0% (lỗi của bộ test, vẫn tính).
        if not m.available:
            return None
        return 0.0 if m.error else m.score

    return {
        "line_coverage": 0.0 if res.collection_error else res.line_coverage,
        "branch_coverage": 0.0 if res.collection_error else res.branch_coverage,
        "mutation_score": mutation_value(held),
        "mutation_all": mutation_value(full),
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
    """Chấm MỌI log thực nghiệm đang có (mọi ngôn ngữ, mọi module), không phụ thuộc lần sinh vừa rồi."""
    rows = []
    for language, modules in LANGUAGES.items():
        if not any(eval_logs(m, "eval_C", language) or eval_logs(m, "eval_D", language) for m in modules):
            continue
        if not language_ready(language):
            continue
        for module in modules:
            logs_c, logs_d = eval_logs(module, "eval_C", language), eval_logs(module, "eval_D", language)
            for run in range(1, max(len(logs_c), len(logs_d)) + 1):
                rows += measure_run(args, language, module, run,
                                    logs_c[run - 1] if run <= len(logs_c) else None,
                                    logs_d[run - 1] if run <= len(logs_d) else None)
    return rows


def measure_run(args, language, module, run, path_c, path_d) -> list:
    c = json.loads(path_c.read_text(encoding="utf-8")) if path_c else None
    d = json.loads(path_d.read_text(encoding="utf-8")) if path_d else None
    # Loại khỏi tập chấm mọi mutant C hoặc D đã thấy -> 4 cấu hình được chấm trên CÙNG một tập mutant
    exclude = (shown_mutants(c) if c else set()) | (shown_mutants(d) if d else set())
    print(f"Chấm {language}/{module} lần {run} (loại {len(exclude)} mutant LLM đã thấy)...", flush=True)
    jobs = []
    if c:
        snaps = c.get("snapshots", {})
        final_c = {"code": c["final_test_code"], "iterations": c["final"]["num_iterations"],
                   "llm_calls": c["stats"]["llm_calls"], "seconds": c["stats"]["total_seconds"],
                   "cost_usd": c["stats"]["cost_usd"]}
        initial = snaps.get("initial", final_c)
        cov_done = snaps.get("coverage_done", final_c)
        jobs += [("A", initial, "sinh một lần", c, path_c),
                 ("B", cov_done, "hết phase coverage" if "coverage_done" in snaps else c["stop_reason"], c, path_c),
                 ("C", final_c, c["stop_reason"], c, path_c)]
    if d:
        final_d = {"code": d["final_test_code"], "iterations": d["final"]["num_iterations"],
                   "llm_calls": d["stats"]["llm_calls"], "seconds": d["stats"]["total_seconds"],
                   "cost_usd": d["stats"]["cost_usd"]}
        jobs.append(("D", final_d, d["stop_reason"], d, path_d))
    rows = []
    for config, state, reason, log, log_path in jobs:
        row = {"language": language, "config": config, "module": module, "run": run,
               **measure(module, state["code"], exclude, args.measure_mutants, language),
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
    """Trung bình, BỎ QUA ô trống (None / ""), ví dụ mutation không đo được. Không có giá trị nào -> None."""
    values = [float(v) for v in values if v not in (None, "")]
    return round(sum(values) / len(values), 2) if values else None


def num(value) -> float:
    """Giá trị để vẽ biểu đồ (ô trống vẽ thành 0)."""
    return 0.0 if value in (None, "") else float(value)


def summarize(rows: list) -> list:
    """Trung bình theo (ngôn ngữ, cấu hình) — trên mọi module và mọi lần chạy của ngôn ngữ đó."""
    summary = []
    for language in LANGUAGES:
        for config in CONFIG_NAMES:
            group = [r for r in rows if r["config"] == config and r["language"] == language]
            if not group:
                continue
            bug_rows = [r for r in group if int(r["has_bug"]) == 1]
            summary.append({
                "language": language,
                "config": CONFIG_NAMES[config],
                "n_rows": len(group),
                "n_runs": len({r["run"] for r in group}),
                "n_modules": len({r["module"] for r in group}),
                "line_coverage": mean(r["line_coverage"] for r in group),
                "branch_coverage": mean(r["branch_coverage"] for r in group),
                "mutation_score": mean(r["mutation_score"] for r in group),
                "mutation_all": mean(r["mutation_all"] for r in group),
                "n_mutation": sum(1 for r in group if r["mutation_score"] not in (None, "")),  # số dòng đo được
                "iterations": mean(r["iterations"] for r in group),
                "llm_calls": mean(r["llm_calls"] for r in group),
                "seconds": mean(r["seconds"] for r in group),
                "cost_usd": mean(r["cost_usd"] for r in group),
                "tests_total": mean(r["tests_total"] for r in group),
                "tests_failing": mean(r["tests_failing"] for r in group),
                "suspected_tp": sum(int(r["suspected_tp"]) for r in group),
                "suspected_fp": sum(int(r["suspected_fp"]) for r in group),
                "bug_detection_rate": round(mean(r["bug_detected"] for r in bug_rows) * 100, 1)
                if bug_rows else 0.0,
                # Bug được agent GẮN NHÃN đúng (có test SUSPECTED_BUG pass trên bản sửa) — không chỉ "có test fail"
                "bug_flagged_rate": round(mean(int(r["suspected_tp"]) > 0 for r in bug_rows) * 100, 1)
                if bug_rows else 0.0,
            })
    return summary


def summarize_by_module(rows: list) -> list:
    out = []
    for language, modules in LANGUAGES.items():
        for module in modules:
            for config in CONFIG_NAMES:
                group = [r for r in rows if r["config"] == config and r["module"] == module
                         and r["language"] == language]
                if group:
                    out.append({"language": language, "module": module, "config": config, "n_runs": len(group),
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


PALETTE = {"A": "#9aa5b1", "B": "#4c8bf5", "C": "#f5a524", "D": "#2bb673"}
LANG_COLORS = {"python": "#3572A5", "javascript": "#e3b341"}


def _label_bars(ax):
    for bar in ax.patches:
        h = bar.get_height()
        ax.annotate(f"{h:.0f}" if h >= 10 else f"{h:.1f}", (bar.get_x() + bar.get_width() / 2, h),
                    ha="center", va="bottom", fontsize=8)


def plot_language(language: str, summary: list, by_module: list):
    """Biểu đồ của MỘT ngôn ngữ: results/summary_<ngôn ngữ>.png và mutation_by_module_<ngôn ngữ>.png."""
    import matplotlib
    matplotlib.use("Agg")  # vẽ ra file, không cần cửa sổ
    import matplotlib.pyplot as plt

    labels = [s["config"].split(":")[0] for s in summary]
    colors = [PALETTE[label] for label in labels]
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
    ax.bar([x - width / 2 for x in xs], [num(s["mutation_score"]) for s in summary], width, color=colors,
           label="Mutant LLM chưa thấy (held-out)")
    ax.bar([x + width / 2 for x in xs], [num(s["mutation_all"]) for s in summary], width, color=colors, alpha=0.45,
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
        _label_bars(a)
    n_runs = max(s["n_runs"] for s in summary)
    n_modules = max(s["n_modules"] for s in summary)
    fig.suptitle(f"{LANGUAGE_NAMES[language]}: so sánh 4 cấu hình — {n_modules} module × {n_runs} lần chạy")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / f"summary_{language}.png", dpi=130)
    plt.close(fig)

    # Mutation score (held-out) theo từng module
    modules = [m for m in LANGUAGES[language] if any(r["module"] == m for r in by_module)]
    configs = [c for c in CONFIG_NAMES if any(r["config"] == c for r in by_module)]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    w = 0.8 / max(1, len(configs))
    for i, config in enumerate(configs):
        values = [num(next((r["mutation_score"] for r in by_module if r["module"] == m and r["config"] == config),
                           0)) for m in modules]
        ax.bar([x + i * w for x in range(len(modules))], values, w, label=CONFIG_NAMES[config],
               color=PALETTE[config])
    ax.set_xticks([x + w * (len(configs) - 1) / 2 for x in range(len(modules))], modules)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Mutation score held-out (%)")
    ax.set_title(f"{LANGUAGE_NAMES[language]}: mutation score theo module (trên mutant LLM chưa thấy)")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / f"mutation_by_module_{language}.png", dpi=130)
    plt.close(fig)


def plot_comparison(summary: list):
    """So sánh HAI ngôn ngữ trên cùng các chỉ số, theo từng cấu hình: results/language_comparison.png."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    languages = [lang for lang in LANGUAGES if any(s["language"] == lang for s in summary)]
    configs = [c for c in CONFIG_NAMES if any(s["config"] == CONFIG_NAMES[c] for s in summary)]
    metrics = [("line_coverage", "Line coverage (%)", 110), ("branch_coverage", "Branch coverage (%)", 110),
               ("mutation_score", "Mutation held-out (%)", 110), ("bug_flagged_rate", "Bug gắn nhãn đúng (%)", 110),
               ("tests_failing", "Test fail còn lại / module", None), ("llm_calls", "Số lần gọi LLM / module", None)]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
    w = 0.8 / max(1, len(languages))
    for ax, (key, title, ylim) in zip(axes.flat, metrics):
        for i, language in enumerate(languages):
            values = [num(next((s[key] for s in summary if s["language"] == language
                                and s["config"] == CONFIG_NAMES[c]), 0)) for c in configs]
            ax.bar([x + i * w for x in range(len(configs))], values, w, label=LANGUAGE_NAMES[language],
                   color=LANG_COLORS[language])
        ax.set_xticks([x + w * (len(languages) - 1) / 2 for x in range(len(configs))], configs)
        if ylim:
            ax.set_ylim(0, ylim)
        ax.set_title(title)
        _label_bars(ax)
    axes[0][0].legend(loc="lower right", fontsize=8)
    runs = {lang: max(s["n_runs"] for s in summary if s["language"] == lang) for lang in languages}
    fig.suptitle("So sánh giữa hai ngôn ngữ — " + ", ".join(f"{LANGUAGE_NAMES[k]}: {v} lần chạy"
                                                            for k, v in runs.items()))
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "language_comparison.png", dpi=130)
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
    for language in LANGUAGES:
        lang_summary = [s for s in summary if s["language"] == language]
        if lang_summary:
            plot_language(language, lang_summary, [r for r in by_module if r["language"] == language])
    if len({s["language"] for s in summary}) > 1:
        plot_comparison(summary)
    print("\n===== TỔNG HỢP (results/results.csv) =====")
    for s in summary:
        print(json.dumps(s, ensure_ascii=False))
    print("Biểu đồ: results/summary_<ngôn ngữ>.png, results/mutation_by_module_<ngôn ngữ>.png, "
          "results/language_comparison.png")


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
    all_modules = [m for modules in LANGUAGES.values() for m in modules]
    parser = argparse.ArgumentParser(description="Thực nghiệm so sánh 4 cấu hình A/B/C/D trên Python và JS/TS")
    parser.add_argument("--languages", nargs="+", default=list(LANGUAGES), choices=list(LANGUAGES))
    parser.add_argument("--modules", nargs="+", default=all_modules, choices=all_modules,
                        help="chỉ SINH cho các module này (tiết kiệm API)")
    parser.add_argument("--runs", type=int, default=3, help="số lần lặp mỗi cấu hình")
    parser.add_argument("--max-iters", type=int, default=6)
    parser.add_argument("--max-mutants", type=int, default=20, help="số mutant agent dùng trong vòng lặp")
    parser.add_argument("--measure-mutants", type=int, default=40, help="số mutant tối đa dùng để CHẤM")
    parser.add_argument("--quick", action="store_true",
                        help="thử nhanh: mỗi ngôn ngữ 1 module có bug (grading, shipping), 1 lần")
    parser.add_argument("--measure-only", action="store_true", help="không gọi LLM, chỉ chấm lại từ log")
    parser.add_argument("--reset", action="store_true", help="làm lại từ đầu (lưu trữ log thực nghiệm cũ)")
    args = parser.parse_args()

    if args.quick:
        args.modules = [m for lang in args.languages for m in QUICK_MODULES[lang]]
        args.runs = 1
    if args.reset:
        reset()
    if not args.measure_only:
        generate(args)
    report(measure_all(args))


if __name__ == "__main__":
    main()
