"""Đọc / sửa file test JavaScript/TypeScript (Jest) mà KHÔNG cần cài parser JS.

Python có sẵn `ast` cho Python, nhưng không có parser cho JS. Ở đây dùng một BỘ QUÉT NGOẶC đơn giản:
đi qua từng ký tự, bỏ qua chuỗi '...' "..." `...${...}...`, comment // và /* */, regex /.../,
rồi đếm độ sâu ngoặc ( [ {. Nhờ đó tách file test thành các "khối cấp cao nhất":

    import { f } from './mod';              -> import
    test('tiêu đề', () => { ... });          -> test   (tên = tiêu đề; cũng nhận it(...), test.failing(...))
    describe('nhóm', () => { ... });         -> test   (cả nhóm tính là MỘT test, tên = tiêu đề nhóm)
    function helper() { ... } / const X = …  -> helper (tên = tên hàm / biến)
    beforeEach(() => { ... });               -> other

Vì vậy prompt yêu cầu LLM viết `test()` ở cấp cao nhất (không describe): agent mới sửa/xoá/gắn nhãn được
TỪNG test. Giới hạn: không hiểu hết cú pháp JS (ví dụ regex đứng sau `)`); đủ dùng cho file test Jest thông thường.

Nhãn nghi bug (tương đương @pytest.mark.xfail): đổi `test(` thành `test.failing(` + comment phía trên:
    // SUSPECTED_BUG: lý do
    test.failing('tiêu đề', () => { ... });
`test.failing` = "dự kiến fail": bộ test vẫn xanh, nhưng người đọc thấy ngay test này nghi phát hiện bug.
"""
import re
from dataclasses import dataclass

from .common import SUSPECTED_TAG

# Ký tự đứng trước dấu "/" mà sau đó là REGEX (không phải phép chia), ví dụ: toThrow(/sai/), x = /a+/
_REGEX_PREV = set("(,=:[!&|?{};+-*%<>~^") | {""}


# ============================================================================ BỘ QUÉT NGOẶC
def scan_depths(code: str):
    """Độ sâu ngoặc ( [ { ở CUỐI mỗi dòng. Trả về None nếu ngoặc/chuỗi/comment không cân bằng (code hỏng)."""
    depths = []
    depth = 0
    template_stack = []   # vào `${` trong template literal: nhớ độ sâu để biết `}` nào quay lại template
    in_template = False
    prev = ""             # ký tự có nghĩa gần nhất bên ngoài chuỗi/comment
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c == "\n":
            depths.append(depth)
            i += 1
            continue
        if in_template:                                   # bên trong `...`
            if c == "\\":
                i += 2
            elif c == "`":
                in_template, prev = False, "`"
                i += 1
            elif code.startswith("${", i):
                template_stack.append(depth)
                depth += 1
                in_template, prev = False, "{"
                i += 2
            else:
                i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if code.startswith("//", i):                      # comment 1 dòng
            j = code.find("\n", i)
            i = n if j < 0 else j
            continue
        if code.startswith("/*", i):                      # comment nhiều dòng
            j = code.find("*/", i + 2)
            if j < 0:
                return None
            depths.extend([depth] * code.count("\n", i, j))
            i = j + 2
            continue
        if c in "'\"":                                    # chuỗi '...' hoặc "..."
            j = i + 1
            while j < n and code[j] != c:
                if code[j] == "\n":
                    return None
                j += 2 if code[j] == "\\" else 1
            if j >= n:
                return None
            i, prev = j + 1, c
            continue
        if c == "`":
            in_template = True
            i += 1
            continue
        if c == "/" and prev in _REGEX_PREV:              # regex /.../cờ
            j, in_class = i + 1, False
            while j < n:
                ch = code[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "\n":
                    return None
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    break
                j += 1
            j += 1
            while j < n and code[j].isalpha():
                j += 1
            i, prev = j, "/"
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if c == "}" and template_stack and depth - 1 == template_stack[-1]:
                template_stack.pop()                     # hết `${...}` -> quay lại template literal
                depth -= 1
                in_template = True
                i += 1
                continue
            depth -= 1
            if depth < 0:
                return None
        prev = c
        i += 1
    if in_template or template_stack or depth != 0:
        return None
    depths.append(depth)
    return depths


def is_valid(code: str) -> bool:
    """Ngoặc, chuỗi, comment cân bằng. (Không phải kiểm tra cú pháp đầy đủ: Jest sẽ báo lỗi còn lại.)"""
    return bool(code.strip()) and scan_depths(code) is not None


# ============================================================================ TÁCH KHỐI CẤP CAO NHẤT
@dataclass
class Item:
    kind: str        # import | test | helper | other
    name: str        # tiêu đề test / tên hàm / nội dung câu import
    start: int       # dòng đầu (tính từ 0), KỂ CẢ các dòng comment ngay phía trên
    body_start: int  # dòng đầu của chính câu lệnh
    end: int         # dòng cuối (bao gồm)


_TEST_RE = re.compile(r"^(?:test|it)(?:\.\w+)*\s*\(\s*(['\"`])(.*?)(?<!\\)\1", re.S)
_EACH_RE = re.compile(r"^(?:test|it)\.each\b.*?\)\s*\(\s*(['\"`])(.*?)(?<!\\)\1", re.S)
_DESCRIBE_RE = re.compile(r"^describe(?:\.\w+)*\s*\(\s*(['\"`])(.*?)(?<!\\)\1", re.S)
_FUNC_RE = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)")
_VAR_RE = re.compile(r"^(?:export\s+)?(?:const|let|var|class)\s+([A-Za-z_$][\w$]*)")
_IMPORT_RE = re.compile(r"^(?:import\b|(?:const|let|var)\s+[^=]+=\s*require\s*\()")


def _continues(line: str, next_line: str) -> bool:
    """Câu lệnh còn tiếp ở dòng sau? (dòng kết thúc bằng toán tử, hoặc dòng sau bắt đầu bằng `.`)."""
    text = re.sub(r"//.*$", "", line).rstrip()
    return bool(text) and (text[-1] in "=+-*/,(&|?:" or next_line.lstrip().startswith("."))


def _classify(text: str):
    for regex in (_EACH_RE, _TEST_RE, _DESCRIBE_RE):
        match = regex.match(text)
        if match:
            return "test", match.group(2)
    if _IMPORT_RE.match(text):
        return "import", " ".join(text.split())
    for regex in (_FUNC_RE, _VAR_RE):
        match = regex.match(text)
        if match:
            return "helper", match.group(1)
    return "other", " ".join(text.split())


def parse_items(code: str) -> list:
    """Tách file thành các khối cấp cao nhất. Ném SyntaxError nếu ngoặc/chuỗi không cân bằng."""
    depths = scan_depths(code)
    if depths is None:
        raise SyntaxError("Ngoặc, chuỗi hoặc comment không cân bằng (code JavaScript/TypeScript bị hỏng)")
    lines = code.split("\n")
    items, i, comment_start = [], 0, None
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            comment_start = None
            i += 1
            continue
        if stripped.startswith("//") or stripped.startswith("/*"):   # comment cấp cao nhất: gắn vào khối sau
            if comment_start is None:
                comment_start = i
            if stripped.startswith("/*"):
                while "*/" not in lines[i] and i + 1 < len(lines):
                    i += 1
            i += 1
            continue
        j = i
        while j + 1 < len(lines) and (depths[j] != 0 or _continues(lines[j], lines[j + 1])):
            j += 1
        kind, name = _classify("\n".join(lines[i:j + 1]).strip())
        items.append(Item(kind, name, comment_start if comment_start is not None else i, i, j))
        comment_start = None
        i = j + 1
    return items


def _block(lines: list, item: Item) -> str:
    return "\n".join(lines[item.start:item.end + 1])


def _same(a: str, b: str) -> bool:
    """Hai khối code giống nhau nếu bỏ qua khác biệt khoảng trắng và kiểu dấu nháy ' / "."""
    return " ".join(a.split()).replace('"', "'") == " ".join(b.split()).replace('"', "'")


def _tidy(code: str) -> str:
    return re.sub(r"\n{4,}", "\n\n\n", code).strip() + "\n"


# ============================================================================ THAO TÁC TRÊN TEST
def test_names(code: str) -> list:
    return [it.name for it in parse_items(code) if it.kind == "test"]


def get_tests_code(code: str, names) -> str:
    lines = code.split("\n")
    by_name = {it.name: it for it in parse_items(code) if it.kind == "test"}
    return "\n\n".join(_block(lines, by_name[n]) for n in names if n in by_name)


def remove_tests(code: str, names) -> str:
    lines = code.split("\n")
    drop = set()
    for it in parse_items(code):
        if it.kind == "test" and it.name in set(names):
            drop.update(range(it.start, it.end + 1))
    return _tidy("\n".join(line for k, line in enumerate(lines) if k not in drop))


def _import_bindings(stmt: str):
    """Câu import -> (nguồn, {tên cục bộ: tên gốc}) nếu là import có tên trong ngoặc nhọn; ngược lại None."""
    match = re.match(r"^import\s+(?:type\s+)?\{([^}]*)\}\s*from\s*(['\"])(.+?)\2", stmt) or \
        re.match(r"^(?:const|let|var)\s*\{([^}]*)\}\s*=\s*require\(\s*(['\"])(.+?)\2", stmt)
    if not match:
        return None
    names = {}
    for part in match.group(1).split(","):
        pieces = [p.strip() for p in re.split(r"\s+as\s+|:", part.strip()) if p.strip()]
        if pieces:                          # import: "gốc as cục_bộ"; require: "gốc: cục_bộ"
            names[pieces[-1]] = pieces[0]
    return match.group(3), names


def _rename_title(block: str, old: str, new: str) -> str:
    """Đổi tiêu đề test trong chuỗi đầu tiên của khối (test('cũ' -> test('mới')."""
    return re.sub(r"(['\"`])" + re.escape(old) + r"\1", lambda m: m.group(1) + new + m.group(1), block, count=1)


def merge_tests(base: str, new: str, on_conflict: str = "rename") -> str:
    """Ghép test mới vào file (giống python_edit.merge_tests):
    - import mới: nếu cùng nguồn với import có sẵn -> gộp tên vào câu import cũ (JS báo lỗi nếu khai báo trùng tên);
      import khác thì thêm lên đầu file.
    - test trùng tiêu đề: "replace" -> thay khối cũ; "rename" -> đổi tiêu đề thành "... (v2)" rồi nối cuối.
      Test chép lại y nguyên -> bỏ qua.
    - hàm/biến phụ trùng tên -> thay bản cũ (không khai báo 2 lần); khối khác nối cuối nếu chưa có.
    """
    new_items = parse_items(new)
    base_items = parse_items(base)
    new_lines, lines = new.split("\n"), base.split("\n")
    by_name = {(it.kind, it.name): it for it in base_items}
    base_text = " ".join(base.split())

    replacements, appended, extra_imports = {}, [], []
    import_updates = {}                     # chỉ số dòng câu import cũ -> câu import mới đã gộp tên
    taken = {it.name for it in base_items if it.kind == "test"}
    for it in new_items:
        block = _block(new_lines, it)
        if it.kind == "import":
            if ("import", it.name) in by_name:
                continue
            parsed = _import_bindings(it.name)
            target = None
            if parsed:
                for old in base_items:
                    old_parsed = _import_bindings(old.name) if old.kind == "import" else None
                    if old_parsed and old_parsed[0] == parsed[0]:
                        target = (old, old_parsed)
                        break
            if target:
                old, (source, old_names) = target
                missing = [f"{orig} as {loc}" if orig != loc else loc
                           for loc, orig in parsed[1].items() if loc not in old_names]
                if missing:
                    current = import_updates.get(old.body_start, _block(lines, old))
                    import_updates[old.body_start] = re.sub(r"\s*\}", ", " + ", ".join(missing) + " }", current,
                                                            count=1)
                continue
            extra_imports.append(block.strip())
        elif it.kind == "test":
            old = by_name.get(("test", it.name))
            if old and _same(_block(lines, old), block):
                continue                                 # LLM chép lại y nguyên test cũ
            if old and on_conflict == "replace":
                replacements[old.start] = (old, block)
            elif it.name in taken:
                new_title = _unique_title(it.name, taken)
                taken.add(new_title)
                appended.append(_rename_title(block, it.name, new_title))
            else:
                taken.add(it.name)
                appended.append(block)
        elif it.kind == "helper" and ("helper", it.name) in by_name:
            old = by_name[("helper", it.name)]
            if not _same(_block(lines, old), block):
                replacements[old.start] = (old, block)
        elif " ".join(block.split()) not in base_text:
            appended.append(block)

    # 1) thay khối cũ / gộp import (từ dưới lên để số dòng phía trên không lệch)
    edits = [(old.start, old.end, blk) for old, blk in replacements.values()]
    for start, text in import_updates.items():
        old = next(it for it in base_items if it.body_start == start)
        edits.append((old.start, old.end, text))
    for start, end, text in sorted(edits, reverse=True):
        lines[start:end + 1] = text.split("\n")
    code = "\n".join(lines)
    # 2) import mới lên đầu, 3) khối mới nối cuối
    if extra_imports:
        code = "\n".join(extra_imports) + "\n" + code
    if appended:
        code = code.rstrip() + "\n\n" + "\n\n".join(appended)
    return _tidy(code)


def _unique_title(title: str, taken: set) -> str:
    i = 2
    while f"{title} (v{i})" in taken:
        i += 1
    return f"{title} (v{i})"


# ============================================================================ NHÃN SUSPECTED_BUG
def _find_test(code: str, name: str):
    for it in parse_items(code):
        if it.kind == "test" and it.name == name:
            return it
    return None


def add_suspected_marker(code: str, test_name: str, reason: str) -> str:
    """test('x', ...) -> // SUSPECTED_BUG: lý do \\n test.failing('x', ...). Giữ nguyên nội dung test."""
    item = _find_test(code, test_name)
    if item is None:
        return code
    lines = code.split("\n")
    if any(SUSPECTED_TAG in line for line in lines[item.start:item.body_start]):
        return code                                            # đã gắn nhãn rồi
    first = lines[item.body_start]
    if not re.match(r"^\s*(test|it)\b", first) or re.match(r"^\s*(test|it)\.each\b", first):
        return code                                            # describe / test.each: không gắn được (xem giới hạn)
    lines[item.body_start] = re.sub(r"^(\s*)(?:test|it)(?:\.only|\.skip|\.failing)?\s*\(", r"\1test.failing(",
                                    first, count=1)
    safe_reason = " ".join(reason.split())[:150]
    lines.insert(item.body_start, f"// {SUSPECTED_TAG}: {safe_reason}")
    return "\n".join(lines).rstrip() + "\n"


def suspected_tests(code: str) -> list:
    try:
        items = parse_items(code)
    except SyntaxError:
        return []
    lines = code.split("\n")
    return [it.name for it in items
            if it.kind == "test" and any(SUSPECTED_TAG in line for line in lines[it.start:it.body_start])]


def failing_marked(code: str) -> list:
    """Tên các test đang được viết là `test.failing(...)` / `it.failing(...)` (Jest đảo kết quả của chúng)."""
    try:
        items = parse_items(code)
    except SyntaxError:
        return []
    lines = code.split("\n")
    return [it.name for it in items
            if it.kind == "test" and re.match(r"^\s*(test|it)\.failing\b", lines[it.body_start])]


def unmark_suspected(code: str) -> str:
    """Bỏ `.failing` của các test nghi bug (dùng khi chạy trên bản code ĐÃ SỬA bug để chấm)."""
    names = set(suspected_tests(code))
    lines = code.split("\n")
    for it in parse_items(code):
        if it.name in names:
            lines[it.body_start] = re.sub(r"^(\s*)test\.failing\s*\(", r"\1test(", lines[it.body_start], count=1)
    return "\n".join(lines)
