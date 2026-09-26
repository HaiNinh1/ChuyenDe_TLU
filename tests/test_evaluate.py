"""Kiểm tra evaluate.py (dùng LLM giả lập, ghi log/kết quả vào thư mục tạm)."""
import argparse
import json

import pytest

import evaluate
from adapters import get_adapter
from testgen import agent as agent_module

needs_node = pytest.mark.skipif(not get_adapter("javascript").check_environment().ok,
                                reason="Chưa cài Node.js/Jest (npm install)")

GOOD_GRADING_TESTS = '''import pytest
import grading


def test_a():
    assert grading.letter_grade(95) == "A"


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: 80 phải là B")
def test_b_boundary():
    assert grading.letter_grade(80) == "B"


def test_wrong_but_unlabeled():
    assert grading.letter_grade(10) == "A"
'''


def test_measure_bug_detection_and_suspected():
    m = evaluate.measure("grading", GOOD_GRADING_TESTS, exclude=set(), measure_mutants=5)
    assert m["has_bug"] == 1 and m["bug_detected"] == 1
    assert m["suspected"] == 1 and m["suspected_tp"] == 1 and m["suspected_fp"] == 0
    assert m["tests_failing"] == 1  # test_wrong_but_unlabeled


def test_measure_excludes_mutants_seen_by_llm():
    code = "import calculator\n\n\ndef test_add():\n    assert calculator.add(1, 2) == 3\n"
    everything = evaluate.measure("calculator", code, exclude=set(), measure_mutants=100)
    held_out = evaluate.measure("calculator", code, exclude={1, 2, 3}, measure_mutants=100)
    assert everything["has_bug"] == 0 and everything["bug_detected"] == 0
    assert held_out["mutants_heldout"] == everything["mutants_heldout"] - 3


def test_shown_mutants_from_new_and_old_logs():
    new_log = {"iterations": [{"action": "kill_mutants", "shown_mutant_ids": [4, 9]},
                              {"action": "stop", "shown_mutant_ids": [], "survived_mutants": []}]}
    old_log = {"iterations": [{"action": "kill_mutants",
                               "survived_mutants": [f"Mutant #{i}, dòng 3: `a` -> `b`" for i in range(1, 9)]}]}
    assert evaluate.shown_mutants(new_log) == {4, 9}
    assert evaluate.shown_mutants(old_log) == {1, 2, 3, 4, 5, 6}  # prompt cũ chứa 6 mutant đầu


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(evaluate, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    return tmp_path


def make_args(**kw):
    base = dict(languages=["python"], modules=["calculator"], runs=1, max_iters=3, max_mutants=5,
                measure_mutants=5)
    base.update(kw)
    return argparse.Namespace(**base)


def test_full_pipeline_with_mock(sandbox):
    evaluate.generate(make_args())
    assert len(list((sandbox / "logs").glob("calculator_eval_C_*.json"))) == 1
    assert len(list((sandbox / "logs").glob("calculator_eval_D_*.json"))) == 1

    # Chạy lại -> không sinh trùng (tiếp tục được qua nhiều ngày)
    evaluate.generate(make_args())
    assert len(list((sandbox / "logs").glob("*.json"))) == 2

    rows = evaluate.measure_all(make_args())
    assert sorted(r["config"] for r in rows) == ["A", "B", "C", "D"]
    assert all(r["provider"] == "mock" for r in rows)
    evaluate.report(rows)
    results = sandbox / "results"
    assert (results / "results.csv").exists() and (results / "runs.csv").exists()
    assert (results / "summary_python.png").exists() and (results / "mutation_by_module_python.png").exists()
    assert not (results / "language_comparison.png").exists()      # mới có 1 ngôn ngữ -> chưa so sánh
    assert all(r["language"] == "python" for r in rows)


def test_run_stopped_by_llm_error_is_not_counted(sandbox, monkeypatch):
    from testgen.llm_client import LLMClient, LLMError

    def broken(self, system, user, task="chat"):
        raise LLMError("hết quota")

    monkeypatch.setattr(LLMClient, "chat", broken)
    evaluate.generate(make_args())
    log = next((sandbox / "logs").glob("calculator_eval_C_*.json"))
    assert json.loads(log.read_text(encoding="utf-8"))["stop_reason"].startswith("Lỗi gọi LLM")
    assert evaluate.eval_logs("calculator", "eval_C") == []   # không được tính
    assert evaluate.measure_all(make_args()) == []


def test_module_files_and_languages():
    assert evaluate.module_file("python", "grading").name == "grading.py"
    assert evaluate.module_file("javascript", "shipping").name == "shipping.ts"
    assert evaluate.module_file("javascript", "bank_account", fixed=True).parent.name == "javascript"
    assert evaluate.language_of("duration_parser") == "javascript"


@needs_node
def test_measure_javascript_bug_detection():
    code = ("import { shippingFee } from './shipping';\n\n"
            "test('đơn nhỏ', () => {\n  expect(shippingFee(100)).toBe(30);\n});\n\n"
            "// SUSPECTED_BUG: 500 phải miễn phí\n"
            "test.failing('biên 500', () => {\n  expect(shippingFee(500)).toBe(0);\n});\n")
    m = evaluate.measure("shipping", code, exclude=set(), measure_mutants=10)
    assert m["has_bug"] == 1 and m["bug_detected"] == 1
    assert (m["suspected"], m["suspected_tp"], m["suspected_fp"]) == (1, 1, 0)
    assert m["tests_failing"] == 0 and 0 < m["line_coverage"] < 100


@needs_node
def test_pipeline_two_languages_with_mock(sandbox):
    evaluate.generate(make_args(languages=["python", "javascript"], modules=["calculator", "string_tools"]))
    assert len(list((sandbox / "logs").glob("string_tools_eval_C_*.json"))) == 1
    rows = evaluate.measure_all(make_args())
    assert {r["language"] for r in rows} == {"python", "javascript"}
    evaluate.report(rows)
    results = sandbox / "results"
    assert (results / "summary_javascript.png").exists() and (results / "language_comparison.png").exists()
    summary = evaluate.summarize(rows)
    assert {(s["language"], s["config"][0]) for s in summary} == {(lang, c) for lang in ("python", "javascript")
                                                                  for c in "ABCD"}
