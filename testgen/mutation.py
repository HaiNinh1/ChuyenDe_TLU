"""Cổng chung cho MUTATION TESTING: "cài lỗi nhân tạo" vào code rồi xem bộ test có phát hiện được không.

- Mutant = một bản sao của module bị sửa NHẸ đúng một chỗ, ví dụ `a > 0` -> `a >= 0`, `+` -> `-`, `True` -> `False`.
- Chạy bộ test trên mutant:
      test FAIL  -> mutant bị "giết" (killed)  -> tốt, bộ test đủ nhạy
      test PASS  -> mutant "sống sót" (survived) -> bộ test chưa kiểm tra kỹ chỗ đó
- Mutation score = số mutant bị giết / tổng số mutant.

Công cụ cụ thể do adapter quyết định:
    Python      -> toán tử đột biến của mutmut 2.5.1 + runner tự viết   (adapters/python_adapter.py)
    JavaScript  -> StrykerJS                                           (adapters/javascript_adapter.py)

Chạy thử:
    python -m testgen.mutation targets/python/grading.py generated_tests/baseline/test_grading.py
"""
import sys
from pathlib import Path

from adapters import adapter_for_file
from adapters.base import Mutant, MutationResult  # noqa: F401  (dataclass dùng chung)


def run_mutation_testing(source_file, test_code: str, max_mutants: int = 20, seed: int = 0, timeout: int = 30,
                         deselect=None, skip_failing: bool = False, exclude_ids=None) -> MutationResult:
    """Chạy mutation testing bằng adapter phù hợp với đuôi file (xem LanguageAdapter.run_mutation)."""
    return adapter_for_file(source_file).run_mutation(
        source_file, test_code, max_mutants=max_mutants, seed=seed, timeout=timeout, deselect=deselect,
        skip_failing=skip_failing, exclude_ids=exclude_ids)


def describe_survivors(result: MutationResult, limit: int = 6) -> str:
    """Mô tả các mutant còn sống để đưa vào prompt (dùng chung mọi ngôn ngữ)."""
    return "\n".join("- " + m.describe() for m in result.survivors()[:limit]) or "(không có)"


if __name__ == "__main__":
    import testgen  # noqa: F401  (UTF-8 cho console Windows)

    source, tests = sys.argv[1], sys.argv[2]
    print(f"Công cụ: {adapter_for_file(source).describe_tools()}")
    res = run_mutation_testing(source, Path(tests).read_text(encoding="utf-8"), max_mutants=30,
                               skip_failing=True)
    if res.error:
        print("LỖI:", res.error)
    print(f"Mutation score: {res.score}% ({res.killed + res.timeout}/{res.total} bị giết, "
          f"lấy mẫu từ {res.sampled_from} mutant, {res.duration}s)")
    print("Mutant còn sống:\n" + describe_survivors(res, limit=50))
