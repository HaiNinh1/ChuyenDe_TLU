"""Cổng chung để CHẠY TEST + ĐO COVERAGE cho mọi ngôn ngữ.

Chọn adapter theo đuôi file mã nguồn (.py -> pytest, .js/.ts -> Jest) rồi gọi adapter.run_tests().
Logic chạy pytest trước đây nằm ở file này đã được chuyển sang adapters/python_adapter.py.

Chạy thử:
    python -m testgen.runner targets/python/grading.py generated_tests/baseline/test_grading.py
    python -m testgen.runner targets/javascript/bank_account.js generated_tests/baseline/bank_account.test.js
"""
import sys
from pathlib import Path

from adapters import adapter_for_file
# Dataclass kết quả dùng chung (xem adapters/base.py) — import lại ở đây để code cũ vẫn dùng được
from adapters.base import CoverageResult, RunResult, TestCaseResult, TestResult  # noqa: F401


def run_tests(source_file, test_code: str, timeout: int = 60, with_coverage: bool = True,
              deselect=None) -> TestResult:
    """Chạy `test_code` cho file mã nguồn `source_file` bằng adapter phù hợp. Trả về TestResult."""
    return adapter_for_file(source_file).run_tests(source_file, test_code, timeout=timeout,
                                                   with_coverage=with_coverage, deselect=deselect)


if __name__ == "__main__":
    import testgen  # noqa: F401  (UTF-8 cho console Windows)

    source, tests = sys.argv[1], sys.argv[2]
    adapter = adapter_for_file(source)
    print(f"Ngôn ngữ: {adapter.describe_tools()}")
    res = run_tests(source, Path(tests).read_text(encoding="utf-8"))
    print(f"passed={res.passed} failed={res.failed} errors={res.errors} xfailed={res.xfailed} "
          f"line={res.line_coverage}% branch={res.branch_coverage}% ({res.duration}s)")
    print("Dòng / nhánh chưa phủ:\n" + adapter.describe_missing(Path(source).read_text(encoding="utf-8"), res))
    for t in res.failing_tests():
        print(f"  FAIL {t.name}: {t.message.splitlines()[0] if t.message else ''}")
    if res.collection_error:
        print("LỖI THU THẬP:", res.collection_error[:500])
