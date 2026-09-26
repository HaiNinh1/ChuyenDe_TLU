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
TỪNG test. Giới hạn: không hiểu hết cú pháp JS; đủ dùng cho file test Jest thông thường.

Nhãn nghi bug (tương đương @pytest.mark.xfail): đổi `test(` thành `test.failing(` + comment phía trên:
    // SUSPECTED_BUG: lý do
    test.failing('tiêu đề', () => { ... });
`test.failing` = "dự kiến fail": bộ test vẫn xanh, nhưng người đọc thấy ngay test này nghi phát hiện bug.
"""
import re
from dataclasses import dataclass, field

from .common import SUSPECTED_TAG

# Ký tự đứng trước dấu "/" mà sau đó là REGEX (không phải phép chia), ví dụ: toThrow(/sai/), x = /a+/
_REGEX_PREV = set("(,=:[!&|?{};+-*%<>~^") | {""}
# Từ khoá đứng trước dấu "/" thì đó cũng là regex, ví dụ: return /a+/.test(x)
_REGEX_KEYWORDS = {"return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do"}
# Dòng kết thúc bằng các ký tự này -> câu lệnh còn tiếp ở dòng sau
_CONTINUE_CHARS = set("=+-*/,(&|?:")


# ============================================================================ BỘ QUÉT NGOẶC
@dataclass
class ScanResult:
    """Thông tin từng dòng (tính từ 0) mà bộ quét thu được."""
    depths: list = field(default_factory=list)     # độ sâu ngoặc ( [ { ở CUỐI dòng
    last: list = field(default_factory=list)       # ký tự code có nghĩa cuối cùng của dòng ("" nếu không có)
    has_code: list = field(default_factory=list)   # dòng có code thật (không chỉ khoảng trắng / comment)


def _word_before(code: str, i: int) -> str:
    j = i - 1
    while j >= 0 and code[j] in " \t":
        j -= 1
    k = j
    while k >= 0 and (code[k].isalnum() or code[k] in "_$"):
        k -= 1
    return code[k + 1:j + 1]


def scan(code: str):
    """Quét code: trả về ScanResult, hoặc None nếu ngoặc/chuỗi/comment không cân bằng (code hỏng)."""
    result = ScanResult()
    depth = 0
    template_stack = []   # vào `${` trong template literal: nhớ độ sâu để biết `}` nào quay lại template
    in_template = False
    prev = ""             # ký tự có nghĩa gần nhất bên ngoài chuỗi/comment
    prev_i = -1           # vị trí của `prev`
    line_last, line_code = "", False

    def end_line():
        nonlocal line_last, line_code
        result.depths.append(depth)
        result.last.append(line_last)
        result.has_code.append(line_code)
        line_last, line_code = "", False

    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c == "\n":
            end_line()
            i += 1
            continue
        if in_template:                                   # bên trong `...`
            line_code, line_last = True, "`"
            if c == "\\":
                i += 2
            elif c == "`":
                in_template, prev, prev_i = False, "`", i
                i += 1
            elif code.startswith("${", i):
                template_stack.append(depth)
                depth += 1
                in_template, prev, prev_i = False, "{", i + 1
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
            for _ in range(code.count("\n", i, j)):
                end_line()
            i = j + 2
            continue
        line_code = True
        if c in "'\"":                                    # chuỗi '...' hoặc "..."
            j = i + 1
            while j < n and code[j] != c:
                if code[j] == "\n":
                    return None
                j += 2 if code[j] == "\\" else 1
            if j >= n:
                return None
            i, prev, prev_i, line_last = j + 1, c, j, c
            continue
        if c == "`":
            in_template, line_last = True, "`"
            i += 1
            continue
        is_regex = c == "/" and (
            (prev in _REGEX_PREV and not (prev in "+-" and prev_i > 0 and code[prev_i - 1] == prev))  # x++ / 2
            or _word_before(code, i) in _REGEX_KEYWORDS)
        if is_regex:                                      # regex /.../cờ
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
            i, prev, prev_i, line_last = j, "/", j - 1, "r"   # "r": kết thúc bằng regex (không phải toán tử)
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
        prev, prev_i, line_last = c, i, c
        i += 1
    if in_template or template_stack or depth != 0:
        return None
    end_line()
    return result


def scan_depths(code: str):
    """Độ sâu ngoặc ở cuối mỗi dòng (None nếu code hỏng)."""
    result = scan(code)
    return None if result is None else result.depths


def is_valid(code: str) -> bool:
    """Ngoặc, chuỗi, comment cân bằng. (Không phải kiểm tra cú pháp đầy đủ: Jest sẽ báo lỗi còn lại.)"""
    return bool(code.strip()) and scan(code) is not None


# ============================================================================ TÁCH KHỐI CẤP CAO NHẤT
@dataclass
class Item:
    kind: str        # import | test | helper | other
    name: str        # tiêu đề test / tên hàm / nội dung câu import
    start: int       # dòng đầu (tính từ 0), KỂ CẢ các dòng comment ngay phía trên
    body_start: int  # dòng đầu của chính câu lệnh
    end: int         # dòng cuối (bao gồm)


_STR = r"(['\"`])((?:\\.|(?!\1).)*)\1"          # chuỗi JS: nhóm 1 = dấu nháy, nhóm 2 = nội dung (còn escape)
_TEST_RE = re.compile(r"^(?:test|it)(?:\.\w+)*\s*\(\s*" + _STR, re.S)
_EACH_RE = re.compile(r"^(?:test|it)\.each\b.*?\)\s*\(\s*" + _STR, re.S)
_DESCRIBE_RE = re.compile(r"^describe(?:\.\w+)*\s*\(\s*" + _STR, re.S)
_FUNC_RE = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)")
_VAR_RE = re.compile(r"^(?:export\s+)?(?:const|let|var|class)\s+([A-Za-z_$][\w$]*)")
_IMPORT_RE = re.compile(r"^(?:import\b|(?:const|let|var)\s+[^=]+=\s*require\s*\()")
_LEADING_COMMENTS = re.compile(r"^(?:\s*/\*.*?\*/|\s*//[^\n]*)*\s*", re.S)
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def unescape(text: str) -> str:
    """Nội dung chuỗi JS -> giá trị thật: 'doesn\\'t' -> "doesn't" (Jest báo tiêu đề test theo giá trị thật)."""
    def repl(match):
        esc = match.group(1)
        if esc[0] in "ux" and len(esc) > 1:
            return chr(int(esc[1:], 16))
        return _ESCAPES.get(esc, esc)
    return re.sub(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", repl, text, flags=re.S)


def _classify(text: str):
    text = _LEADING_COMMENTS.sub("", text, count=1)
    for regex in (_EACH_RE, _TEST_RE, _DESCRIBE_RE):
        match = regex.match(text)
        if match:
            return "test", unescape(match.group(2))
    if _IMPORT_RE.match(text):
        return "import", " ".join(text.split())
    for regex in (_FUNC_RE, _VAR_RE):
        match = regex.match(text)
        if match:
            return "helper", match.group(1)
    return "other", " ".join(text.split())


def parse_items(code: str) -> list:
    """Tách file thành các khối cấp cao nhất. Ném SyntaxError nếu ngoặc/chuỗi không cân bằng."""
    info = scan(code)
    if info is None:
        raise SyntaxError("Ngoặc, chuỗi hoặc comment không cân bằng (code JavaScript/TypeScript bị hỏng)")
    lines = code.split("\n")
    items, i, comment_start = [], 0, None
    while i < len(lines):
        if not lines[i].strip():
            comment_start = None
            i += 1
            continue
        if not info.has_code[i]:                 # dòng chỉ có comment: gắn vào khối ngay sau nó
            if comment_start is None:
                comment_start = i
            i += 1
            continue
        j = i
        # câu lệnh còn tiếp nếu ngoặc chưa đóng, dòng kết thúc bằng toán tử, hoặc dòng sau bắt đầu bằng "."
        while j + 1 < len(lines) and (info.depths[j] != 0 or info.last[j] in _CONTINUE_CHARS
                                      or lines[j + 1].lstrip().startswith(".")):
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


# ---------------------------------------------------------------------------- câu import
@dataclass
class ImportInfo:
    kind: str                       # "import" (ES module) | "require" (CommonJS)
    source: str                     # './bank'
    default: str = None             # import X from ... / const X = require(...)
    namespace: str = None           # import * as X from ...
    named: dict = field(default_factory=dict)   # {tên cục bộ: tên gốc}: import { a, b as c } / const { a, b: c }

    def local_names(self) -> set:
        return set(self.named) | {n for n in (self.default, self.namespace) if n}


_IMPORT_FROM = re.compile(r"^import\s+(?:type\s+)?(?P<clause>.+?)\s+from\s*(['\"])(?P<src>.+?)\2", re.S)
_REQUIRE = re.compile(r"^(?:const|let|var)\s+(?P<clause>.+?)\s*=\s*require\(\s*(['\"])(?P<src>.+?)\2\s*\)", re.S)


def _parse_named(text: str, separator: str) -> dict:
    names = {}
    for part in text.split(","):
        part = re.sub(r"^type\s+", "", part.strip())
        pieces = [p.strip() for p in re.split(separator, part) if p.strip()]
        if pieces:
            names[pieces[-1]] = pieces[0]
    return names


def parse_import(stmt: str):
    """Câu import / require -> ImportInfo (None nếu không hiểu, ví dụ `import './setup'`)."""
    stmt = _LEADING_COMMENTS.sub("", stmt, count=1)
    match = _IMPORT_FROM.match(stmt)
    if match:
        clause, info = match["clause"].strip(), ImportInfo("import", match["src"])
        brace = re.search(r"\{([^}]*)\}", clause)
        if brace:
            info.named = _parse_named(brace.group(1), r"\s+as\s+")
            clause = clause[:brace.start()] + clause[brace.end():]
        star = re.search(r"\*\s*as\s+([\w$]+)", clause)
        if star:
            info.namespace = star.group(1)
            clause = clause.replace(star.group(0), "")
        rest = clause.replace(",", " ").split()
        info.default = rest[0] if rest else None
        return info
    match = _REQUIRE.match(stmt)
    if match:
        clause = match["clause"].strip()
        if clause.startswith("{"):
            return ImportInfo("require", match["src"], named=_parse_named(clause.strip("{} "), r"\s*:\s*"))
        return ImportInfo("require", match["src"], default=clause)
    return None


def build_import(info: ImportInfo) -> str:
    """ImportInfo -> câu lệnh (dùng dấu nháy đơn). Không gộp được namespace với {..} -> gọi 2 lần."""
    if info.kind == "require":
        if info.named:
            parts = ", ".join(o if o == loc else f"{o}: {loc}" for loc, o in info.named.items())
            return f"const {{ {parts} }} = require('{info.source}');"
        return f"const {info.default} = require('{info.source}');"
    clause = [info.default] if info.default else []
    if info.namespace:
        clause.append(f"* as {info.namespace}")
    elif info.named:
        clause.append("{ " + ", ".join(o if o == loc else f"{o} as {loc}" for loc, o in info.named.items()) + " }")
    return f"import {', '.join(clause)} from '{info.source}';"


def _rename_title(block: str, old: str, new: str) -> str:
    """Đổi tiêu đề test ở chuỗi đầu tiên của khối (giữ kiểu dấu nháy, escape lại khi cần)."""
    for match in re.finditer(_STR, block, flags=re.S):
        if unescape(match.group(2)) == old:
            quote = match.group(1)
            escaped = new.replace("\\", "\\\\").replace(quote, "\\" + quote)
            return block[:match.start()] + quote + escaped + quote + block[match.end():]
    return block


# ---------------------------------------------------------------------------- ghép test mới vào file
def merge_tests(base: str, new: str, on_conflict: str = "rename") -> str:
    """Ghép test mới vào file (giống python_edit.merge_tests):
    - import: chỉ thêm những TÊN chưa được khai báo (JS báo lỗi nếu một tên được khai báo 2 lần, Python thì không);
      tên có tên gốc cùng nguồn với câu `import { }` sẵn có -> gộp vào câu đó, còn lại thêm câu import mới lên đầu.
    - test trùng tiêu đề: "replace" -> thay khối cũ; "rename" -> đổi tiêu đề thành "... (v2)" rồi nối cuối.
      Test chép lại y nguyên -> bỏ qua.
    - hàm/biến phụ trùng tên -> thay bản cũ (không khai báo 2 lần); khối khác nối cuối nếu chưa có.
    """
    new_items = parse_items(new)
    base_items = parse_items(base)
    new_lines, lines = new.split("\n"), base.split("\n")
    by_name = {(it.kind, it.name): it for it in base_items}
    base_text = " ".join(base.split())

    base_imports = {it.body_start: (it, parse_import(it.name)) for it in base_items if it.kind == "import"}
    bound = set()                                          # các tên đã được import trong file
    for _, info in base_imports.values():
        bound |= info.local_names() if info else set()
    import_updates = {}                                    # dòng câu import cũ -> ImportInfo sau khi gộp
    replacements, appended, extra_imports = {}, [], []
    taken = {it.name for it in base_items if it.kind == "test"}
    for it in new_items:
        block = _block(new_lines, it)
        if it.kind == "import":
            info = parse_import(it.name)
            if info is None:                               # import không hiểu được: thêm nếu chưa có y hệt
                if not any(_same(block, _block(lines, b)) for b, _ in base_imports.values()):
                    extra_imports.append(block.strip())
                continue
            named = {loc: o for loc, o in info.named.items() if loc not in bound}
            default = info.default if info.default and info.default not in bound else None
            namespace = info.namespace if info.namespace and info.namespace not in bound else None
            if not (named or default or namespace):
                continue                                   # mọi tên đã có -> bỏ qua
            target = next((line for line, (_, old) in base_imports.items()
                           if old and old.kind == info.kind and old.source == info.source and old.named
                           and not old.namespace), None)
            if named and target is not None:               # gộp tên vào câu import { } cũ cùng nguồn
                current = import_updates.get(target, base_imports[target][1])
                import_updates[target] = ImportInfo(current.kind, current.source, current.default, None,
                                                    {**current.named, **named})
                named = {}
            if default or namespace:
                extra_imports.append(build_import(ImportInfo(info.kind, info.source, default, namespace,
                                                             {} if namespace else named)))
                if not namespace:
                    named = {}
            if named:
                extra_imports.append(build_import(ImportInfo(info.kind, info.source, named=named)))
            bound |= set(info.named) | {n for n in (info.default, info.namespace) if n}
        elif it.kind == "test":
            old = by_name.get(("test", it.name))
            if old and _same(_block(lines, old), block):
                continue                                   # LLM chép lại y nguyên test cũ
            if old and on_conflict == "replace":
                replacements[old.start] = (old.start, old.end, block)
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
                replacements[old.start] = (old.start, old.end, block)
        elif " ".join(block.split()) not in base_text:
            appended.append(block)

    # 1) thay khối cũ / viết lại câu import đã gộp (từ dưới lên để số dòng phía trên không lệch)
    edits = list(replacements.values())
    for line, info in import_updates.items():
        item = base_imports[line][0]
        edits.append((item.body_start, item.end, build_import(info)))   # giữ comment phía trên câu import
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
_FAILING_RE = re.compile(r"^\s*(test|it)\.failing\b")


def _find_test(code: str, name: str):
    for it in parse_items(code):
        if it.kind == "test" and it.name == name:
            return it
    return None


def add_suspected_marker(code: str, test_name: str, reason: str) -> str:
    """test('x', ...) -> // SUSPECTED_BUG: lý do \\n test.failing('x', ...). Giữ nguyên nội dung test.

    Đã có comment nhãn nhưng LLM lỡ bỏ `.failing` -> gắn lại `.failing`. Test trong describe / test.each: không gắn
    được (trả lại code như cũ; agent kiểm tra lại bằng suspected_tests()).
    """
    item = _find_test(code, test_name)
    if item is None:
        return code
    lines = code.split("\n")
    first = lines[item.body_start]
    if not re.match(r"^\s*(test|it)\b", first) or re.match(r"^\s*(test|it)\.each\b", first):
        return code
    has_comment = any(SUSPECTED_TAG in line for line in lines[item.start:item.body_start])
    if has_comment and _FAILING_RE.match(first):
        return code                                            # đã gắn nhãn đầy đủ
    lines[item.body_start] = re.sub(r"^(\s*)(?:test|it)(?:\.only|\.skip|\.failing)?\s*\(", r"\1test.failing(",
                                    first, count=1)
    if not has_comment:
        safe_reason = " ".join(reason.split())[:150]
        lines.insert(item.body_start, f"// {SUSPECTED_TAG}: {safe_reason}")
    return "\n".join(lines).rstrip() + "\n"


def suspected_tests(code: str) -> list:
    """Tên các test có comment nhãn SUSPECTED_BUG phía trên."""
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
    return [it.name for it in items if it.kind == "test" and _FAILING_RE.match(lines[it.body_start])]


def unmark_suspected(code: str) -> str:
    """Bỏ `.failing` của các test nghi bug (dùng khi chạy trên bản code ĐÃ SỬA bug để chấm).

    Code hỏng (không phân tích được) -> trả lại nguyên văn: công cụ test sẽ tự báo lỗi, không được làm sập bước chấm.
    """
    try:
        items = parse_items(code)
    except SyntaxError:
        return code
    names = set(suspected_tests(code))
    lines = code.split("\n")
    for it in items:
        if it.name in names:
            lines[it.body_start] = re.sub(r"^(\s*)test\.failing\s*\(", r"\1test(", lines[it.body_start], count=1)
    return "\n".join(lines)
