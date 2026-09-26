"""Kiểm tra bộ quét ngoặc + các thao tác sửa file test JavaScript/TypeScript (không cần Node.js)."""
import pytest

from adapters import js_edit as je

BASE = """import { deposit } from './bank';

// hàm phụ
const make = () => ({ a: 1, b: `x${1 + {c: 2}.c}y` });

test('nạp tiền dương', () => {
  expect(deposit(5)).toBe(5); // comment có dấu )
  expect(() => deposit(-1)).toThrow(/số tiền [(]/);
});

test("chia", () => {
  const x = 10 / 2 / 5;
  expect(x).toBe(1);
});
"""


def test_scanner_ignores_brackets_in_strings_comments_regex_templates():
    depths = je.scan_depths(BASE)
    assert depths is not None and depths[-1] == 0
    assert je.is_valid(BASE)


@pytest.mark.parametrize("broken", ["test('a', () => {", "const s = 'chưa đóng;", "/* comment chưa đóng",
                                    "const t = `a${b`;", ""])
def test_scanner_detects_broken_code(broken):
    assert not je.is_valid(broken)


def test_parse_items_kinds_and_names():
    items = je.parse_items(BASE)
    assert [(it.kind, it.name) for it in items] == [
        ("import", "import { deposit } from './bank';"), ("helper", "make"),
        ("test", "nạp tiền dương"), ("test", "chia")]
    assert items[1].start == 2 and items[1].body_start == 3  # comment phía trên được gắn vào khối


def test_other_forms_are_recognised():
    code = ("it.only('một', () => {});\n\ndescribe('nhóm', () => {\n  test('con', () => {});\n});\n\n"
            "test.each([[1], [2]])('mẫu %i', (n) => {\n  expect(n).toBeGreaterThan(0);\n});\n\n"
            "function helper(x) {\n  return x;\n}\n\nconst { a, b } = require('./m');\n")
    kinds = [(it.kind, it.name) for it in je.parse_items(code)]
    assert kinds == [("test", "một"), ("test", "nhóm"), ("test", "mẫu %i"), ("helper", "helper"),
                     ("import", "const { a, b } = require('./m');")]


def test_get_and_remove_tests():
    assert "10 / 2 / 5" in je.get_tests_code(BASE, ["chia"])
    assert je.test_names(je.remove_tests(BASE, ["chia"])) == ["nạp tiền dương"]


def test_merge_rename_replace_and_import_union():
    new = ("import { deposit, withdraw } from './bank';\n\n"
           "test('chia', () => {\n  expect(1).toBe(1);\n});\n\n"
           "test('rút', () => {\n  expect(withdraw(1)).toBe(0);\n});\n")
    renamed = je.merge_tests(BASE, new, on_conflict="rename")
    assert je.test_names(renamed) == ["nạp tiền dương", "chia", "chia (v2)", "rút"]
    # import cùng nguồn được GỘP (JS báo lỗi nếu khai báo `deposit` hai lần)
    assert renamed.count("from './bank'") == 1 and "withdraw" in renamed.splitlines()[0]
    replaced = je.merge_tests(BASE, new, on_conflict="replace")
    assert je.test_names(replaced) == ["nạp tiền dương", "chia", "rút"]
    assert "10 / 2 / 5" not in replaced


def test_merge_skips_echoed_test_and_replaces_helper():
    echoed = "test('chia', () => {\n  const x = 10 / 2 / 5;\n  expect(x).toBe(1);\n});\n"
    assert je.test_names(je.merge_tests(BASE, echoed)) == ["nạp tiền dương", "chia"]
    helper = "const make = () => ({ a: 2 });\n"
    merged = je.merge_tests(BASE, helper)
    assert merged.count("const make") == 1 and "a: 2" in merged


def test_merge_invalid_code_raises_syntax_error():
    with pytest.raises(SyntaxError):
        je.merge_tests(BASE, "test('x', () => {")


def test_suspected_marker_roundtrip():
    code = je.add_suspected_marker(BASE, "chia", 'code "sai"\nở đây')
    code = je.add_suspected_marker(code, "chia", "lần hai")        # gắn 2 lần -> chỉ 1 nhãn
    assert code.count("SUSPECTED_BUG") == 1 and 'test.failing("chia"' in code
    assert je.suspected_tests(code) == ["chia"]
    assert je.is_valid(code)
    assert je.failing_marked(code) == ["chia"]
    unmarked = je.unmark_suspected(code)
    assert "test.failing" not in unmarked and 'test("chia"' in unmarked
    assert je.failing_marked(unmarked) == [] and je.suspected_tests(unmarked) == ["chia"]  # comment vẫn giữ
