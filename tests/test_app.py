"""Kiểm tra giao diện Streamlit chạy không lỗi (dùng AppTest, không cần mở trình duyệt)."""
import json

import pytest
from streamlit.testing.v1 import AppTest

from adapters import get_adapter
from testgen import agent as agent_module
from testgen.config import ROOT_DIR

APP = str(ROOT_DIR / "app.py")
needs_node = pytest.mark.skipif(not get_adapter("javascript").check_environment().ok,
                                reason="Chưa cài Node.js/Jest (npm install)")

# Thanh bên, chế độ "Chạy mới" + "Module mẫu": selectbox[0] = ngôn ngữ, [1] = module, [2] = nhà cung cấp LLM
LANG, MODULE, PROVIDER = 0, 1, 2


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    return tmp_path


def run_mock(at):
    at.sidebar.checkbox[0].set_value(False)                 # tắt mutation cho nhanh
    at.sidebar.selectbox[PROVIDER].set_value("mock")        # nhà cung cấp = mock
    at.sidebar.button[0].click().run()
    return at


def test_app_starts_without_error(isolated):
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert len(at.tabs) >= 5
    assert any("pytest" in info.value for info in at.sidebar.info)   # hiển thị công cụ của ngôn ngữ


def test_run_new_with_mock_llm(isolated):
    at = run_mock(AppTest.from_file(APP, default_timeout=180).run())
    assert not at.exception
    assert any("Kết thúc" in s.value for s in at.success)
    assert list((isolated / "logs").glob("*.json"))


@needs_node
def test_run_javascript_module_with_mock_llm(isolated):
    at = AppTest.from_file(APP, default_timeout=240).run()
    at.sidebar.selectbox[LANG].select_index(
        [o for o in at.sidebar.selectbox[LANG].options].index("JavaScript/TypeScript")).run()
    assert any("Jest" in info.value for info in at.sidebar.info)
    at = run_mock(at)
    assert not at.exception
    log = json.loads(next((isolated / "logs").glob("*.json")).read_text(encoding="utf-8"))
    assert log["language"] == "javascript"


def test_pasted_code_language_is_detected(isolated):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[1].set_value("Dán code").run()
    at.sidebar.text_area[0].set_value("export function add(a: number, b: number): number {\n  return a + b;\n}\n").run()
    assert not at.exception
    assert "TypeScript (tự nhận diện)" in at.sidebar.selectbox[0].options
    assert any("Jest" in info.value for info in at.sidebar.info)


def test_replay_mode(isolated):
    # Tạo một log mẫu rồi phát lại
    at = run_mock(AppTest.from_file(APP, default_timeout=180).run())
    log = next((isolated / "logs").glob("*.json"))
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["iterations"]

    at.sidebar.radio[0].set_value("REPLAY từ log").run()
    assert not at.exception


@pytest.mark.parametrize("language", ["python", "javascript"])
def test_replay_real_log_plays_all_iterations(isolated, language):
    """Phát lại một log THẬT đã lưu (có sẵn log mẫu cho cả Python và JavaScript)."""
    logs = [p for p in sorted((ROOT_DIR / "logs").glob("*.json"))
            if json.loads(p.read_text(encoding="utf-8")).get("language", "python") == language]
    if not logs:
        pytest.skip(f"chưa có log thật của {language} trong logs/")
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.sidebar.radio[0].set_value("REPLAY từ log").run()
    box = at.sidebar.selectbox[0]
    box.select_index([str(o) for o in box.options].index(f"[{language}] {logs[-1].name}")).run()
    at.sidebar.slider[0].set_value(0.0)
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("REPLAY" in s.value for s in at.subheader)
    assert any("Kết thúc" in s.value for s in at.success)
