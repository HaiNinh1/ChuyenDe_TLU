"""Kiểm tra evaluate.py chạy trọn vẹn (dùng LLM giả lập, ghi kết quả vào thư mục tạm)."""
import argparse

import evaluate

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
    m = evaluate.measure("grading", GOOD_GRADING_TESTS, measure_mutants=5)
    assert m["has_bug"] == 1 and m["bug_detected"] == 1
    assert m["suspected"] == 1 and m["suspected_tp"] == 1 and m["suspected_fp"] == 0
    assert m["tests_failing"] == 1  # test_wrong_but_unlabeled


def test_measure_module_without_bug():
    code = "import calculator\n\n\ndef test_add():\n    assert calculator.add(1, 2) == 3\n"
    m = evaluate.measure("calculator", code, measure_mutants=50)  # lấy hết mutant -> có mutant của add()
    assert m["has_bug"] == 0 and m["bug_detected"] == 0
    assert m["mutation_score"] > 0


def test_full_pipeline_with_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(evaluate, "RUNS_CSV", tmp_path / "runs.csv")
    from testgen import agent as agent_module
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")

    args = argparse.Namespace(modules=["calculator"], configs=["A", "B", "C", "D"], runs=1, max_iters=3,
                              max_mutants=5, measure_mutants=5, independent=False)
    evaluate.run_experiment(args)
    rows = evaluate.read_rows()
    assert sorted(r["config"] for r in rows) == ["A", "B", "C", "D"]
    assert all(r["provider"] == "mock" for r in rows)

    # Chạy lại -> không chạy trùng (tiếp tục được qua nhiều ngày)
    evaluate.run_experiment(args)
    assert len(evaluate.read_rows()) == 4

    evaluate.report()
    assert (tmp_path / "results.csv").exists()
    assert (tmp_path / "summary.png").exists() and (tmp_path / "mutation_by_module.png").exists()
