"""BASELINE: sinh test MỘT LẦN (không có vòng lặp phản hồi).

Đây là mốc so sánh (cấu hình A trong thực nghiệm): gửi mã nguồn cho LLM, nhận file test, lưu lại. Hết.
Ngôn ngữ được nhận diện theo đuôi file (adapter), prompt dùng khung chung + phần riêng của ngôn ngữ.

Chạy thử:
    python -m testgen.generator targets/python/calculator.py
    python -m testgen.generator targets/javascript/string_tools.js
    python -m testgen.generator --all
"""
import argparse
import time
from pathlib import Path

from adapters import LanguageAdapter, adapter_for_file, supported_extensions

from . import code_utils as cu
from . import prompts
from .config import ROOT_DIR
from .llm_client import LLMClient

TARGETS_DIR = ROOT_DIR / "targets"
BASELINE_DIR = ROOT_DIR / "generated_tests" / "baseline"


def generate_tests(module_path, client: LLMClient, lessons: str = "", adapter: LanguageAdapter = None) -> str:
    """Gọi LLM một lần để sinh file test cho module. Trả về code test (chuỗi)."""
    module_path = Path(module_path)
    adapter = adapter or adapter_for_file(module_path)
    hints = adapter.prompt_hints(module_path)
    source = module_path.read_text(encoding="utf-8")
    user_prompt = prompts.initial_prompt(hints, adapter.module_name(module_path), source, lessons)
    answer = client.chat(prompts.system_prompt(hints), user_prompt, task="initial")
    return cu.extract_code(answer, adapter.code_fence_tags, adapter.code_markers)


def save_tests(test_code: str, module_path, out_dir: Path = BASELINE_DIR) -> Path:
    """Lưu file test theo quy ước tên của ngôn ngữ (test_x.py / x.test.js)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = adapter_for_file(module_path).test_file_path(module_path, out_dir)
    path.write_text(test_code, encoding="utf-8")
    return path


def all_targets() -> list:
    """Mọi file mã nguồn mục tiêu trong targets/ (mọi ngôn ngữ được hỗ trợ)."""
    return sorted(p for p in TARGETS_DIR.rglob("*")
                  if p.suffix in supported_extensions() and ".test." not in p.name and not p.name.startswith("test_"))


def main():
    parser = argparse.ArgumentParser(description="Baseline: sinh test một lần bằng LLM")
    parser.add_argument("modules", nargs="*", help="đường dẫn module, ví dụ targets/python/calculator.py")
    parser.add_argument("--all", action="store_true", help="sinh test cho mọi module trong targets/")
    args = parser.parse_args()

    paths = all_targets() if args.all else [Path(m) for m in args.modules]
    if not paths:
        parser.error("Cần chỉ ra module hoặc dùng --all")

    client = LLMClient()
    print(f"Dùng LLM: {client.settings.provider} / {client.settings.model}")
    for path in paths:
        start = time.time()
        code = generate_tests(path, client)
        out = save_tests(code, path)
        print(f"  {path.name}: {len(code.splitlines())} dòng test -> {out} ({time.time() - start:.1f}s)")
    print("Thống kê LLM:", client.stats())


if __name__ == "__main__":
    main()
