"""PythonAdapter: pytest + coverage.py (pytest-cov) + toán tử đột biến của mutmut 2.5.1.

Toàn bộ logic ở đây được CHUYỂN NGUYÊN từ bản chỉ-Python trước refactor
(testgen/runner.py, testgen/mutation.py, một phần memory.py và prompts.py), không viết lại.

--- Chạy test ---
Tại sao chạy trong thư mục tạm và bằng subprocess (tiến trình con)?
- Cô lập: test do LLM sinh có thể lỗi, treo, hoặc sửa biến toàn cục; chạy ở tiến trình riêng thì
  chương trình chính không bị ảnh hưởng.
- Có timeout: test lặp vô hạn sẽ bị dừng sau `timeout` giây.
- Thư mục tạm chỉ chứa đúng 2 file: `<module>.py` và `test_<module>.py` -> `import <module>` luôn đúng.
Cách lấy kết quả (không phải "đọc chữ" trên màn hình):
- `--junitxml=report.xml`      -> file XML liệt kê từng test: pass/fail/error/skip/xfail + thông báo lỗi
- `--cov-report=json:cov.json` -> file JSON coverage: dòng/nhánh nào chưa chạy

--- Mutation testing ---
Sinh mutant: dùng bộ toán tử đột biến của thư viện **mutmut 2.5.1** (`list_mutations`, `mutate`).
Chạy mutant: tự viết vì mutmut 3 không chạy trên Windows và CLI của mutmut không giới hạn được số mutant.
Để demo chạy nhanh: chỉ đột biến MỘT module đang test, lấy mẫu tối đa `max_mutants` mutant
(cố định seed để các cấu hình so sánh được với nhau), chạy song song vài tiến trình.
"""
import ast
import importlib.util
import json
import os
import random
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from importlib import metadata
from pathlib import Path

from . import python_edit
from .base import (EnvironmentStatus, LanguageAdapter, Mutant, MutationResult, TestCaseResult, TestResult,
                   finish_mutation_result)
from .common import run_subprocess as _run_subprocess
from .common import tail

# ============================================================================ PROMPT RIÊNG CHO PYTHON
# Các đoạn chữ này được chèn vào khung prompt chung (testgen/prompts.py).
# Ghép lại cho ra ĐÚNG TỪNG KÝ TỰ các prompt của bản chỉ-Python trước refactor.
PYTHON_HINTS = {
    "language": "Python",
    "framework": "pytest",
    "fence": "python",
    "spec": "docstring",
    "import_rule": "Module cần test nằm cùng thư mục với file test: dùng `import <module>` hoặc "
                   "`from <module> import ...`.",
    "libs_rule": "Chỉ dùng pytest và thư viện chuẩn. Không đọc/ghi file, không gọi mạng, không sleep.",
    "structure_rule": "Viết các hàm test cấp module (không dùng class), mỗi test kiểm tra một ý, tên hàm mô tả rõ, "
                      "bắt đầu bằng `test_`.",
    "assert_rule": "Dùng `pytest.raises` cho ngoại lệ và `pytest.approx` khi so sánh số thực.",
    "keep_marker": "giữ nguyên các decorator `@pytest.mark.xfail` nếu có",
    "test_id": "tên hàm test",
    "keep_name": "GIỮ NGUYÊN TÊN HÀM TEST",
    "test_unit": "hàm test",
    "impl_details": "ví dụ so sánh danh tính object bằng `is`, kiểu dữ liệu trả về không được nêu, "
                    "class giả tự chế để dò cách cài đặt",
}


# ============================================================================ CHẠY TEST + COVERAGE
def run_subprocess(cmd, cwd, timeout):
    """Chạy lệnh Python với timeout. Trả về None nếu quá thời gian."""
    return _run_subprocess(cmd, cwd, timeout, extra_env={
        "PYTHONPATH": str(cwd),            # để `import <module>` tìm thấy module trong thư mục tạm
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",                 # tránh lỗi mã hoá tiếng Việt trên Windows
    })


def run_tests(module_path, test_code: str, timeout: int = 60, with_coverage: bool = True,
              deselect=None) -> TestResult:
    """Chạy `test_code` với module ở `module_path`. Trả về TestResult.

    deselect: danh sách tên test cần bỏ qua (dùng khi đo mutation chỉ trên các test pass).
    """
    module_path = Path(module_path)
    module_name = module_path.stem
    result = TestResult()

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


def parse_junit(xml_path: Path, result: TestResult):
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


def parse_coverage(json_path: Path, file_name: str, result: TestResult):
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


def describe_missing(source: str, result: TestResult, limit: int = 25) -> str:
    """Mô tả dòng/nhánh chưa phủ bằng lời, kèm nội dung dòng code, để đưa vào prompt.

    Nhánh của coverage.py là cặp [từ dòng, tới dòng]; số âm = thoát khỏi hàm.
    """
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


# ============================================================================ MUTATION TESTING
def _strip_docstrings(tree):
    """Bỏ docstring khỏi cây AST (đột biến trong docstring không làm đổi hành vi -> bỏ qua)."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def generate_mutants(source: str) -> list:
    """Sinh tất cả mutant của mã nguồn bằng toán tử đột biến của mutmut."""
    from mutmut import Context, list_mutations, mutate  # import tại chỗ: thiếu mutmut vẫn chạy được test/coverage

    original_ast = ast.dump(_strip_docstrings(ast.parse(source)))
    original_lines = source.splitlines()
    mutants = []
    for mutation_id in list_mutations(Context(source=source, filename="target.py")):
        new_source, count = mutate(Context(source=source, filename="target.py", mutation_id=mutation_id))
        if count == 0 or new_source == source:
            continue
        try:
            if ast.dump(_strip_docstrings(ast.parse(new_source))) == original_ast:
                continue  # chỉ đổi docstring -> không phải thay đổi hành vi
        except SyntaxError:
            continue
        line_no = mutation_id.line_number + 1  # mutmut đánh số dòng từ 0
        new_lines = new_source.splitlines()
        mutants.append(Mutant(
            id=len(mutants) + 1,
            line=line_no,
            original=original_lines[line_no - 1] if line_no <= len(original_lines) else "",
            mutated=new_lines[line_no - 1] if line_no <= len(new_lines) else "",
            source=new_source,
        ))
    return mutants


def _run_one(mutant: Mutant, module_name: str, test_code: str, timeout: int, deselect) -> str:
    """Chạy bộ test trên MỘT mutant trong thư mục tạm riêng. Trả về trạng thái."""
    work_dir = Path(tempfile.mkdtemp(prefix="mutant_"))
    try:
        (work_dir / f"{module_name}.py").write_text(mutant.source, encoding="utf-8")
        test_file = work_dir / f"test_{module_name}.py"
        test_file.write_text(test_code, encoding="utf-8")
        # -x: dừng ngay khi có test fail đầu tiên (mutant đã bị giết, không cần chạy tiếp)
        cmd = [sys.executable, "-m", "pytest", test_file.name, "-x", "-q", "-p", "no:cacheprovider",
               "--rootdir", str(work_dir)]
        for name in deselect or []:
            cmd += ["--deselect", f"{test_file.name}::{name}"]
        proc = run_subprocess(cmd, work_dir, timeout)
        if proc is None:
            return "timeout"   # mutant làm test chạy mãi (vd. vòng lặp vô hạn) -> coi như bị phát hiện
        return "survived" if proc.returncode == 0 else "killed"
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_mutation_testing(module_path, test_code: str, max_mutants: int = 20, seed: int = 0,
                         timeout: int = 30, workers: int = None, deselect=None,
                         skip_failing: bool = False, exclude_ids=None) -> MutationResult:
    """Chạy mutation testing cho một module với bộ test cho trước.

    skip_failing=True: bỏ qua các test đang FAIL trên code gốc (dùng khi ĐO để so sánh các cấu hình,
    ví dụ baseline có test fail thì mutation score được tính trên các test còn lại).
    exclude_ids: bỏ các mutant có id này (dùng khi chấm: loại các mutant LLM đã được xem trong prompt,
    giống tách tập train/test trong học máy). max_mutants=None: dùng tất cả mutant, không lấy mẫu.
    """
    start = time.time()
    module_path = Path(module_path)
    source = module_path.read_text(encoding="utf-8")
    result = MutationResult()
    deselect = list(deselect or [])

    if importlib.util.find_spec("mutmut") is None:
        result.available = False
        result.error = "Chưa cài mutmut (pip install mutmut==2.5.1) -> bỏ qua mutation testing"
        return result

    if skip_failing:
        first = run_tests(module_path, test_code, with_coverage=False, deselect=deselect)
        deselect += [t.name for t in first.failing_tests()]

    # Điều kiện tiên quyết: bộ test phải PASS trên code gốc (test xfail vẫn được)
    baseline = run_tests(module_path, test_code, with_coverage=False, deselect=deselect)
    if not baseline.ok:
        result.error = "Bộ test chưa pass trên code gốc nên không thể chạy mutation testing"
        return result

    mutants = [m for m in generate_mutants(source) if m.id not in set(exclude_ids or [])]
    result.sampled_from = len(mutants)
    if max_mutants is not None and len(mutants) > max_mutants:
        # Lấy mẫu ngẫu nhiên nhưng CỐ ĐỊNH (seed) -> các cấu hình khác nhau được đo trên cùng tập mutant
        mutants = sorted(random.Random(seed).sample(mutants, max_mutants), key=lambda m: m.id)

    workers = workers or min(4, os.cpu_count() or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        statuses = list(pool.map(
            lambda m: _run_one(m, module_path.stem, test_code, timeout, deselect), mutants))
    for mutant, status in zip(mutants, statuses):
        mutant.status = status

    finish_mutation_result(result, mutants)
    result.duration = round(time.time() - start, 1)
    return result


# ============================================================================ NHÃN MODULE (cho bộ nhớ)
def module_tags(source: str) -> list:
    """Gắn nhãn đặc điểm cho module bằng phân tích AST (dùng để tìm kinh nghiệm liên quan)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    tags = set()
    n_if = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            tags.add("class")
        elif isinstance(node, (ast.Raise, ast.Try)):
            tags.add("exception")
        elif isinstance(node, ast.If):
            n_if += 1
        elif isinstance(node, (ast.For, ast.While)):
            tags.add("loop")
        elif isinstance(node, ast.BoolOp):
            tags.add("compound_condition")
        elif isinstance(node, ast.Attribute) and node.attr in ("split", "strip", "lower", "upper", "join", "replace"):
            tags.add("string")
        elif isinstance(node, ast.Call) and getattr(node.func, "id", "") == "round":
            tags.add("float")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            tags.add("float")
        elif isinstance(node, ast.Dict):
            tags.add("dict")
        elif isinstance(node, ast.Assign) and any(isinstance(t, (ast.Attribute, ast.Subscript)) for t in node.targets):
            tags.add("state")
    if n_if >= 4:
        tags.add("branches")
    return sorted(tags)


# ============================================================================ ADAPTER
def _version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return ""


class PythonAdapter(LanguageAdapter):
    name = "python"
    display_name = "Python"
    file_extensions = (".py",)
    test_framework = "pytest"
    coverage_tool = "coverage.py (pytest-cov)"
    mutation_tool = "mutmut 2.5.1 (toán tử) + runner tự viết"
    code_fence_tags = ("python", "py")        # thẻ khối code chấp nhận trong câu trả lời LLM
    code_markers = ("def test", "import ")    # dấu hiệu "đây là code" khi LLM quên bọc khối

    def check_environment(self) -> EnvironmentStatus:
        tools = {p: _version(p) for p in ("pytest", "pytest-cov", "coverage", "mutmut")}
        problems = [f"thiếu gói Python `{p}`" for p in ("pytest", "pytest-cov", "coverage") if not tools[p]]
        mutation_ok = tools["mutmut"].startswith("2.")
        if not tools["mutmut"]:
            problems.append("thiếu `mutmut` -> không chạy được mutation testing")
        elif not mutation_ok:
            problems.append(f"mutmut {tools['mutmut']} không hỗ trợ (cần 2.5.1; mutmut 3 không chạy trên Windows)")
        return EnvironmentStatus(ok=not any("pytest" in p or "coverage" in p for p in problems),
                                 mutation_available=mutation_ok, tools=tools, problems=problems,
                                 install_hint="pip install -r requirements.txt")

    def test_file_path(self, source_file, out_dir=None) -> Path:
        source_file = Path(source_file)
        return Path(out_dir or source_file.parent) / f"test_{source_file.stem}.py"

    def prompt_hints(self, source_file=None) -> dict:
        return dict(PYTHON_HINTS)

    def run_tests(self, source_file, test_code, timeout=60, with_coverage=True, deselect=None) -> TestResult:
        return run_tests(source_file, test_code, timeout=timeout, with_coverage=with_coverage, deselect=deselect)

    def run_mutation(self, source_file, test_code, max_mutants=20, seed=0, timeout=30, deselect=None,
                     skip_failing=False, exclude_ids=None) -> MutationResult:
        return run_mutation_testing(source_file, test_code, max_mutants=max_mutants, seed=seed, timeout=timeout,
                                    deselect=deselect, skip_failing=skip_failing, exclude_ids=exclude_ids)

    def describe_missing(self, source, result, limit=25) -> str:
        return describe_missing(source, result, limit)

    # ---- đọc / sửa file test: dùng ast (python_edit.py)
    def is_valid(self, code):
        return python_edit.is_valid_python(code)

    def test_names(self, code):
        return python_edit.test_function_names(code)

    def get_tests_code(self, code, names):
        return python_edit.get_functions_code(code, names)

    def remove_tests(self, code, names):
        return python_edit.remove_functions(code, names)

    def merge_tests(self, base, new, on_conflict="rename"):
        return python_edit.merge_tests(base, new, on_conflict=on_conflict)

    def add_suspected_marker(self, code, test_name, reason):
        return python_edit.add_suspected_marker(code, test_name, reason)

    def suspected_tests(self, code):
        return python_edit.suspected_tests(code)

    def base_test_name(self, name):
        return python_edit.base_test_name(name)

    def module_tags(self, source):
        return module_tags(source)
