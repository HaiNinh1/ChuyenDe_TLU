"""Kiểm tra lớp trừu tượng LanguageAdapter, dataclass dùng chung và registry (dùng một adapter giả)."""
from pathlib import Path

import pytest

from adapters import registry
from adapters.base import (CoverageResult, LanguageAdapter, Mutant, MutationResult, RunResult, TestResult,
                           finish_mutation_result)


class FakeAdapter(LanguageAdapter):
    """Adapter tối thiểu cho ngôn ngữ giả ".fake" — chứng minh giao diện đủ để cài một ngôn ngữ mới."""
    name, display_name, file_extensions = "fake", "Fake", (".fake",)

    def check_environment(self):
        from adapters.base import EnvironmentStatus
        return EnvironmentStatus(ok=True, tools={"fakeunit": "1.0"})

    def test_file_path(self, source_file, out_dir=None):
        return Path(out_dir or ".") / "fake_test.fake"

    def prompt_hints(self, source_file=None):
        return {}

    def run_tests(self, source_file, test_code, timeout=60, with_coverage=True, deselect=None):
        return TestResult(passed=1, line_coverage=50.0, missing_lines=[2])

    def run_mutation(self, source_file, test_code, **kwargs):
        return MutationResult(available=False, error="không có công cụ mutation")

    def is_valid(self, code):
        return True

    def test_names(self, code):
        return []

    def get_tests_code(self, code, names):
        return ""

    def remove_tests(self, code, names):
        return code

    def merge_tests(self, base, new, on_conflict="rename"):
        return base + new

    def add_suspected_marker(self, code, test_name, reason):
        return code

    def suspected_tests(self, code):
        return []


@pytest.fixture
def fake():
    adapter = registry.register(FakeAdapter())
    yield adapter
    registry._ADAPTERS.pop("fake", None)


def test_abstract_class_cannot_be_instantiated():
    with pytest.raises(TypeError):
        LanguageAdapter()


def test_registry_finds_adapter_by_extension(fake):
    assert registry.adapter_for_file("x/y/module.FAKE") is fake
    assert registry.get_adapter("fake") is fake
    assert ".fake" in registry.supported_extensions()


def test_registry_unknown_extension_has_clear_message(fake):
    with pytest.raises(registry.UnsupportedLanguageError, match=r"\.fake"):
        registry.adapter_for_file("main.cobol")


def test_default_get_coverage_and_describe_missing(fake):
    cov = fake.get_coverage("a.fake", "")
    assert isinstance(cov, CoverageResult) and cov.line_coverage == 50.0 and cov.missing_lines == [2]
    text = fake.describe_missing("dòng 1\n  dòng 2\n", fake.run_tests("a.fake", ""))
    assert "Dòng 2 chưa chạy: `dòng 2`" in text


def test_shared_dataclasses_keep_old_behaviour():
    assert RunResult is TestResult  # tên cũ vẫn dùng được
    r = TestResult(passed=2, failed=1)
    assert r.total == 3 and not r.ok and r.to_dict()["total"] == 3
    m = finish_mutation_result(MutationResult(), [Mutant(1, 1, "a", "b", "killed"),
                                                  Mutant(2, 1, "a", "c", "survived"),
                                                  Mutant(3, 2, "x", "y", "timeout")])
    assert (m.total, m.killed, m.survived, m.timeout, m.score) == (3, 1, 1, 1, 66.7)
    assert m.available and [s.id for s in m.survivors()] == [2]


@pytest.mark.parametrize("code, expected", [
    ('def add(a, b):\n    """Cộng."""\n    return a + b\n', ".py"),
    ("export function add(a, b) {\n  return a + b;\n}\n", ".js"),
    ("export function add(a: number, b: number): number {\n  return a + b;\n}\n", ".ts"),
    ("class Cart:\n    def __init__(self):\n        self.items = {}\n", ".py"),
])
def test_detect_language(code, expected):
    assert registry.detect_language(code) == expected
