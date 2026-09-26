"""Đọc cấu hình LLM từ file .env (hoặc biến môi trường).

Muốn đổi nhà cung cấp chỉ cần sửa .env, không phải sửa code.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Thư mục gốc của dự án (chứa .env, targets/, ...)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Model mặc định cho từng nhà cung cấp (dùng khi LLM_MODEL để trống)
DEFAULT_MODELS = {
    "openrouter": "z-ai/glm-5.2",
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "ollama": "qwen2.5-coder:7b",
    "mock": "mock",
}

# Địa chỉ API của các nhà cung cấp dùng chung giao thức OpenAI
OPENAI_COMPATIBLE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com",
    "openai": None,  # None = dùng địa chỉ mặc định của thư viện openai
}

# Tên biến môi trường chứa API key của từng nhà cung cấp
API_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


@dataclass
class Settings:
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.2
    max_tokens: int = 8000
    timeout: int = 180
    max_retries: int = 3


def load_settings(provider: str = None, model: str = None) -> Settings:
    """Đọc cấu hình. Tham số truyền vào (nếu có) được ưu tiên hơn file .env."""
    load_dotenv(ROOT_DIR / ".env")

    provider = (provider or os.getenv("LLM_PROVIDER", "mock")).strip().lower()
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"LLM_PROVIDER không hợp lệ: {provider}. Chọn một trong {list(DEFAULT_MODELS)}")

    model = model or os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODELS[provider]

    api_key = ""
    if provider in API_KEY_ENV:
        api_key = os.getenv(API_KEY_ENV[provider], "").strip()

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    else:
        base_url = OPENAI_COMPATIBLE_URLS.get(provider) or ""

    return Settings(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8000")),
        timeout=int(os.getenv("LLM_TIMEOUT", "180")),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
    )
