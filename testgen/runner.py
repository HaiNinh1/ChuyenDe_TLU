"""Chạy bộ test bằng pytest trong một thư mục tạm và thu thập kết quả + coverage.

Tại sao chạy trong thư mục tạm và bằng subprocess (tiến trình con)?
- Cô lập: test do LLM sinh có thể lỗi, treo, hoặc sửa biến toàn cục; chạy ở tiến trình riêng thì
  chương trình chính không bị ảnh hưởng.
- Có timeout: test lặp vô hạn sẽ bị dừng sau `timeout` giây.
- Thư mục tạm chỉ chứa đúng 2 file: `<module>.py` và `test_<module>.py` -> `import <module>` luôn đúng.

Cách lấy kết quả (không phải "đọc chữ" trên màn hình):
- `--junitxml=report.xml`      -> file XML liệt kê từng test: pass/fail/error/skip/xfail + thông báo lỗi
- `--cov-report=json:cov.json` -> file JSON coverage: dòng/nhánh nào chưa chạy
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class TestCaseResult:
    __test__ = False  # báo pytest: đây không phải class test
    name: str        # tên test, ví dụ "test_letter_grade_b_range" hoặc "test_x[1-2]"
    outcome: str     # passed | failed | error | skipped | xfailed
    message: str = ""


@dataclass
class RunResult:
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    xfailed: int = 0
    collection_error: str = ""      # khác rỗng nếu file test không chạy được (syntax/import/không có test)
    timed_out: bool = False
    line_coverage: float = 0.0      # %
    branch_coverage: float = 0.0    # %
    missing_lines: list = field(default_factory=list)      # [12, 15, ...]
    missing_branches: list = field(default_factory=list)   # [[17, 19], [30, -28], ...]  (-N: thoát khỏi hàm)
    tests: list = field(default_factory=list)              # list[TestCaseResult]
    output: str = ""                # phần cuối output của pytest (để gửi cho LLM khi cần)
    duration: float = 0.0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors + self.skipped + self.xfailed

    @property
    def ok(self) -> bool:
        """Bộ test chạy được và không có test nào fail/error."""
        return not self.collection_error and self.failed == 0 and self.errors == 0 and self.total > 0

    def failing_tests(self) -> list:
        return [t for t in self.tests if t.outcome in ("failed", "error")]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["total"] = self.total
        return data


def run_tests(module_path, test_code: str, timeout: int = 60, with_coverage: bool = True,
              deselect=None) -> RunResult:
    """Chạy `test_code` với module ở `module_path`. Trả về RunResult.

    deselect: danh sách tên test cần bỏ qua (dùng khi đo mutation chỉ trên các test pass).
    """
    module_path = Path(module_path)
    module_name = module_path.stem
    result = RunResult()

    # Kiểm tra cú pháp trước: nếu sai thì khỏi chạy pytest
    try:
        ast.parse(test_code)
    except SyntaxError as exc:
        result.collection_error = f"SyntaxError: {exc.msg} (dòng {exc.lineno}): {exc.text!r}"
        result.output = result.collection_error
        return result

    work_dir = Path(tempfile.mkdtemp(prefix="testgen_"))
    try:
        shutil.copy(module_path, work_dir / f"{module_name}.py")
        test_file = work_dir / f"test_{module_name}.py"
        test_file.write_text(test_code, encoding="utf-8")

        cmd = [sys.executable, "-m", "pytest", test_file.name, "-q", "-p", "no:cacheprovider",
               "--rootdir", str(work_dir), "--junitxml=report.xml"]
        if with_coverage:
            cmd += [f"--cov={module_name}", "--cov-branch", "--cov-report=json:cov.json"]
        for name in deselect or []:
            cmd += ["--deselect", f"{test_file.name}::{name}"]

        start = time.time()
        proc = run_subprocess(cmd, work_dir, timeout)
        result.duration = round(time.time() - start, 2)

        if proc is None:
            result.timed_out = True
            result.collection_error = f"Bộ test chạy quá {timeout} giây (có thể lặp vô hạn) và đã bị dừng."
            result.output = result.collection_error
            return result

        result.output = tail(proc.stdout + proc.stderr, 4000)
        parse_junit(work_dir / "report.xml", result)

        # Mã thoát của pytest: 0 = pass hết, 1 = có test fail, 2 = lỗi khi thu thập/bị ngắt,
        # 3 = lỗi nội bộ, 4 = sai tham số dòng lệnh, 5 = không tìm thấy test nào
        if proc.returncode in (2, 3, 4):
            result.collection_error = "Lỗi khi thu thập test (syntax/import/fixture):\n" + result.output
        elif proc.returncode == 5:
            result.collection_error = "Không tìm thấy hàm test nào (tên hàm phải bắt đầu bằng test_)."

        if with_coverage:
            parse_coverage(work_dir / "cov.json", f"{module_name}.py", result)
        return result
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_subprocess(cmd, cwd, timeout):
    """Chạy lệnh với timeout. Trả về None nếu quá thời gian."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(cwd)            # để `import <module>` tìm thấy module trong thư mục tạm
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"                 # tránh lỗi mã hoá tiếng Việt trên Windows
    try:
        return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def parse_junit(xml_path: Path, result: RunResult):
    """Đọc report.xml của pytest -> đếm pass/fail/error/skip/xfail cho từng test."""
    if not xml_path.exists():
        return
    root = ET.parse(xml_path).getroot()
    for case in root.iter("testcase"):
        name = case.get("name", "")
        outcome, message = "passed", ""
        for child in case:
            if child.tag == "failure":
                outcome, message = "failed", (child.get("message") or "") + "\n" + (child.text or "")
            elif child.tag == "error":
                outcome, message = "error", (child.get("message") or "") + "\n" + (child.text or "")
            elif child.tag == "skipped":
                # pytest ghi xfail dưới dạng <skipped type="pytest.xfail">
                outcome = "xfailed" if child.get("type") == "pytest.xfail" else "skipped"
                message = child.get("message") or ""
        # Lỗi thu thập được pytest ghi thành testcase không có tên hàm -> không tính là test
        if not name and outcome == "error":
            continue
        result.tests.append(TestCaseResult(name=name, outcome=outcome, message=tail(message.strip(), 1500)))
        if outcome == "passed":
            result.passed += 1
        elif outcome == "failed":
            result.failed += 1
        elif outcome == "error":
            result.errors += 1
        elif outcome == "xfailed":
            result.xfailed += 1
        else:
            result.skipped += 1


def parse_coverage(json_path: Path, file_name: str, result: RunResult):
    """Đọc cov.json của coverage.py -> % dòng, % nhánh, danh sách dòng/nhánh chưa chạy."""
    if not json_path.exists():
        return
    data = json.loads(json_path.read_text(encoding="utf-8"))
    info = None
    for path, file_info in data.get("files", {}).items():
        if Path(path).name == file_name:
            info = file_info
            break
    if info is None:
        return
    summary = info["summary"]
    statements = summary.get("num_statements", 0)
    branches = summary.get("num_branches", 0)
    result.line_coverage = round(100.0 * summary.get("covered_lines", 0) / statements, 1) if statements else 100.0
    result.branch_coverage = round(100.0 * summary.get("covered_branches", 0) / branches, 1) if branches else 100.0
    result.missing_lines = info.get("missing_lines", [])
    result.missing_branches = info.get("missing_branches", [])


def describe_missing(source: str, result: RunResult, limit: int = 25) -> str:
    """Mô tả dòng/nhánh chưa phủ bằng lời, kèm nội dung dòng code, để đưa vào prompt."""
    lines = source.splitlines()

    def code_at(n):
        return lines[n - 1].strip() if 0 < n <= len(lines) else ""

    parts = []
    for n in result.missing_lines[:limit]:
        parts.append(f"- Dòng {n} chưa chạy: `{code_at(n)}`")
    for start, end in result.missing_branches[:limit]:
        if start in result.missing_lines:
            continue  # dòng chưa chạy thì hiển nhiên nhánh của nó cũng chưa chạy
        target = "thoát khỏi hàm" if end < 0 else f"dòng {end} (`{code_at(end)}`)"
        parts.append(f"- Nhánh từ dòng {start} (`{code_at(start)}`) sang {target} chưa được đi qua")
    return "\n".join(parts) if parts else "(không có)"


def tail(text: str, max_chars: int) -> str:
    """Giữ phần CUỐI của chuỗi dài (thông tin lỗi quan trọng thường nằm ở cuối)."""
    return text if len(text) <= max_chars else "...\n" + text[-max_chars:]


if __name__ == "__main__":
    # Chạy thử: python -m testgen.runner targets/grading.py generated_tests/baseline/test_grading.py
    module, tests = sys.argv[1], sys.argv[2]
    res = run_tests(module, Path(tests).read_text(encoding="utf-8"))
    print(f"passed={res.passed} failed={res.failed} errors={res.errors} xfailed={res.xfailed} "
          f"line={res.line_coverage}% branch={res.branch_coverage}% ({res.duration}s)")
    print("Dòng chưa phủ:", res.missing_lines, "| Nhánh chưa phủ:", res.missing_branches)
    for t in res.failing_tests():
        print(f"  FAIL {t.name}: {t.message.splitlines()[0] if t.message else ''}")
    if res.collection_error:
        print("LỖI THU THẬP:", res.collection_error[:500])
