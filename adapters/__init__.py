"""adapters — mỗi ngôn ngữ lập trình là một "phích cắm" (Adapter) cho agent.

    base.py                 lớp trừu tượng LanguageAdapter + dataclass kết quả dùng chung
    registry.py             đuôi file -> adapter
    common.py               tiện ích chung (chạy tiến trình con có timeout...)
    python_adapter.py       Python: pytest + coverage.py + mutmut      (python_edit.py: sửa file test bằng ast)
    javascript_adapter.py   JS/TS: Jest + Istanbul + StrykerJS          (js_edit.py: sửa file test bằng bộ quét ngoặc)
"""
from .base import (CoverageResult, EnvironmentStatus, LanguageAdapter, Mutant, MutationResult, RunResult,
                   TestCaseResult, TestResult)
from .registry import (UnsupportedLanguageError, adapter_for_file, all_adapters, detect_language, get_adapter,
                       register, supported_extensions)

__all__ = ["CoverageResult", "EnvironmentStatus", "LanguageAdapter", "Mutant", "MutationResult", "RunResult",
           "TestCaseResult", "TestResult", "UnsupportedLanguageError", "adapter_for_file", "all_adapters",
           "detect_language", "get_adapter", "register", "supported_extensions"]

# ---- Đăng ký các ngôn ngữ được hỗ trợ (thêm ngôn ngữ mới: thêm một dòng register) ----
from .javascript_adapter import JavaScriptAdapter  # noqa: E402
from .python_adapter import PythonAdapter  # noqa: E402

register(PythonAdapter())
register(JavaScriptAdapter())
