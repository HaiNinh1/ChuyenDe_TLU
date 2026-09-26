"""BASELINE: sinh test MỘT LẦN (không có vòng lặp phản hồi).

Đây là mốc so sánh (cấu hình A trong thực nghiệm): gửi mã nguồn cho LLM, nhận file test, lưu lại. Hết.

Chạy thử:
    python -m testgen.generator targets/calculator.py
    python -m testgen.generator --all
"""
import argparse
import time
from pathlib import Path

from . import prompts
from .code_utils import extract_code
from .config import ROOT_DIR
from .llm_client import LLMClient

TARGETS_DIR = ROOT_DIR / "targets"
BASELINE_DIR = ROOT_DIR / "generated_tests" / "baseline"


def generate_tests(module_path, client: LLMClient, lessons: str = "") -> str:
    """Gọi LLM một lần để sinh file test cho module. Trả về code test (chuỗi)."""
    module_path = Path(module_path)
    source = module_path.read_text(encoding="utf-8")
    user_prompt = prompts.initial_prompt(module_path.stem, source, lessons)
    answer = client.chat(prompts.SYSTEM_PROMPT, user_prompt, task="initial")
    return extract_code(answer)


def save_tests(test_code: str, module_name: str, out_dir: Path = BASELINE_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"test_{module_name}.py"
    path.write_text(test_code, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="Baseline: sinh test một lần bằng LLM")
    parser.add_argument("modules", nargs="*", help="đường dẫn module, ví dụ targets/calculator.py")
    parser.add_argument("--all", action="store_true", help="sinh test cho mọi module trong targets/")
    args = parser.parse_args()

    paths = sorted(TARGETS_DIR.glob("*.py")) if args.all else [Path(m) for m in args.modules]
    if not paths:
        parser.error("Cần chỉ ra module hoặc dùng --all")

    client = LLMClient()
    print(f"Dùng LLM: {client.settings.provider} / {client.settings.model}")
    for path in paths:
        start = time.time()
        code = generate_tests(path, client)
        out = save_tests(code, path.stem)
        print(f"  {path.name}: {len(code.splitlines())} dòng test -> {out} ({time.time() - start:.1f}s)")
    print("Thống kê LLM:", client.stats())


if __name__ == "__main__":
    main()
