"""Kiểm tra JavaScriptAdapter với Jest + StrykerJS thật (không gọi LLM).

Cần Node.js + `npm install`. Máy chưa cài -> các test chạy Node được bỏ qua (skip) kèm lý do rõ ràng.
"""
import json

import pytest

from adapters import adapter_for_file, get_adapter
from adapters.javascript_adapter import JavaScriptAdapter
from testgen import agent as agent_module
from testgen.agent import AgentConfig, TestGenAgent
from testgen.config import ROOT_DIR, Settings
from testgen.llm_client import LLMClient

JS = get_adapter("javascript")
ENV = JS.check_environment()
needs_node = pytest.mark.skipif(not ENV.ok, reason="Chưa cài Node.js/Jest: " + "; ".join(ENV.problems))

SHIPPING = ROOT_DIR / "targets" / "javascript" / "shipping.ts"
TESTS = """import { shippingFee, deliveryDays } from './shipping';

test('đơn nhỏ phí 30', () => {
  expect(shippingFee(100)).toBe(30);
});

test('biên 500 miễn phí', () => {
  expect(shippingFee(500)).toBe(0);
});

test('âm ném RangeError', () => {
  expect(() => shippingFee(-1)).toThrow(RangeError);
});
"""


def test_registry_and_conventions():
    assert adapter_for_file("a/b.ts") is JS and adapter_for_file("x.js") is JS
    assert JS.test_file_path(SHIPPING, "out").as_posix() == "out/shipping.test.ts"
    assert JS.prompt_hints(SHIPPING)["fence"] == "typescript"
    assert JS.prompt_hints("x.js")["fence"] == "javascript"
    assert {"exception", "branches"} <= set(JS.module_tags((ROOT_DIR / "targets" / "javascript" /
                                                            "duration_parser.js").read_text(encoding="utf-8")))


@needs_node
def test_run_tests_counts_coverage_and_failures():
    res = JS.run_tests(SHIPPING, TESTS)
    assert (res.passed, res.failed, res.xfailed) == (2, 1, 0)
    assert res.failing_tests()[0].name == "biên 500 miễn phí"          # bug cài sẵn: 500 -> 15 thay vì 0
    assert 0 < res.line_coverage < 100 and 0 < res.branch_coverage < 100
    text = JS.describe_missing(SHIPPING.read_text(encoding="utf-8"), res)
    assert "switch" in text and "Dòng" in text


@needs_node
def test_suspected_marker_becomes_xfail_and_suite_is_green():
    code = JS.add_suspected_marker(TESTS, "biên 500 miễn phí", "500 phải miễn phí")
    res = JS.run_tests(SHIPPING, code)
    assert res.ok and res.xfailed == 1
    # trên bản ĐÃ SỬA bug, bỏ nhãn đi thì test đó pass
    fixed = ROOT_DIR / "evaluation" / "fixed_targets" / "javascript" / "shipping.ts"
    on_fixed = JS.run_tests(fixed, JS.unmark_suspected(code), with_coverage=False)
    assert on_fixed.ok and (on_fixed.passed, on_fixed.xfailed) == (3, 0)   # comment còn nhưng không còn .failing


@needs_node
def test_broken_and_empty_files_are_collection_errors():
    assert JS.run_tests(SHIPPING, "test('a', () => {").collection_error                 # ngoặc chưa đóng
    missing_module = "import { f } from './khong_co';\n\ntest('x', () => {\n  expect(f()).toBe(1);\n});\n"
    assert "khong_co" in JS.run_tests(SHIPPING, missing_module).collection_error      # import sai
    assert JS.run_tests(SHIPPING, "const a = 1;\n").collection_error                   # không có test nào


@needs_node
def test_mutation_with_stryker_and_exclusion():
    code = JS.add_suspected_marker(TESTS, "biên 500 miễn phí", "500 phải miễn phí")
    res = JS.run_mutation(SHIPPING, code, max_mutants=None)
    assert res.available and res.total > 10 and 0 < res.score < 100
    assert all(m.describe().startswith("Mutant #") for m in res.survivors())
    shown = [m.id for m in res.survivors()[:3]]
    held = JS.run_mutation(SHIPPING, code, max_mutants=None, exclude_ids=shown)
    assert held.total == res.total - 3


def test_mutation_unavailable_when_stryker_missing(monkeypatch, tmp_path):
    from adapters import javascript_adapter as ja
    monkeypatch.setattr(ja, "STRYKER_BIN", tmp_path / "khong_co.js")
    res = JavaScriptAdapter().run_mutation(SHIPPING, TESTS)
    assert not res.available and "Stryker" in res.error


@needs_node
def test_agent_on_javascript_with_mock_llm(tmp_path, monkeypatch):
    """Toàn bộ vòng lặp agent trên file .ts: phân loại nghi bug -> gắn test.failing -> bổ sung coverage."""
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    script = [
        f"```typescript\n{TESTS}```",
        json.dumps({"verdicts": [{"test": "biên 500 miễn phí", "verdict": "SUSPECTED_BUG",
                                  "reason": "JSDoc: total >= 500 -> 0"}]}),
        "```typescript\nimport { deliveryDays } from './shipping';\n\n"
        "test('các khu vực', () => {\n  expect(deliveryDays('inner')).toBe(1);\n  expect(deliveryDays('outer')).toBe(3);\n"
        "  expect(deliveryDays('remote')).toBe(7);\n});\n```",
    ]
    client = LLMClient(settings=Settings(provider="mock", model="mock", max_retries=1), mock_responses=script)
    summary = TestGenAgent(SHIPPING, client=client, config=AgentConfig(max_iterations=3)).run()
    assert summary["language"] == "javascript"
    assert [it["action"] for it in summary["iterations"]][:2] == ["fix_tests", "improve_coverage"]
    assert "biên 500 miễn phí" in summary["suspected_bugs"]
    assert "test.failing('biên 500 miễn phí'" in summary["final_test_code"]
    assert "import { shippingFee, deliveryDays } from './shipping';" in summary["final_test_code"]
    assert summary["final"]["failed"] == 0 and summary["final"]["xfailed"] == 1
    assert (tmp_path / "out" / "agent" / "shipping.test.ts").exists()
