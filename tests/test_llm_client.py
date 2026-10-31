import pytest

from testgen.config import Settings, load_settings
from testgen.llm_client import LLMClient, LLMError, LLMReply


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


class FakeStatusError(Exception):
    def __init__(self, status_code):
        super().__init__(f"lỗi {status_code}")
        self.status_code = status_code


def client_with_keys(monkeypatch, responses):
    """Client có 3 key; `responses` cho biết mỗi key trả lỗi gì (None = chạy được). Trả về client + các key đã dùng."""
    client = LLMClient(settings=mock_settings(api_key="k1", api_keys=["k1", "k2", "k3"]))
    used = []

    def fake_call(system, user, task):
        key = client.settings.api_key
        used.append(key)
        if responses[key] is not None:
            raise FakeStatusError(responses[key])
        return LLMReply(text=f"trả lời từ {key}")

    monkeypatch.setattr(client, "_call_once", fake_call)
    monkeypatch.setattr("time.sleep", lambda s: None)
    return client, used


@pytest.mark.parametrize("status", [401, 402, 429])
def test_key_problem_switches_to_next_key(monkeypatch, status):
    client, used = client_with_keys(monkeypatch, {"k1": status, "k2": None, "k3": None})
    assert client.chat("s", "u") == "trả lời từ k2"
    assert used == ["k1", "k2"]
    assert client.history[0].attempts == 1  # đổi key không tính là một lần retry


def test_working_key_is_kept_for_next_calls(monkeypatch):
    client, used = client_with_keys(monkeypatch, {"k1": 429, "k2": 429, "k3": None})
    client.chat("s", "u")
    client.chat("s", "u")
    assert used == ["k1", "k2", "k3", "k3"]  # lần gọi sau không thử lại key đã hết


def test_all_keys_exhausted_raises_llm_error(monkeypatch):
    client, _ = client_with_keys(monkeypatch, {"k1": 402, "k2": 402, "k3": 402})
    with pytest.raises(LLMError, match="402"):
        client.chat("s", "u")


def test_other_error_does_not_switch_key(monkeypatch):
    client, used = client_with_keys(monkeypatch, {"k1": 404, "k2": None, "k3": None})
    with pytest.raises(LLMError, match="404"):  # sai tên model: đổi key cũng vô ích
        client.chat("s", "u")
    assert used == ["k1"]


def test_load_settings_reads_comma_separated_keys(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k1, k2 ,k3,")
    settings = load_settings(provider="openrouter")
    assert settings.api_keys == ["k1", "k2", "k3"]
    assert settings.api_key == "k1"


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
