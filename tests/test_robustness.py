"""Test hồi quy cho các lỗi mà lượt review độc lập (RF9) tìm ra: timeout, thiếu công cụ, số liệu chấm."""
import argparse
import json
import sys
import time

import pytest

import evaluate
from adapters import get_adapter, python_adapter
from adapters.base import EnvironmentStatus, MutationResult
from adapters.common import run_subprocess
from testgen import agent as agent_module
from testgen.agent import AgentConfig, TestGenAgent
from testgen.config import Settings
from testgen.llm_client import LLMClient

needs_node = pytest.mark.skipif(not get_adapter("javascript").check_environment().ok,
                                reason="Chưa cài Node.js/Jest (npm install)")


def test_timeout_kills_grandchildren(tmp_path):
    """Quá timeout phải dừng cả tiến trình CHÁU (vd. worker của Stryker), không chờ chúng tự thoát."""
    script = tmp_path / "spawn.py"
    script.write_text("import subprocess, sys, time\n"
                      "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])\n"
                      "time.sleep(20)\n", encoding="utf-8")
    start = time.time()
    assert run_subprocess([sys.executable, str(script)], tmp_path, timeout=2) is None
    assert time.time() - start < 12


def test_missing_program_does_not_raise(tmp_path):
    proc = run_subprocess(["chuong_trinh_khong_ton_tai_xyz"], tmp_path, timeout=5)
    assert proc.returncode == 127 and "Không chạy được" in proc.stderr


def test_broken_mutmut_is_unavailable_not_crash(tmp_path, monkeypatch):
    module = tmp_path / "mod.py"
    module.write_text("def f(x):\n    return x + 1\n", encoding="utf-8")

    def broken(source):
        raise ImportError("mutmut hỏng")

    monkeypatch.setattr(python_adapter, "generate_mutants", broken)
    res = get_adapter("python").run_mutation(module, "import mod\n\n\ndef test_f():\n    assert mod.f(1) == 2\n")
    assert not res.available and "mutmut" in res.error


def test_unavailable_mutation_is_blank_not_zero(monkeypatch):
    adapter = get_adapter("python")
    monkeypatch.setattr(type(adapter), "run_mutation",
                        lambda self, *a, **k: MutationResult(available=False, error="không có công cụ"))
    code = "import calculator\n\n\ndef test_add():\n    assert calculator.add(1, 2) == 3\n"
    m = evaluate.measure("calculator", code, exclude=set(), measure_mutants=5)
    assert m["mutation_score"] is None and m["mutation_all"] is None
    assert evaluate.mean([None, 80.0, "", 90.0]) == 85.0 and evaluate.mean([None]) is None


def test_module_file_ignores_test_files(tmp_path, monkeypatch):
    folder = tmp_path / "javascript"
    folder.mkdir()
    (folder / "shipping.test.js").write_text("", encoding="utf-8")
    (folder / "shipping.ts").write_text("", encoding="utf-8")
    monkeypatch.setattr(evaluate, "TARGETS_DIR", tmp_path)
    assert evaluate.module_file("javascript", "shipping").name == "shipping.ts"


def test_missing_language_tools_skip_only_that_language(tmp_path, monkeypatch):
    """Máy không có Node.js: phần JavaScript bị bỏ qua kèm cảnh báo, phần Python vẫn chạy."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    for target in (evaluate, agent_module):
        monkeypatch.setattr(target, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    js = get_adapter("javascript")
    monkeypatch.setattr(type(js), "check_environment",
                        lambda self: EnvironmentStatus(ok=False, problems=["chưa cài Node.js"]))
    args = argparse.Namespace(languages=["python", "javascript"], modules=["calculator", "string_tools"], runs=1,
                              max_iters=2, max_mutants=5, measure_mutants=5)
    evaluate.generate(args)
    logs = [json.loads(p.read_text(encoding="utf-8"))["language"] for p in (tmp_path / "logs").glob("*.json")]
    assert logs and set(logs) == {"python"}


@needs_node
def test_agent_treats_unmarkable_suspected_test_as_wrong(tmp_path, monkeypatch):
    """Test JS trong describe không gắn được test.failing -> không được ghi nhận là 'nghi bug' rồi để đỏ mãi."""
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    module = tmp_path / "mod.js"
    module.write_text("/** Trả về x + 1. */\nexport function inc(x) {\n  return x + 1;\n}\n", encoding="utf-8")
    grouped = ("```javascript\nimport { inc } from './mod';\n\ndescribe('nhóm', () => {\n"
               "  test('sai', () => {\n    expect(inc(1)).toBe(3);\n  });\n});\n```")
    verdict = json.dumps({"verdicts": [{"test": "nhóm", "verdict": "SUSPECTED_BUG", "reason": "?"}]})
    fixed = "```javascript\ntest('nhóm', () => {\n  expect(inc(1)).toBe(2);\n});\n```"
    client = LLMClient(settings=Settings(provider="mock", model="mock", max_retries=1),
                       mock_responses=[grouped, verdict, fixed])
    summary = TestGenAgent(module, client=client, config=AgentConfig(max_iterations=2)).run()
    assert summary["suspected_bugs"] == {}
    assert summary["iterations"][0]["action"] == "fix_tests" and summary["final"]["failed"] == 0
