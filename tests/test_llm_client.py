import pytest

from testgen.config import Settings, load_settings
from testgen.llm_client import LLMClient, LLMError


def mock_settings(**kw):
    return Settings(provider="mock", model="mock", max_retries=2, **kw)


def test_mock_scripted_responses_in_order():
    client = LLMClient(settings=mock_settings(), mock_responses=["một", "hai"])
    assert client.chat("sys", "user") == "một"
    assert client.chat("sys", "user") == "hai"
    assert client.call_count == 2
    assert client.stats()["llm_calls"] == 2


def test_mock_default_response_uses_module_name():
    client = LLMClient(settings=mock_settings())
    text = client.chat("sys", "Tên module: `grading`\n...", task="initial")
    assert "import grading" in text


def test_retry_then_success(monkeypatch):
    client = LLMClient(settings=mock_settings())
    calls = {"n": 0}

    def flaky(system, user, task):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("mạng chập chờn")
        from testgen.llm_client import LLMReply
        return LLMReply(text="ok")

    monkeypatch.setattr(client, "_call_once", flaky)
    monkeypatch.setattr("time.sleep", lambda s: None)  # không chờ thật khi test
    assert client.chat("s", "u") == "ok"
    assert client.history[0].attempts == 2


def test_non_retryable_error_fails_fast(monkeypatch):
    client = LLMClient(settings=mock_settings())

    class PaymentError(Exception):
        status_code = 402

    def broke(system, user, task):
        raise PaymentError("hết tiền")

    monkeypatch.setattr(client, "_call_once", broke)
    with pytest.raises(LLMError, match="402"):
        client.chat("s", "u")


def test_missing_api_key_raises():
    client = LLMClient(settings=Settings(provider="deepseek", model="deepseek-chat", max_retries=1))
    with pytest.raises(LLMError):
        client.chat("s", "u")


def test_load_settings_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_MODEL", "")
    settings = load_settings()
    assert settings.model == "deepseek-chat"
    assert settings.base_url == "https://api.deepseek.com"


def test_load_settings_rejects_unknown_provider():
    with pytest.raises(ValueError):
        load_settings(provider="khong-ton-tai")
