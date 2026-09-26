"""Kiểm tra vòng lặp agent bằng LLM GIẢ LẬP (mock) với kịch bản trả lời định sẵn.

Kịch bản đi qua đủ các nhánh: sửa lỗi cú pháp -> phân loại test fail (1 test sai, 1 nghi bug)
-> sửa test sai -> bổ sung test tăng coverage -> đạt ngưỡng -> dừng.
"""
import json

import pytest

from testgen import agent as agent_module
from testgen.agent import AgentConfig, TestGenAgent
from testgen.config import Settings
from testgen.llm_client import LLMClient

MODULE = '''def grade(score):
    """score >= 50 -> "PASS", ngược lại "FAIL". score < 0 -> ném ValueError."""
    if score < 0:
        raise ValueError("điểm âm")
    if score > 50:
        return "PASS"
    return "FAIL"
'''

SCRIPT = [
    # 1) sinh ban đầu: lỗi cú pháp
    "```python\nimport mod\n\ndef test_x(:\n    pass\n```",
    # 2) sửa cả file: 1 test đúng, 1 test SAI, 1 test bắt được bug ở biên 50
    '```python\nimport pytest\nimport mod\n\n\ndef test_pass():\n    assert mod.grade(80) == "PASS"\n\n\n'
    'def test_wrong():\n    assert mod.grade(10) == "PASS"\n\n\n'
    'def test_boundary():\n    assert mod.grade(50) == "PASS"\n```\nLESSON: Kiểm tra cú pháp trước khi trả lời.',
    # 3) phân loại
    json.dumps({"verdicts": [
        {"test": "test_wrong", "verdict": "TEST_WRONG", "reason": "10 < 50 nên phải là FAIL"},
        {"test": "test_boundary", "verdict": "SUSPECTED_BUG", "reason": "docstring nói 50 -> PASS"},
    ]}),
    # 4) sửa test sai
    '```python\ndef test_wrong():\n    assert mod.grade(10) == "FAIL"\n```\nLESSON: Đọc kỹ ngưỡng trong docstring.',
    # 5) bổ sung coverage
    "```python\ndef test_negative():\n    with pytest.raises(ValueError):\n        mod.grade(-1)\n```",
]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    module_path = tmp_path / "mod.py"
    module_path.write_text(MODULE, encoding="utf-8")
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    client = LLMClient(settings=Settings(provider="mock", model="mock", max_retries=1),
                       mock_responses=list(SCRIPT))
    return module_path, client, tmp_path


def test_full_loop_with_mock(setup):
    module_path, client, tmp_path = setup
    events = []
    agent = TestGenAgent(module_path, client=client,
                         config=AgentConfig(max_iterations=8, line_threshold=95, branch_threshold=90),
                         progress=lambda kind, payload: events.append(kind))
    summary = agent.run()

    actions = [it["action"] for it in summary["iterations"]]
    assert actions == ["fix_collection", "fix_tests", "improve_coverage", "stop"]
    assert summary["stop_reason"] == "Đạt ngưỡng coverage"
    assert summary["stats"]["llm_calls"] == 5

    # Oracle problem: test bắt bug được GIỮ và gắn nhãn, không bị sửa cho khớp code
    assert "test_boundary" in summary["suspected_bugs"]
    assert 'assert mod.grade(50) == "PASS"' in summary["final_test_code"]
    assert "SUSPECTED_BUG" in summary["final_test_code"]

    final = summary["final"]
    assert final["failed"] == 0 and final["xfailed"] == 1
    assert final["line_coverage"] == 100.0 and final["branch_coverage"] == 100.0

    # Có log JSON + file test cuối, và giao diện nhận được sự kiện
    assert (tmp_path / "logs").glob("mod_agent_*.json")
    assert (tmp_path / "out" / "agent" / "test_mod.py").exists()
    assert "iteration" in events and "message" in events


def test_wrong_test_is_removed_after_max_attempts(setup):
    module_path, client, _ = setup
    always_wrong = '```python\nimport mod\n\ndef test_bad():\n    assert mod.grade(80) == "FAIL"\n```'
    verdict = json.dumps({"verdicts": [{"test": "test_bad", "verdict": "TEST_WRONG", "reason": "sai"}]})
    client.mock_responses = [always_wrong, verdict, always_wrong, verdict, always_wrong, verdict]
    agent = TestGenAgent(module_path, client=client,
                         config=AgentConfig(max_iterations=6, max_fix_attempts=2))
    summary = agent.run()
    removed = [name for it in summary["iterations"] for name in it["removed_tests"]]
    assert removed == ["test_bad"]
    assert "test_bad" not in summary["final_test_code"]


def test_stops_when_coverage_does_not_improve(setup):
    module_path, client, _ = setup
    first = '```python\nimport mod\n\ndef test_pass():\n    assert mod.grade(80) == "PASS"\n```'
    useless = '```python\ndef test_again():\n    assert mod.grade(90) == "PASS"\n```'
    client.mock_responses = [first, useless, useless, useless]
    agent = TestGenAgent(module_path, client=client, config=AgentConfig(max_iterations=8, patience=2))
    summary = agent.run()
    assert "không cải thiện" in summary["stop_reason"]
    assert summary["stats"]["llm_calls"] == 3  # sinh ban đầu + 2 lần bổ sung vô ích


def test_suspected_marker_restored_when_llm_drops_it(setup):
    module_path, client, _ = setup
    first = ('```python\nimport mod\n\n\ndef test_boundary():\n    assert mod.grade(50) == "PASS"\n\n\n'
             'def test_wrong():\n    assert mod.grade(10) == "PASS"\n```')
    verdict = json.dumps({"verdicts": [
        {"test": "test_boundary", "verdict": "SUSPECTED_BUG", "reason": "50 phải PASS"},
        {"test": "test_wrong", "verdict": "TEST_WRONG", "reason": "10 -> FAIL"}]})
    # LLM sửa test_wrong nhưng trả lại cả test_boundary KHÔNG có decorator
    fix = ('```python\ndef test_boundary():\n    assert mod.grade(50) == "PASS"\n\n\n'
           'def test_wrong():\n    assert mod.grade(10) == "FAIL"\n```')
    client.mock_responses = [first, verdict, fix]
    summary = TestGenAgent(module_path, client=client, config=AgentConfig(max_iterations=3)).run()
    assert "SUSPECTED_BUG" in summary["final_test_code"]
    assert summary["final"]["failed"] == 0


def test_rollback_when_run_ends_with_broken_file(setup):
    module_path, client, _ = setup
    good = '```python\nimport mod\n\n\ndef test_pass():\n    assert mod.grade(80) == "PASS"\n```'
    broken = "```python\nfrom mod import khong_ton_tai\n\n\ndef test_x():\n    assert khong_ton_tai\n```"
    client.mock_responses = [good, broken]
    summary = TestGenAgent(module_path, client=client, config=AgentConfig(max_iterations=1)).run()
    assert "khong_ton_tai" not in summary["final_test_code"]
    assert summary["final"]["line_coverage"] > 0
