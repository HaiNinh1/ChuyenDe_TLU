"""Gọi LLM với nhiều nhà cung cấp, có retry và thống kê số lần gọi / token / chi phí.

Cách dùng:
    client = LLMClient()                       # đọc cấu hình từ .env
    text = client.chat(system_prompt, user_prompt, task="initial")

Thêm nhà cung cấp mới: viết một hàm _call_xxx(system, user) trả về LLMReply rồi thêm vào _call_once.
"""
import json
import re
import time
from dataclasses import dataclass, field

from .config import Settings, load_settings


class LLMError(Exception):
    """Lỗi khi gọi LLM (đã thử lại mà vẫn thất bại)."""


# Mã lỗi HTTP không nên thử lại: 400 sai yêu cầu, 401 sai key, 402 hết tiền, 403 bị cấm, 404 sai model
NON_RETRYABLE_STATUS = {400, 401, 402, 403, 404}


@dataclass
class LLMReply:
    """Kết quả một lần gọi LLM."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0  # USD, chỉ OpenRouter trả về trực tiếp; nhà cung cấp khác để 0


@dataclass
class CallRecord:
    """Ghi lại một lần gọi để thống kê (số lần gọi LLM là một chỉ số thực nghiệm)."""
    task: str
    seconds: float
    input_tokens: int
    output_tokens: int
    cost: float
    attempts: int


@dataclass
class LLMClient:
    settings: Settings = None
    mock_responses: list = field(default_factory=list)  # chỉ dùng cho provider "mock"
    history: list = field(default_factory=list)

    def __post_init__(self):
        if self.settings is None:
            self.settings = load_settings()
        self._sdk_client = None  # tạo lười (lazy) khi gọi lần đầu

    # ------------------------------------------------------------------ API chính
    def chat(self, system: str, user: str, task: str = "chat") -> str:
        """Gửi prompt, trả về văn bản. Thử lại tối đa `max_retries` lần với thời gian chờ tăng dần."""
        last_error = None
        start = time.time()
        for attempt in range(1, self.settings.max_retries + 1):
            try:
                reply = self._call_once(system, user, task)
                if not reply.text.strip():
                    raise LLMError("LLM trả về nội dung rỗng")
                self.history.append(CallRecord(
                    task=task,
                    seconds=round(time.time() - start, 2),
                    input_tokens=reply.input_tokens,
                    output_tokens=reply.output_tokens,
                    cost=reply.cost,
                    attempts=attempt,
                ))
                return reply.text
            except Exception as exc:  # lỗi mạng, rate limit, timeout, ...
                last_error = exc
                message = str(exc)[:300]  # thông báo lỗi có thể rất dài -> cắt bớt
                status = getattr(exc, "status_code", None)
                if status in NON_RETRYABLE_STATUS:
                    # Sai key / hết tiền / sai tên model: thử lại cũng vô ích -> báo lỗi ngay
                    raise LLMError(f"Lỗi {status} từ {self.settings.provider}: {message}") from exc
                if attempt < self.settings.max_retries:
                    wait = 2 ** attempt  # 2s, 4s, 8s ... (exponential backoff)
                    print(f"[llm] Lỗi lần {attempt}: {message} -> thử lại sau {wait}s")
                    time.sleep(wait)
        raise LLMError(f"Gọi LLM thất bại sau {self.settings.max_retries} lần: {str(last_error)[:300]}")

    # --------------------------------------------------------------- thống kê
    @property
    def call_count(self) -> int:
        return len(self.history)

    def stats(self) -> dict:
        return {
            "llm_calls": len(self.history),
            "input_tokens": sum(r.input_tokens for r in self.history),
            "output_tokens": sum(r.output_tokens for r in self.history),
            "cost_usd": round(sum(r.cost for r in self.history), 6),
            "llm_seconds": round(sum(r.seconds for r in self.history), 1),
        }

    # ------------------------------------------------------- gọi từng nhà cung cấp
    def _call_once(self, system: str, user: str, task: str) -> LLMReply:
        provider = self.settings.provider
        if provider in ("openrouter", "deepseek", "openai"):
            return self._call_openai_compatible(system, user)
        if provider == "anthropic":
            return self._call_anthropic(system, user)
        if provider == "ollama":
            return self._call_ollama(system, user)
        if provider == "mock":
            return self._call_mock(system, user, task)
        raise LLMError(f"Nhà cung cấp chưa hỗ trợ: {provider}")

    def _call_openai_compatible(self, system: str, user: str) -> LLMReply:
        """OpenAI, DeepSeek và OpenRouter dùng chung giao thức -> chỉ khác base_url và key."""
        if not self.settings.api_key:
            raise LLMError(f"Thiếu API key cho {self.settings.provider} trong file .env")
        if self._sdk_client is None:
            from openai import OpenAI  # import lười: chỉ cần cài khi dùng
            self._sdk_client = OpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.base_url or None,
                timeout=self.settings.timeout,
                max_retries=0,  # retry do chính mình xử lý ở hàm chat()
            )
        response = self._sdk_client.chat.completions.create(
            model=self.settings.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )
        usage = response.usage
        cost = 0.0
        if usage is not None and getattr(usage, "model_extra", None):
            cost = float(usage.model_extra.get("cost") or 0.0)  # OpenRouter trả về chi phí thật
        return LLMReply(
            text=response.choices[0].message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cost=cost,
        )

    def _call_anthropic(self, system: str, user: str) -> LLMReply:
        if not self.settings.api_key:
            raise LLMError("Thiếu ANTHROPIC_API_KEY trong file .env")
        if self._sdk_client is None:
            import anthropic
            self._sdk_client = anthropic.Anthropic(
                api_key=self.settings.api_key, timeout=self.settings.timeout, max_retries=0
            )
        response = self._sdk_client.messages.create(
            model=self.settings.model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMReply(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def _call_ollama(self, system: str, user: str) -> LLMReply:
        import requests
        response = requests.post(
            f"{self.settings.base_url}/api/chat",
            json={
                "model": self.settings.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False,
                "options": {"temperature": self.settings.temperature},
            },
            timeout=self.settings.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return LLMReply(
            text=data["message"]["content"],
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )

    def _call_mock(self, system: str, user: str, task: str) -> LLMReply:
        """LLM GIẢ LẬP để kiểm tra pipeline khi không có mạng/API key.

        - Nếu có `mock_responses` (danh sách chuỗi) -> lần lượt trả về từng chuỗi (dùng trong unit test).
        - Nếu hết -> trả về một câu trả lời mặc định rất đơn giản theo loại task.
        KHÔNG dùng kết quả mock làm kết quả thực nghiệm.
        """
        if self.mock_responses:
            return LLMReply(text=self.mock_responses.pop(0))
        match = re.search(r"Tên module: `?(\w+)`?", user)
        module = match.group(1) if match else "module"
        if task == "classify":
            return LLMReply(text=json.dumps({"verdicts": []}))
        return LLMReply(text=(
            "```python\n"
            f"import {module}\n\n\n"
            f"def test_mock_module_imports():\n"
            f"    assert {module} is not None\n"
            "```\nLESSON: (mock) không có bài học.\n"
        ))
