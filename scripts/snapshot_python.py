"""Chụp "ảnh" hành vi của phần PYTHON để so sánh TRƯỚC và SAU khi refactor sang kiến trúc Adapter.

Ý tưởng (kiểm thử hồi quy - regression test cho chính công cụ):
    1. PROMPT: dựng mọi prompt với cùng dữ liệu đầu vào -> lưu mã băm SHA-256.
       Sau refactor, prompt cho Python phải GIỐNG HỆT từng ký tự (LLM nhận đúng nội dung như cũ).
    2. RUNNER + MUTATION (tất định, không gọi LLM): chạy lại các bộ test đã lưu trong log thực nghiệm
       -> số pass/fail, coverage, dòng chưa phủ, trạng thái TỪNG mutant. Sau refactor phải giống hệt.
    3. AGENT VỚI LLM GIẢ LẬP (tất định): kịch bản trả lời cố định -> chuỗi hành động + kết quả cuối.
    4. (tuỳ chọn --llm) AGENT VỚI LLM THẬT trên 1 module: LLM không tất định nên chỉ so "tương đương":
       chạy đủ các bước, coverage/mutation ở mức tương tự.

Chạy:
    python scripts/snapshot_python.py --out docs/baseline_truoc_refactor.json --llm
    python scripts/snapshot_python.py --out docs/sau_refactor.json --llm --compare docs/baseline_truoc_refactor.json
"""
import argparse
import hashlib
import json
import platform
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import testgen  # noqa: E402,F401  (UTF-8 cho console Windows)
from testgen import prompts  # noqa: E402
from testgen.agent import AgentConfig, TestGenAgent  # noqa: E402
from testgen.config import Settings  # noqa: E402
from testgen.llm_client import LLMClient  # noqa: E402
from testgen.mutation import run_mutation_testing  # noqa: E402
from testgen.runner import run_tests  # noqa: E402

MODULES = ["grading", "shopping_cart"]


def target_path(module: str) -> Path:
    """Sau refactor module Python nằm ở targets/python/, trước đó ở targets/."""
    new = ROOT / "targets" / "python" / f"{module}.py"
    return new if new.exists() else ROOT / "targets" / f"{module}.py"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ 1. prompt
def snapshot_prompts() -> dict:
    src = target_path("grading").read_text(encoding="utf-8")
    test_code = "import grading\n\n\ndef test_a():\n    assert grading.letter_grade(95) == 'A'\n"
    lessons = "- [ImportError] Luôn import module bằng tên file."
    numbered = "\n".join(f"{i:4d} | {line}" for i, line in enumerate(src.splitlines(), start=1))
    if hasattr(prompts, "system_prompt"):
        # Sau refactor: khung prompt chung + phần riêng của Python lấy từ PythonAdapter.prompt_hints()
        from adapters import get_adapter
        hints = get_adapter("python").prompt_hints()
        system = prompts.system_prompt(hints)

        def build(fn, *args):
            return fn(hints, *args)
    else:
        # Trước refactor: prompt viết cứng cho Python
        system = prompts.SYSTEM_PROMPT

        def build(fn, *args):
            return fn(*args)
    cases = {
        "SYSTEM_PROMPT": system,
        "initial": build(prompts.initial_prompt, "grading", src),
        "initial_lessons": build(prompts.initial_prompt, "grading", src, lessons),
        "fix_collection": build(prompts.fix_collection_prompt, "grading", src, test_code, "ImportError: x", lessons),
        "classify": build(prompts.classify_prompt, "grading", src, test_code, "AssertionError: 'C' != 'B'"),
        "fix_tests": build(prompts.fix_tests_prompt, "grading", src, test_code, "AssertionError", lessons),
        "coverage": build(prompts.coverage_prompt, "grading", numbered, test_code, 80.0, 75.5, "- Dòng 3 chưa chạy"),
        "mutation": build(prompts.mutation_prompt, "grading", numbered, test_code,
                          "- Mutant #1, dòng 3: `a` -> `b`"),
    }
    return {name: {"sha256": sha(text), "chars": len(text)} for name, text in cases.items()}


# ------------------------------------------------------------------ 2. runner + mutation
def latest_log(module: str, label: str = "eval_C") -> dict:
    path = sorted((ROOT / "logs").glob(f"{module}_{label}_*.json"))[0]  # log lượt 1 (cố định)
    return json.loads(path.read_text(encoding="utf-8"))


def run_summary(module_path: Path, code: str) -> dict:
    res = run_tests(module_path, code)
    return {
        "passed": res.passed, "failed": res.failed, "errors": res.errors, "xfailed": res.xfailed,
        "skipped": res.skipped, "collection_error": bool(res.collection_error),
        "line_coverage": res.line_coverage, "branch_coverage": res.branch_coverage,
        "missing_lines": res.missing_lines, "missing_branches": res.missing_branches,
        "outcomes": sorted(f"{t.name}={t.outcome}" for t in res.tests),
    }


def mutation_summary(module_path: Path, code: str) -> dict:
    m = run_mutation_testing(module_path, code, max_mutants=40, seed=0, skip_failing=True)
    return {
        "total": m.total, "killed": m.killed, "survived": m.survived, "timeout": m.timeout,
        "score": m.score, "sampled_from": m.sampled_from, "error": m.error,
        "mutants": [f"{mu.status} | {mu.describe()}" for mu in m.mutants],
    }


def snapshot_deterministic() -> dict:
    out = {}
    for module in MODULES:
        log = latest_log(module)
        path = target_path(module)
        for name, code in (("initial", log["snapshots"]["initial"]["code"]), ("final", log["final_test_code"])):
            key = f"{module}/{name}"
            print(f"  [tất định] {key}", flush=True)
            out[key] = {"test_code_sha256": sha(code), "run": run_summary(path, code),
                        "mutation": mutation_summary(path, code)}
    return out


# ------------------------------------------------------------------ 3. agent + LLM giả lập
MOCK_MODULE = '''def grade(score):
    """score >= 50 -> "PASS", ngược lại "FAIL". score < 0 -> ném ValueError."""
    if score < 0:
        raise ValueError("điểm âm")
    if score > 50:
        return "PASS"
    return "FAIL"
'''

MOCK_SCRIPT = [
    "```python\nimport mod\n\ndef test_x(:\n    pass\n```",
    '```python\nimport pytest\nimport mod\n\n\ndef test_pass():\n    assert mod.grade(80) == "PASS"\n\n\n'
    'def test_wrong():\n    assert mod.grade(10) == "PASS"\n\n\n'
    'def test_boundary():\n    assert mod.grade(50) == "PASS"\n```\nLESSON: Kiểm tra cú pháp trước khi trả lời.',
    json.dumps({"verdicts": [
        {"test": "test_wrong", "verdict": "TEST_WRONG", "reason": "10 < 50 nên phải là FAIL"},
        {"test": "test_boundary", "verdict": "SUSPECTED_BUG", "reason": "docstring nói 50 -> PASS"},
    ]}),
    '```python\ndef test_wrong():\n    assert mod.grade(10) == "FAIL"\n```\nLESSON: Đọc kỹ ngưỡng trong docstring.',
    "```python\ndef test_negative():\n    with pytest.raises(ValueError):\n        mod.grade(-1)\n```",
    # phase mutation: thêm test ở biên
    "```python\ndef test_high():\n    assert mod.grade(51) == \"PASS\"\n\n\ndef test_zero():\n"
    "    assert mod.grade(0) == \"FAIL\"\n```",
]


def snapshot_mock_agent() -> dict:
    from testgen import agent as agent_module
    saved = agent_module.LOGS_DIR, agent_module.OUTPUT_DIR
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        module_path = tmp / "mod.py"
        module_path.write_text(MOCK_MODULE, encoding="utf-8")
        agent_module.LOGS_DIR, agent_module.OUTPUT_DIR = tmp / "logs", tmp / "out"  # log giả lập -> thư mục tạm
        try:
            client = LLMClient(settings=Settings(provider="mock", model="mock", max_retries=1),
                               mock_responses=list(MOCK_SCRIPT))
            config = AgentConfig(max_iterations=8, use_mutation=True, mutation_threshold=100.0, max_mutants=20)
            summary = TestGenAgent(module_path, client=client, config=config).run()
        finally:
            agent_module.LOGS_DIR, agent_module.OUTPUT_DIR = saved  # trả lại để lần chạy LLM thật lưu log đúng chỗ
    return {
        "actions": [it["action"] for it in summary["iterations"]],
        "stop_reason": summary["stop_reason"],
        "final": summary["final"],
        "suspected_bugs": sorted(summary["suspected_bugs"]),
        "llm_calls": summary["stats"]["llm_calls"],
        "final_test_code_sha256": sha(summary["final_test_code"]),
        "mutation_scores": [it["mutation_score"] for it in summary["iterations"]],
    }


# ------------------------------------------------------------------ 4. agent + LLM thật
def snapshot_real_llm(module: str = "grading") -> dict:
    config = AgentConfig(max_iterations=6, use_mutation=True, label="refactor_check")
    summary = TestGenAgent(target_path(module), client=LLMClient(), config=config).run()
    return {
        "module": module,
        "llm": summary["llm"],
        "actions": [it["action"] for it in summary["iterations"]],
        "stop_reason": summary["stop_reason"],
        "final": summary["final"],
        "suspected_bugs": summary["suspected_bugs"],
        "llm_calls": summary["stats"]["llm_calls"],
        "seconds": summary["stats"]["total_seconds"],
        "log": Path(summary["log_path"]).name,
    }


# ------------------------------------------------------------------ so sánh
def compare(old: dict, new: dict) -> list:
    """Trả về danh sách khác biệt ở các phần TẤT ĐỊNH (prompt, runner, mutation, agent giả lập)."""
    diffs = []
    for section in ("prompts", "deterministic", "mock_agent"):
        a, b = old.get(section), new.get(section)
        if a == b:
            continue
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                if a.get(key) != b.get(key):
                    diffs.append(f"{section}/{key}: TRƯỚC={json.dumps(a.get(key), ensure_ascii=False)[:300]} "
                                 f"SAU={json.dumps(b.get(key), ensure_ascii=False)[:300]}")
        else:
            diffs.append(f"{section}: khác nhau")
    return diffs


def main():
    parser = argparse.ArgumentParser(description="Chụp hành vi phần Python để so sánh trước/sau refactor")
    parser.add_argument("--out", required=True)
    parser.add_argument("--llm", action="store_true", help="chạy thêm agent với LLM thật (tốn ~3-6 request)")
    parser.add_argument("--compare", help="file snapshot cũ để so sánh")
    args = parser.parse_args()

    snap = {"created": datetime.now().isoformat(timespec="seconds"), "python": platform.python_version()}
    print("1) Prompt...", flush=True)
    snap["prompts"] = snapshot_prompts()
    print("2) Runner + mutation (tất định)...", flush=True)
    snap["deterministic"] = snapshot_deterministic()
    print("3) Agent + LLM giả lập...", flush=True)
    snap["mock_agent"] = snapshot_mock_agent()
    if args.llm:
        print("4) Agent + LLM thật...", flush=True)
        snap["real_llm"] = snapshot_real_llm()

    Path(args.out).write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã lưu {args.out}")

    if args.compare:
        old = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        diffs = compare(old, snap)
        print("\n===== SO SÁNH VỚI", args.compare, "=====")
        print("Phần tất định GIỐNG HỆT" if not diffs else "\n".join(["KHÁC BIỆT:"] + diffs))
        if "real_llm" in old and "real_llm" in snap:
            for key in ("actions", "stop_reason", "final", "suspected_bugs", "llm_calls"):
                print(f"  LLM thật {key}: TRƯỚC={old['real_llm'][key]} | SAU={snap['real_llm'][key]}")
        sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
