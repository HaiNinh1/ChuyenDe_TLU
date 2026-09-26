import json
from pathlib import Path

from testgen import agent as agent_module
from testgen.agent import AgentConfig, TestGenAgent
from testgen.config import Settings
from testgen.llm_client import LLMClient
from adapters.python_adapter import module_tags
from testgen.memory import Memory, error_type

from test_agent import MODULE, SCRIPT

ROOT = Path(__file__).resolve().parent.parent


def test_module_tags_reflect_code_features():
    grading = module_tags((ROOT / "targets" / "python" / "grading.py").read_text(encoding="utf-8"))
    cart = module_tags((ROOT / "targets" / "python" / "shopping_cart.py").read_text(encoding="utf-8"))
    assert {"branches", "exception", "compound_condition"} <= set(grading)
    assert {"class", "state", "dict"} <= set(cart)


def test_error_type():
    assert error_type("E   ModuleNotFoundError: No module named 'x'") == "ModuleNotFoundError"
    assert error_type("không có gì") == "Other"


def test_add_lesson_deduplicates_and_persists(tmp_path):
    mem = Memory(tmp_path / "m.json")
    mem.add_lesson("ImportError: x", "Luôn import đúng tên module được cung cấp", "a", ["class"])
    mem.add_lesson("ImportError: y", "Luôn import đúng tên module được cung cấp.", "b", ["class"])
    mem.add_lesson("AssertionError", "(mock) không có bài học.", "c", [])  # bị bỏ qua
    assert len(mem.lessons) == 1 and mem.lessons[0]["times_seen"] == 2
    mem.save()
    assert Memory(tmp_path / "m.json").stats() == {"lessons": 1, "good_tests": 0}


def test_relevant_lessons_prefers_same_error_type(tmp_path):
    mem = Memory(tmp_path / "m.json")
    mem.add_lesson("AssertionError", "So sánh số thực phải dùng pytest.approx", "a", ["float"])
    mem.add_lesson("ImportError", "Chỉ import những tên có trong module", "b", ["float"])
    top = mem.relevant_lessons(["float"], error_text="E ImportError: cannot import name", k=1)
    assert top[0]["error_type"] == "ImportError"


def test_good_tests_from_other_modules_only(tmp_path):
    mem = Memory(tmp_path / "m.json")
    mem.add_good_test("def test_a():\n    assert 1", "mod_a", ["branches"], "giết được mutant")
    mem.add_good_test("def test_b():\n    assert 1", "mod_b", ["branches"], "tăng coverage")
    text = mem.format_for_prompt("mod_a", ["branches"])
    assert "test_b" in text and "test_a" not in text


def test_agent_learns_then_reuses_lessons(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    module_path = tmp_path / "mod.py"
    module_path.write_text(MODULE, encoding="utf-8")
    memory = Memory(tmp_path / "memory.json")
    settings = Settings(provider="mock", model="mock", max_retries=1)
    config = AgentConfig(use_memory=True, label="mem")

    # Lần 1: agent gặp lỗi, sửa thành công -> học bài học + lưu mẫu test tốt
    first = TestGenAgent(module_path, client=LLMClient(settings=settings, mock_responses=list(SCRIPT)),
                         config=config, memory=memory).run()
    texts = [lesson["text"] for lesson in memory.lessons]
    assert "Kiểm tra cú pháp trước khi trả lời." in texts
    assert "Đọc kỹ ngưỡng trong docstring." in texts
    assert memory.good_tests and memory.good_tests[0]["reason"] == "tăng coverage"
    assert first["memory"]["lessons"] == 2
    assert (tmp_path / "memory.json").exists()

    # Lần 2 (module khác): bài học được đưa vào prompt ban đầu
    other = tmp_path / "other.py"
    other.write_text(MODULE.replace("grade", "grade2"), encoding="utf-8")
    second = TestGenAgent(other, client=LLMClient(settings=settings), config=config, memory=memory).run()
    assert "Đọc kỹ ngưỡng trong docstring." in second["lessons_used"]


def test_memory_disabled_by_default(tmp_path):
    module_path = tmp_path / "mod.py"
    module_path.write_text(MODULE, encoding="utf-8")
    agent = TestGenAgent(module_path, client=LLMClient(settings=Settings(provider="mock", model="mock")))
    assert agent.memory is None and agent._lessons_for_initial() == ""


# ------------------------------------------------------------------ RF5: bộ nhớ theo ngôn ngữ
def test_old_format_is_converted_to_python(tmp_path):
    old = {"lessons": [{"error_type": "ImportError", "text": "Luôn import đúng tên module", "module": "a",
                        "tags": ["class"], "times_seen": 1, "times_used": 0, "created": "2026-09-26T19:00:00"}],
           "good_tests": []}
    path = tmp_path / "old.json"
    path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    mem = Memory(path)
    assert mem.stats_all() == {"python": {"lessons": 1, "good_tests": 0}}
    mem.save()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["version"] == 2 and saved["languages"]["python"]["lessons"][0]["text"] == "Luôn import đúng tên module"


def test_lessons_are_isolated_by_language(tmp_path):
    mem = Memory(tmp_path / "m.json")
    mem.add_lesson("AssertionError", "So sánh số thực phải dùng pytest.approx", "a", ["float"])
    mem.add_good_test("def test_a():\n    assert 1", "mod_a", ["float"], "tăng coverage")
    mem.select_language("javascript")
    assert mem.stats() == {"lessons": 0, "good_tests": 0}
    assert mem.format_for_prompt("x", ["float"], fence="javascript") == ""   # không lẫn bài học Python
    mem.add_lesson("TypeError", "Gọi hàm bằng đúng tên được export", "b", ["float"])
    assert "pytest" not in mem.format_for_prompt("x", ["float"], fence="javascript")
    mem.select_language("python")
    assert "pytest.approx" in mem.format_for_prompt("x", ["float"], fence="python")
    assert mem.stats_all() == {"python": {"lessons": 1, "good_tests": 1},
                               "javascript": {"lessons": 1, "good_tests": 0}}


def test_agent_selects_memory_language_from_adapter(tmp_path):
    js_module = tmp_path / "mod.js"
    js_module.write_text("export function f() {\n  return 1;\n}\n", encoding="utf-8")
    mem = Memory(tmp_path / "m.json")
    mem.add_lesson("AssertionError", "So sánh số thực phải dùng pytest.approx", "a", ["float"])
    agent = TestGenAgent(js_module, client=LLMClient(settings=Settings(provider="mock", model="mock")),
                         config=AgentConfig(use_memory=True), memory=mem)
    assert agent.memory.language == "javascript" and agent._lessons_for_initial() == ""
