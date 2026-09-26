"""adapters — mỗi ngôn ngữ lập trình là một "phích cắm" (Adapter) cho agent.

    base.py                 lớp trừu tượng LanguageAdapter + dataclass kết quả dùng chung
    registry.py             đuôi file -> adapter
"""
from .base import (CoverageResult, EnvironmentStatus, LanguageAdapter, Mutant, MutationResult, RunResult,
                   TestCaseResult, TestResult)
from .registry import (UnsupportedLanguageError, adapter_for_file, all_adapters, detect_language, get_adapter,
                       register, supported_extensions)

__all__ = ["CoverageResult", "EnvironmentStatus", "LanguageAdapter", "Mutant", "MutationResult", "RunResult",
           "TestCaseResult", "TestResult", "UnsupportedLanguageError", "adapter_for_file", "all_adapters",
           "detect_language", "get_adapter", "register", "supported_extensions"]
