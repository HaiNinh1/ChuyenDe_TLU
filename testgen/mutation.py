"""Mutation testing: "cài lỗi nhân tạo" vào code rồi xem bộ test có phát hiện được không.

- Mutant = một bản sao của module bị sửa NHẸ đúng một chỗ, ví dụ `a > 0` -> `a >= 0`, `+` -> `-`, `True` -> `False`.
- Chạy bộ test trên mutant:
      test FAIL  -> mutant bị "giết" (killed)  -> tốt, bộ test đủ nhạy
      test PASS  -> mutant "sống sót" (survived) -> bộ test chưa kiểm tra kỹ chỗ đó
- Mutation score = số mutant bị giết / tổng số mutant.

Sinh mutant: dùng bộ toán tử đột biến của thư viện **mutmut 2.5.1** (`list_mutations`, `mutate`).
Chạy mutant: tự viết (bên dưới) vì mutmut 3 không chạy trên Windows và CLI của mutmut không giới hạn
được số mutant. Để demo chạy nhanh: chỉ đột biến MỘT module đang test, lấy mẫu tối đa `max_mutants` mutant
(cố định seed để các cấu hình so sánh được với nhau), chạy song song vài tiến trình.

Chạy thử:
    python -m testgen.mutation targets/grading.py generated_tests/baseline/test_grading.py
"""
import ast
import os
import random
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mutmut import Context, list_mutations, mutate

# Dataclass kết quả dùng chung cho mọi ngôn ngữ (xem adapters/base.py)
from adapters.base import Mutant, MutationResult, finish_mutation_result

from .runner import run_subprocess, run_tests


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


def describe_survivors(result: MutationResult, limit: int = 6) -> str:
    """Mô tả các mutant còn sống để đưa vào prompt."""
    return "\n".join("- " + m.describe() for m in result.survivors()[:limit]) or "(không có)"


if __name__ == "__main__":
    module, tests = sys.argv[1], sys.argv[2]
    res = run_mutation_testing(module, Path(tests).read_text(encoding="utf-8"), max_mutants=30,
                               skip_failing=True)
    if res.error:
        print("LỖI:", res.error)
    print(f"Mutation score: {res.score}% ({res.killed + res.timeout}/{res.total} bị giết, "
          f"lấy mẫu từ {res.sampled_from} mutant, {res.duration}s)")
    print("Mutant còn sống:\n" + describe_survivors(res, limit=50))
