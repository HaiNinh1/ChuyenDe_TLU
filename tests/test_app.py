"""Kiểm tra giao diện Streamlit chạy không lỗi (dùng AppTest, không cần mở trình duyệt)."""
import json

import pytest
from streamlit.testing.v1 import AppTest

from testgen import agent as agent_module
from testgen.config import ROOT_DIR

APP = str(ROOT_DIR / "app.py")


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    return tmp_path


def test_app_starts_without_error(isolated):
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert len(at.tabs) == 5


def test_run_new_with_mock_llm(isolated):
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.sidebar.checkbox[0].set_value(False)          # tắt mutation cho nhanh
    at.sidebar.selectbox[1].set_value("mock")         # nhà cung cấp = mock
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Kết thúc" in s.value for s in at.success)
    assert list((isolated / "logs").glob("*.json"))


def test_replay_mode(isolated):
    # Tạo một log mẫu rồi phát lại
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.sidebar.checkbox[0].set_value(False)
    at.sidebar.selectbox[1].set_value("mock")
    at.sidebar.button[0].click().run()
    log = next((isolated / "logs").glob("*.json"))
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["iterations"]

    at.sidebar.radio[0].set_value("REPLAY từ log").run()
    assert not at.exception


def test_replay_real_log_plays_all_iterations(isolated):
    logs = sorted((ROOT_DIR / "logs").glob("*.json"))
    if not logs:
        pytest.skip("chưa có log thật trong logs/")
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.sidebar.radio[0].set_value("REPLAY từ log").run()
    at.sidebar.slider[0].set_value(0.0)
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("REPLAY" in s.value for s in at.subheader)
    assert any("Kết thúc" in s.value for s in at.success)
