"""Kiểm tra nhanh rằng các module mục tiêu import được và bug cài sẵn đúng như BUGS.md.

Đây là test của CÔNG CỤ (không phải test do LLM sinh).
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ["calculator", "text_utils", "grading", "safe_parser", "shopping_cart"]


def load(path: Path):
    """Nạp một module từ đường dẫn file (để nạp được cả bản có bug lẫn bản đã sửa)."""
    spec = importlib.util.spec_from_file_location(f"{path.parent.name}_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", TARGETS)
def test_target_and_fixed_version_exist(name):
    load(ROOT / "targets" / "python" / f"{name}.py")
    load(ROOT / "evaluation" / "fixed_targets" / "python" / f"{name}.py")


def test_bug1_letter_grade_boundary():
    buggy = load(ROOT / "targets" / "python" / "grading.py")
    fixed = load(ROOT / "evaluation" / "fixed_targets" / "python" / "grading.py")
    assert buggy.letter_grade(80) == "C"   # hành vi sai
    assert fixed.letter_grade(80) == "B"   # hành vi đúng theo docstring


def test_bug2_remove_item_keeps_empty_item():
    for folder, expected in (("targets/python", 1), ("evaluation/fixed_targets/python", 0)):
        module = load(ROOT / folder / "shopping_cart.py")
        cart = module.ShoppingCart()
        cart.add_item("tao", 5, 2)
        cart.remove_item("tao", 2)
        assert cart.unique_items() == expected


def test_non_buggy_behaviour_matches():
    calc = load(ROOT / "targets" / "python" / "calculator.py")
    text = load(ROOT / "targets" / "python" / "text_utils.py")
    parser = load(ROOT / "targets" / "python" / "safe_parser.py")
    assert calc.factorial(5) == 120
    assert text.truncate("hello world", 8) == "hello..."
    assert text.slugify("  Hello, World!! 2024 ") == "hello-world-2024"
    assert parser.parse_config(" a = 1; b=2 ;") == {"a": "1", "b": "2"}
