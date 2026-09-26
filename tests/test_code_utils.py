import pytest

from testgen import code_utils as cu

BASE = '''import pytest
import calc


def test_a():
    assert calc.f(1) == 1


def test_b():
    assert calc.f(2) == 3
'''


def test_extract_code_from_markdown():
    text = "Đây là test:\n```python\nimport x\n\ndef test_x():\n    pass\n```\nLESSON: luôn import module"
    assert cu.extract_code(text).startswith("import x")
    assert cu.extract_lesson(text) == "luôn import module"


def test_extract_code_without_fence_but_looks_like_code():
    assert "def test_x" in cu.extract_code("import x\ndef test_x():\n    pass")
    assert cu.extract_code("Xin lỗi, tôi không làm được.") == ""


def test_extract_json_inside_fence():
    text = '```json\n{"verdicts": [{"test": "test_a", "verdict": "TEST_WRONG"}]}\n```'
    assert cu.extract_json(text)["verdicts"][0]["test"] == "test_a"
    assert cu.extract_json("không có json") == {}


def test_base_test_name_strips_parameters():
    assert cu.base_test_name("test_x[1-2]") == "test_x"
    assert cu.base_test_name("test_y") == "test_y"


def test_merge_rename_on_conflict_keeps_old_test():
    new = "import math\n\ndef test_a():\n    assert calc.f(5) == 5\n\ndef test_c():\n    pass\n"
    merged = cu.merge_tests(BASE, new, on_conflict="rename")
    names = cu.test_function_names(merged)
    assert names == ["test_a", "test_b", "test_a_v2", "test_c"]
    assert merged.startswith("import math")


def test_merge_replace_on_conflict():
    new = "def test_b():\n    assert calc.f(2) == 2\n"
    merged = cu.merge_tests(BASE, new, on_conflict="replace")
    assert cu.test_function_names(merged) == ["test_a", "test_b"]
    assert "calc.f(2) == 2" in merged and "calc.f(2) == 3" not in merged


def test_merge_invalid_code_raises():
    with pytest.raises(SyntaxError):
        cu.merge_tests(BASE, "def test_x(:\n    pass")


def test_remove_and_get_functions():
    assert "calc.f(2)" in cu.get_functions_code(BASE, ["test_b"])
    assert cu.test_function_names(cu.remove_functions(BASE, ["test_a"])) == ["test_b"]


def test_add_suspected_marker_is_idempotent():
    code = cu.add_suspected_marker(BASE, "test_b", 'code trả "C" thay vì "B"')
    code = cu.add_suspected_marker(code, "test_b", "lần hai")
    assert code.count("SUSPECTED_BUG") == 1
    assert cu.suspected_tests(code) == ["test_b"]
    assert cu.is_valid_python(code)


def test_add_marker_adds_pytest_import():
    code = cu.add_suspected_marker("import calc\n\ndef test_a():\n    assert 1\n", "test_a", "x")
    assert code.startswith("import pytest")


def test_number_lines():
    assert cu.number_lines("a\nb").splitlines()[1] == "   2 | b"


# ---- các trường hợp được phát hiện khi review code ----
def test_extract_json_with_braces_in_surrounding_text():
    text = 'Kết quả cho {test_x}:\n```json\n{"verdicts": [{"test": "test_x", "verdict": "SUSPECTED_BUG"}]}\n```'
    assert cu.extract_json(text)["verdicts"][0]["verdict"] == "SUSPECTED_BUG"


def test_merge_replaces_fixture_instead_of_renaming():
    base = ("import pytest\n\n\n@pytest.fixture\ndef cart():\n    return []\n\n\n"
            "def test_empty(cart):\n    assert cart == []\n")
    new = ("@pytest.fixture\ndef cart():\n    return [1]\n\n\n"
           "def test_empty(cart):\n    assert cart == []\n\n\n"   # LLM chép lại test cũ
           "def test_one(cart):\n    assert len(cart) == 1\n")
    merged = cu.merge_tests(base, new, on_conflict="rename")
    assert "cart_v2" not in merged and "return [1]" in merged       # fixture được THAY, không đổi tên
    assert cu.test_function_names(merged).count("test_empty") == 1  # test y nguyên chép lại -> bỏ qua
    assert "test_empty_v2" not in merged


def test_merge_import_dedup_is_exact():
    base = "from shop import CartX\n\n\ndef test_a():\n    assert CartX\n"
    merged = cu.merge_tests(base, "from shop import Cart\n\n\ndef test_b():\n    assert Cart\n")
    assert "from shop import Cart\n" in merged
