from pathlib import Path

import pytest

from adapters.python_adapter import describe_missing
from testgen.runner import run_tests

MODULE = '''def sign(x):
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0
'''


@pytest.fixture
def module_path(tmp_path) -> Path:
    path = tmp_path / "mymod.py"
    path.write_text(MODULE, encoding="utf-8")
    return path


def test_all_pass_full_coverage(module_path):
    code = ("import mymod\n\ndef test_pos():\n    assert mymod.sign(5) == 1\n\n"
            "def test_neg():\n    assert mymod.sign(-2) == -1\n\ndef test_zero():\n    assert mymod.sign(0) == 0\n")
    res = run_tests(module_path, code)
    assert res.ok and res.passed == 3 and res.total == 3
    assert res.line_coverage == 100.0 and res.branch_coverage == 100.0
    assert res.missing_lines == [] and res.missing_branches == []


def test_partial_coverage_reports_missing(module_path):
    code = "import mymod\n\ndef test_pos():\n    assert mymod.sign(5) == 1\n"
    res = run_tests(module_path, code)
    assert res.ok
    assert res.line_coverage < 100 and res.branch_coverage < 100
    assert 4 in res.missing_lines and 5 in res.missing_lines
    text = describe_missing(MODULE, res)
    assert "Dòng 5 chưa chạy: `return -1`" in text
    assert "Nhánh từ dòng 2" in text


def test_failing_test_is_reported(module_path):
    code = "import mymod\n\ndef test_wrong():\n    assert mymod.sign(5) == 2\n"
    res = run_tests(module_path, code)
    assert not res.ok and res.failed == 1
    assert res.failing_tests()[0].name == "test_wrong"
    assert "assert 1 == 2" in res.failing_tests()[0].message
    assert res.line_coverage > 0  # vẫn đo coverage dù test fail


def test_syntax_error_detected_without_running(module_path):
    res = run_tests(module_path, "def test_x(:\n    pass\n")
    assert res.collection_error.startswith("SyntaxError")
    assert not res.ok


def test_import_error_is_collection_error(module_path):
    res = run_tests(module_path, "import khong_ton_tai\n\ndef test_x():\n    assert True\n")
    assert "Lỗi khi thu thập test" in res.collection_error
    assert "khong_ton_tai" in res.collection_error


def test_no_tests_found(module_path):
    res = run_tests(module_path, "import mymod\n\ndef helper():\n    pass\n")
    assert "Không tìm thấy hàm test" in res.collection_error


def test_timeout_is_handled(module_path):
    res = run_tests(module_path, "def test_forever():\n    while True:\n        pass\n", timeout=3)
    assert res.timed_out and not res.ok


def test_xfail_and_deselect(module_path):
    code = ("import pytest\nimport mymod\n\n"
            "@pytest.mark.xfail(strict=False, reason='SUSPECTED_BUG: x')\n"
            "def test_bug():\n    assert mymod.sign(0) == 99\n\n"
            "def test_bad():\n    assert False\n\n"
            "def test_ok():\n    assert mymod.sign(1) == 1\n")
    res = run_tests(module_path, code, deselect=["test_bad"])
    assert res.xfailed == 1 and res.passed == 1 and res.failed == 0
    assert res.ok
