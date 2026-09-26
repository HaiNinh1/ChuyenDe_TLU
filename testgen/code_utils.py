"""Các hàm tiện ích xử lý code: tách code khỏi câu trả lời LLM, ghép/thay/xoá hàm test, gắn nhãn xfail.

Dùng module `ast` (cây cú pháp của Python) để tìm chính xác vị trí từng hàm test trong file,
thay vì dùng regex dễ sai.
"""
import ast
import json
import re

SUSPECTED_TAG = "SUSPECTED_BUG"


# ----------------------------------------------------------------- đọc câu trả lời LLM
def extract_code(text: str) -> str:
    """Lấy code Python trong các khối ```python ... ``` của câu trả lời LLM."""
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.DOTALL)
    if blocks:
        return "\n\n".join(block.strip() for block in blocks).strip() + "\n"
    # LLM quên bọc code: nếu trông giống code thì dùng luôn
    if "def test" in text or "import " in text:
        return text.strip() + "\n"
    return ""


def extract_lesson(text: str) -> str:
    """Lấy dòng `LESSON: ...` (bài học) nếu LLM có viết."""
    match = re.search(r"LESSON:\s*(.+)", text)
    return match.group(1).strip() if match else ""


def extract_json(text: str) -> dict:
    """Lấy object JSON đầu tiên trong câu trả lời (LLM đôi khi bọc JSON trong ```json```)."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {}


def is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


# ----------------------------------------------------------------- phân tích file test
def base_test_name(node_name: str) -> str:
    """'test_x[1-2]' (test tham số hoá) -> 'test_x'."""
    return node_name.split("[", 1)[0]


def test_function_names(code: str) -> list:
    """Tên các hàm test cấp module trong file."""
    tree = ast.parse(code)
    return [n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]


def _function_spans(tree) -> dict:
    """{tên hàm: (dòng bắt đầu kể cả decorator, dòng kết thúc)} — số dòng tính từ 1."""
    spans = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            spans[node.name] = (start, node.end_lineno)
    return spans


def get_functions_code(code: str, names) -> str:
    """Trích mã nguồn của các hàm có tên trong `names` (để gửi riêng các test fail cho LLM)."""
    lines = code.splitlines()
    spans = _function_spans(ast.parse(code))
    parts = []
    for name in names:
        if name in spans:
            start, end = spans[name]
            parts.append("\n".join(lines[start - 1:end]))
    return "\n\n\n".join(parts)


def remove_functions(code: str, names) -> str:
    """Xoá các hàm có tên trong `names` khỏi file."""
    lines = code.splitlines()
    spans = _function_spans(ast.parse(code))
    to_delete = set()
    for name in names:
        if name in spans:
            start, end = spans[name]
            to_delete.update(range(start - 1, end))
    kept = [line for i, line in enumerate(lines) if i not in to_delete]
    return _tidy("\n".join(kept))


def _tidy(code: str) -> str:
    """Gộp các dòng trống liên tiếp (tối đa 2) cho gọn."""
    return re.sub(r"\n{4,}", "\n\n\n", code).strip() + "\n"


# ------------------------------------------------------------------ ghép code mới vào file
def merge_tests(base: str, new: str, on_conflict: str = "rename") -> str:
    """Ghép code test mới (`new`) vào file hiện có (`base`).

    - Các dòng import mới được thêm lên đầu file (nếu chưa có).
    - Hàm/class mới trùng tên hàm cũ:
        on_conflict="rename"  -> đổi tên hàm mới (thêm hậu tố _v2, _v3...) rồi nối vào cuối  (khi BỔ SUNG test)
        on_conflict="replace" -> thay hàm cũ bằng hàm mới tại đúng vị trí                  (khi SỬA test)
    - Các câu lệnh khác (hằng số, helper) được nối vào cuối nếu chưa có.
    Ném SyntaxError nếu `new` không phải code Python hợp lệ.
    """
    new_tree = ast.parse(new)
    new_lines = new.splitlines()
    base_tree = ast.parse(base)
    existing = _function_spans(base_tree)

    imports, appended, replacements = [], [], {}
    for node in new_tree.body:
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        snippet = "\n".join(new_lines[start - 1:node.end_lineno])
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if snippet.strip() not in base:
                imports.append(snippet.strip())
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in existing and on_conflict == "replace":
                replacements[node.name] = snippet
            elif node.name in existing:
                new_name = _unique_name(node.name, set(existing))
                existing[new_name] = (0, 0)
                snippet = re.sub(rf"\b(def|class)\s+{node.name}\b", rf"\1 {new_name}", snippet, count=1)
                appended.append(snippet)
            else:
                existing[node.name] = (0, 0)
                appended.append(snippet)
        elif snippet.strip() and snippet.strip() not in base:
            appended.append(snippet)

    # 1) thay các hàm bị sửa (duyệt từ dưới lên để số dòng phía trên không bị lệch)
    lines = base.splitlines()
    spans = _function_spans(base_tree)
    for name in sorted(replacements, key=lambda n: spans[n][0], reverse=True):
        start, end = spans[name]
        lines[start - 1:end] = replacements[name].splitlines()
    code = "\n".join(lines)

    # 2) thêm import lên đầu, 3) nối hàm mới vào cuối
    if imports:
        code = "\n".join(imports) + "\n" + code
    if appended:
        code = code.rstrip() + "\n\n\n" + "\n\n\n".join(appended)
    return _tidy(code)


def _unique_name(name: str, taken: set) -> str:
    i = 2
    while f"{name}_v{i}" in taken:
        i += 1
    return f"{name}_v{i}"


# --------------------------------------------------------------- nhãn SUSPECTED_BUG (xfail)
def add_suspected_marker(code: str, test_name: str, reason: str) -> str:
    """Gắn `@pytest.mark.xfail(reason="SUSPECTED_BUG: ...")` lên test nghi phát hiện bug.

    Test được GIỮ NGUYÊN nội dung (không sửa assert cho khớp code). xfail nghĩa là "dự kiến fail":
    bộ test vẫn chạy xanh, nhưng pytest báo test này là XFAIL để con người xem lại.
    strict=False: nếu test là dạng tham số hoá, các trường hợp đang pass không bị coi là lỗi.
    """
    tree = ast.parse(code)
    target = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_name:
            target = node
            break
    if target is None:
        return code
    lines = code.splitlines()
    start = min([target.lineno] + [d.lineno for d in target.decorator_list])
    if any(SUSPECTED_TAG in line for line in lines[start - 1:target.lineno]):
        return code  # đã gắn nhãn rồi
    indent = lines[target.lineno - 1][: len(lines[target.lineno - 1]) - len(lines[target.lineno - 1].lstrip())]
    safe_reason = reason.replace("\\", " ").replace('"', "'").replace("\n", " ")[:150]
    marker = f'{indent}@pytest.mark.xfail(strict=False, reason="{SUSPECTED_TAG}: {safe_reason}")'
    lines.insert(start - 1, marker)
    code = "\n".join(lines) + "\n"
    if not re.search(r"^import pytest\b", code, flags=re.MULTILINE):
        code = "import pytest\n" + code
    return code


def suspected_tests(code: str) -> list:
    """Tên các test đang mang nhãn SUSPECTED_BUG."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines = code.splitlines()
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.decorator_list:
            start = min(d.lineno for d in node.decorator_list)
            if any(SUSPECTED_TAG in line for line in lines[start - 1:node.lineno]):
                names.append(node.name)
    return names


# ---------------------------------------------------------------------- hiển thị
def number_lines(source: str) -> str:
    """Đánh số dòng cho mã nguồn để LLM hiểu "dòng 17" là dòng nào."""
    return "\n".join(f"{i:4d} | {line}" for i, line in enumerate(source.splitlines(), start=1))
