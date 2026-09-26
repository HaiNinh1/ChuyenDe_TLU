"""Registry: nhận diện ngôn ngữ theo đuôi file và trả về adapter tương ứng.

    adapter = adapter_for_file("targets/python/grading.py")    # -> PythonAdapter
    adapter = get_adapter("javascript")                        # -> JavaScriptAdapter

Thêm ngôn ngữ mới: viết lớp adapter rồi gọi register(...) ở cuối file này.
"""
import re
from pathlib import Path

from .base import LanguageAdapter

_ADAPTERS = {}   # {tên ngôn ngữ: đối tượng adapter}


class UnsupportedLanguageError(ValueError):
    """Đuôi file / tên ngôn ngữ chưa có adapter."""


def register(adapter: LanguageAdapter) -> LanguageAdapter:
    """Đăng ký một adapter (mỗi ngôn ngữ một đối tượng dùng chung)."""
    _ADAPTERS[adapter.name] = adapter
    return adapter


def all_adapters() -> list:
    return list(_ADAPTERS.values())


def supported_extensions() -> list:
    return [ext for a in _ADAPTERS.values() for ext in a.file_extensions]


def get_adapter(name: str) -> LanguageAdapter:
    try:
        return _ADAPTERS[name.lower()]
    except KeyError:
        raise UnsupportedLanguageError(f"Chưa hỗ trợ ngôn ngữ '{name}'. Đang hỗ trợ: {list(_ADAPTERS)}") from None


def adapter_for_file(path) -> LanguageAdapter:
    """Chọn adapter theo đuôi file (.py -> Python, .js/.ts -> JavaScript)."""
    suffix = Path(path).suffix.lower()
    for adapter in _ADAPTERS.values():
        if suffix in adapter.file_extensions:
            return adapter
    raise UnsupportedLanguageError(
        f"Không nhận diện được ngôn ngữ của '{Path(path).name}' (đuôi '{suffix}'). "
        f"Các đuôi được hỗ trợ: {', '.join(supported_extensions())}")


def detect_language(code: str) -> str:
    """Đoán đuôi file của đoạn code người dùng DÁN vào giao diện: ".py", ".js" hoặc ".ts".

    Heuristic đơn giản (đếm dấu hiệu đặc trưng), không phải bộ phân tích cú pháp -> có thể đoán sai
    với đoạn code rất ngắn; giao diện luôn cho người dùng chọn lại.
    """
    python_signs = len(re.findall(r"^\s*(def |class \w+.*:\s*$|import \w+\s*$|from \w+ import|elif |"
                                  r"@\w+|\"\"\")", code, flags=re.MULTILINE))
    js_signs = len(re.findall(r"(\bfunction\b|\bconst\b|\blet\b|=>|\bexport\b|\bmodule\.exports\b|"
                              r"\brequire\(|;\s*$|\bthis\.)", code, flags=re.MULTILINE))
    ts_signs = len(re.findall(r"(\binterface\s+\w+|\btype\s+\w+\s*=|:\s*(number|string|boolean|void)\b|"
                              r"\bpublic\b|\bprivate\b|\breadonly\b)", code))
    if python_signs > js_signs:
        return ".py"
    if js_signs == 0 and python_signs == 0:
        return ".py"
    return ".ts" if ts_signs > 0 else ".js"
