import pytest

from testgen import agent as agent_module
from testgen.agent import AgentConfig, TestGenAgent
from testgen.config import Settings
from testgen.llm_client import LLMClient
from adapters.python_adapter import generate_mutants
from testgen.mutation import describe_survivors, run_mutation_testing

MODULE = '''def sign(x):
    """Trả về 1 nếu x > 0, -1 nếu x < 0, và 0 nếu x == 0."""
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0
'''

# Bộ test "yếu": phủ 100% dòng và nhánh nhưng không kiểm tra giá trị chính xác
WEAK_TESTS = '''import mod


def test_pos():
    assert mod.sign(5) > 0


def test_neg():
    assert mod.sign(-5) < 0


def test_zero():
    assert mod.sign(0) == 0
'''

STRONG_EXTRA = '''def test_exact_values():
    assert mod.sign(1) == 1
    assert mod.sign(5) == 1
    assert mod.sign(-1) == -1
    assert mod.sign(-5) == -1
'''


@pytest.fixture
def module_path(tmp_path):
    path = tmp_path / "mod.py"
    path.write_text(MODULE, encoding="utf-8")
    return path


def test_generate_mutants_skips_docstring():
    mutants = generate_mutants(MODULE)
    assert len(mutants) >= 4
    assert all(m.line != 2 for m in mutants)  # dòng 2 là docstring
    first = mutants[0]
    assert first.line == 3 and first.original.strip() == "if x > 0:" and first.mutated != first.original


def test_weak_tests_leave_survivors(module_path):
    res = run_mutation_testing(module_path, WEAK_TESTS, max_mutants=50)
    assert res.error == ""
    assert res.total > 0 and res.survived > 0 and res.score < 100
    assert "Mutant #" in describe_survivors(res)


def test_strong_tests_kill_all(module_path):
    res = run_mutation_testing(module_path, WEAK_TESTS + "\n\n" + STRONG_EXTRA, max_mutants=50)
    assert res.score == 100.0 and res.survivors() == []


def test_sampling_is_limited_and_deterministic(module_path):
    a = run_mutation_testing(module_path, WEAK_TESTS, max_mutants=3, seed=1)
    b = run_mutation_testing(module_path, WEAK_TESTS, max_mutants=3, seed=1)
    assert a.total == 3 and a.sampled_from > 3
    assert [m.id for m in a.mutants] == [m.id for m in b.mutants]


def test_failing_suite_is_rejected_unless_skipped(module_path):
    bad = WEAK_TESTS + "\n\ndef test_wrong():\n    assert mod.sign(3) == 7\n"
    assert run_mutation_testing(module_path, bad).error != ""
    res = run_mutation_testing(module_path, bad, skip_failing=True)
    assert res.error == "" and res.total > 0


def test_agent_mutation_phase_with_mock(module_path, tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    client = LLMClient(settings=Settings(provider="mock", model="mock", max_retries=1),
                       mock_responses=[f"```python\n{WEAK_TESTS}```", f"```python\n{STRONG_EXTRA}```"])
    config = AgentConfig(use_mutation=True, mutation_threshold=100, max_mutants=50, label="mut")
    summary = TestGenAgent(module_path, client=client, config=config).run()

    actions = [it["action"] for it in summary["iterations"]]
    assert actions == ["kill_mutants", "stop"]
    assert summary["iterations"][0]["survived_mutants"]           # vòng 0 có mutant sống
    assert summary["final"]["mutation_score"] == 100.0
    assert "Đạt ngưỡng mutation" in summary["stop_reason"]
    assert summary["stats"]["llm_calls"] == 2
