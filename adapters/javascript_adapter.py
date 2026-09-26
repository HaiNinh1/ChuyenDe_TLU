"""JavaScriptAdapter: Jest (chạy test) + Istanbul (coverage có sẵn trong Jest) + StrykerJS (mutation) cho .js và .ts.

Cài đặt (một lần, ở thư mục gốc dự án):  npm install      (đọc package.json)

Chạy test giống hệt ý tưởng bên Python:
- Tạo thư mục tạm RIÊNG cho mỗi lần chạy: chỉ chứa `<module>.js|ts`, `<module>.test.js|ts`, `jest.config.json`.
  Thư mục tạm nằm trong `workspace/js_runs/` của dự án để Node.js tìm thấy `node_modules/` ở thư mục gốc.
- Jest chạy bằng tiến trình con, `--runInBand` (một tiến trình -> dừng được khi quá timeout).
- TypeScript: babel-jest + @babel/preset-typescript chỉ BỎ phần khai báo kiểu rồi chạy (không kiểm tra kiểu)
  -> một cấu hình dùng chung cho .js và .ts.
- Kết quả đọc từ file, không đọc chữ trên màn hình:
    `--json --outputFile=report.json`    -> từng test: passed / failed / pending + thông báo lỗi
    `--coverageReporters=json`           -> cov/coverage-final.json: số lần chạy mỗi câu lệnh (s) và nhánh (b)

Mutation: StrykerJS (@stryker-mutator/core + jest-runner) đọc báo cáo `mutation.json`.
Stryker chưa cài hoặc chạy lỗi -> MutationResult(available=False): agent dừng phase mutation, giữ kết quả coverage.
"""
import json
import random
import re
import shutil
import tempfile
import time
from pathlib import Path

from . import js_edit
from .base import (EnvironmentStatus, LanguageAdapter, Mutant, MutationResult, TestCaseResult, TestResult,
                   finish_mutation_result)
from .common import run_subprocess, tail

ROOT_DIR = Path(__file__).resolve().parent.parent            # thư mục gốc dự án (có package.json)
NODE_MODULES = ROOT_DIR / "node_modules"
JEST_BIN = NODE_MODULES / "jest" / "bin" / "jest.js"
STRYKER_BIN = NODE_MODULES / "@stryker-mutator" / "core" / "bin" / "stryker.js"
WORK_ROOT = ROOT_DIR / "workspace" / "js_runs"
ANSI = re.compile(r"\x1b\[[0-9;]*m")                          # mã màu trong thông báo lỗi của Jest
STRYKER_TIMEOUT = 900                                         # giây, cho cả lần chạy Stryker

# Trạng thái mutant của Stryker -> trạng thái dùng chung. CompileError/RuntimeError/Ignored: mutant không hợp lệ
# (giống mutant sai cú pháp bên Python) -> bỏ, không tính vào điểm.
STRYKER_STATUS = {"Killed": "killed", "Timeout": "timeout", "Survived": "survived", "NoCoverage": "survived"}

# Tên các loại nhánh của Istanbul -> mô tả tiếng Việt cho prompt
BRANCH_TYPES = {"if": "if", "cond-expr": "biểu thức điều kiện ?:", "binary-expr": "biểu thức && / || / ??",
                "switch": "switch", "default-arg": "giá trị mặc định của tham số"}

# ============================================================================ PROMPT RIÊNG CHO JS / TS
JS_HINTS = {
    "language": "JavaScript",
    "framework": "Jest",
    "fence": "javascript",
    "spec": "JSDoc",
    "import_rule": "Module cần test nằm cùng thư mục với file test: dùng `import { ... } from './<module>'` "
                   "(cú pháp ES module, không ghi đuôi file).",
    "libs_rule": "Chỉ dùng Jest (các hàm toàn cục `test`, `expect`, không cần import) và thư viện chuẩn của Node.js. "
                 "Không đọc/ghi file, không gọi mạng, không dùng timer/sleep.",
    "structure_rule": "Viết mỗi test là một lời gọi `test('tiêu đề mô tả rõ', () => { ... });` ở CẤP CAO NHẤT của "
                      "file — KHÔNG dùng `describe`, KHÔNG dùng `test.each`; mỗi test kiểm tra một ý, "
                      "tiêu đề các test không trùng nhau.",
    "assert_rule": "Dùng `expect(() => ...).toThrow(LoạiLỗi)` cho ngoại lệ, `toBeCloseTo` khi so sánh số thực, "
                   "`toEqual` khi so sánh object/mảng.",
    "keep_marker": "giữ nguyên các `test.failing(...)` cùng dòng comment `// SUSPECTED_BUG` phía trên nếu có",
    "test_id": "tiêu đề test, tức chuỗi trong test('...')",
    "keep_name": "GIỮ NGUYÊN TIÊU ĐỀ TEST (chuỗi trong test('...'))",
    "test_unit": "khối `test('...', ...)`",
    "impl_details": "ví dụ so sánh tham chiếu bằng `toBe` khi JSDoc chỉ nói về giá trị, kiểu dữ liệu không được nêu, "
                    "spy/mock để dò cách cài đặt",
}
TS_HINTS = dict(JS_HINTS, language="TypeScript", fence="typescript",
                import_rule=JS_HINTS["import_rule"] + " File test cũng là TypeScript (`.test.ts`); không cần khai "
                "báo kiểu phức tạp (kiểu không được kiểm tra khi chạy test).")


# ============================================================================ CHẠY JEST
def _jest_config(module_file: str, with_coverage: bool) -> dict:
    config = {
        "rootDir": ".",
        "testEnvironment": "node",
        "testMatch": ["**/*.test.[jt]s"],
        # babel-jest: chuyển mã ES module / TypeScript về dạng Node chạy được (không kiểm tra kiểu)
        "transform": {r"\.[jt]sx?$": ["babel-jest", {
            "presets": [["@babel/preset-env", {"targets": {"node": "current"}}], "@babel/preset-typescript"],
            "babelrc": False, "configFile": False}]},
    }
    if with_coverage:
        config.update({"collectCoverageFrom": [module_file], "coverageReporters": ["json"],
                       "coverageDirectory": "cov"})
    return config


def _prepare_dir(source_file: Path, test_code: str, with_coverage: bool, source_text: str = None) -> Path:
    """Thư mục tạm: module + file test + jest.config.json."""
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="jest_", dir=WORK_ROOT))
    source_text = source_file.read_text(encoding="utf-8") if source_text is None else source_text
    (work_dir / source_file.name).write_text(source_text, encoding="utf-8")
    (work_dir / _test_name(source_file)).write_text(test_code, encoding="utf-8")
    (work_dir / "jest.config.json").write_text(json.dumps(_jest_config(source_file.name, with_coverage)),
                                               encoding="utf-8")
    return work_dir


def _test_name(source_file: Path) -> str:
    return f"{source_file.stem}.test{source_file.suffix}"


def _node_env() -> dict:
    return {"FORCE_COLOR": "0", "NO_COLOR": "1", "CI": "1"}


def run_tests(source_file, test_code: str, timeout: int = 60, with_coverage: bool = True,
              deselect=None) -> TestResult:
    source_file = Path(source_file)
    result = TestResult()
    if deselect:
        test_code = js_edit.remove_tests(test_code, list(deselect))
    if not js_edit.is_valid(test_code):
        result.collection_error = ("SyntaxError: ngoặc, chuỗi hoặc comment không cân bằng — file test "
                                   "JavaScript/TypeScript bị hỏng (có thể câu trả lời của LLM bị cắt giữa chừng).")
        result.output = result.collection_error
        return result

    work_dir = _prepare_dir(source_file, test_code, with_coverage)
    try:
        cmd = ["node", str(JEST_BIN), "--config", "jest.config.json", "--runInBand", "--ci", "--silent",
               "--watchman=false", "--json", "--outputFile=report.json"]
        if with_coverage:
            cmd.append("--coverage")
        start = time.time()
        proc = run_subprocess(cmd, work_dir, timeout, extra_env=_node_env())
        result.duration = round(time.time() - start, 2)
        if proc is None:
            result.timed_out = True
            result.collection_error = f"Bộ test chạy quá {timeout} giây (có thể lặp vô hạn) và đã bị dừng."
            result.output = result.collection_error
            return result
        result.output = tail(ANSI.sub("", proc.stdout + proc.stderr), 4000)
        _parse_report(work_dir / "report.json", test_code, result)
        if with_coverage and not result.collection_error:
            _parse_coverage(work_dir / "cov" / "coverage-final.json", source_file.name, result)
        return result
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _file_test_name(reported: str, file_names: list) -> str:
    """Tên test trong báo cáo -> tiêu đề test trong file (test.each tạo tên theo mẫu %s, $x...)."""
    if reported in file_names:
        return reported
    for name in file_names:
        pattern = re.escape(name)
        pattern = re.sub(r"%[sdifjopc#%]|\\\$[\w.]+", ".*", pattern)
        if re.fullmatch(pattern, reported):
            return name
    return reported


def _parse_report(report_path: Path, test_code: str, result: TestResult):
    """Đọc report.json của Jest -> đếm pass/fail/skip/xfail cho từng test."""
    if not report_path.exists():
        result.collection_error = "Jest không chạy được:\n" + result.output
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    suites = report.get("testResults", [])
    suite = suites[0] if suites else {}
    if not suite or (suite.get("status") == "failed" and not suite.get("assertionResults")):
        # Lỗi cú pháp / import / không có test: Jest báo "Test suite failed to run"
        message = ANSI.sub("", suite.get("message", "") or result.output)
        result.collection_error = "Lỗi khi nạp file test (syntax/import/không có test):\n" + tail(message, 3000)
        return
    try:
        file_names = js_edit.test_names(test_code)
    except SyntaxError:
        file_names = []
    suspected = set(js_edit.failing_marked(test_code))   # chỉ test viết bằng test.failing mới bị Jest đảo kết quả
    for assertion in suite["assertionResults"]:
        titles = assertion.get("ancestorTitles") or []
        name = _file_test_name(titles[0] if titles else assertion["title"], file_names)
        message = ANSI.sub("", "\n".join(assertion.get("failureMessages") or []))
        status = assertion["status"]
        if status == "passed":
            # test.failing "pass" nghĩa là thân test FAIL đúng như dự kiến -> tương đương xfail của pytest
            outcome = "xfailed" if name in suspected else "passed"
        elif status == "failed":
            # test.failing mà thân test lại PASS (code chạy đúng) -> coi như pass (giống xfail strict=False)
            outcome = "passed" if name in suspected and "supposed to fail" in message else "failed"
        else:
            outcome = "skipped"                          # pending / todo / skipped
        result.tests.append(TestCaseResult(name=name, outcome=outcome, message=tail(message.strip(), 1500)))
        setattr(result, outcome, getattr(result, outcome) + 1)
    if not result.tests:
        result.collection_error = "Không tìm thấy test nào (mỗi test phải là test('...', () => {...}))."


def _parse_coverage(json_path: Path, file_name: str, result: TestResult):
    """Đọc coverage-final.json (Istanbul) -> % dòng, % nhánh, dòng chưa chạy, nhánh chưa đi qua."""
    if not json_path.exists():
        return
    data = json.loads(json_path.read_text(encoding="utf-8"))
    info = next((v for k, v in data.items() if Path(k).name == file_name), None)
    if info is None:
        return
    # Dòng: một dòng được tính là đã chạy nếu có câu lệnh bắt đầu ở dòng đó được chạy ít nhất 1 lần (như Istanbul)
    line_hits = {}
    for sid, count in info["s"].items():
        line = info["statementMap"][sid]["start"]["line"]
        line_hits[line] = max(line_hits.get(line, 0), count)
    covered_lines = sum(1 for c in line_hits.values() if c > 0)
    result.line_coverage = round(100.0 * covered_lines / len(line_hits), 1) if line_hits else 100.0
    result.missing_lines = sorted(line for line, c in line_hits.items() if c == 0)
    # Nhánh: mỗi "b" là danh sách số lần chạy của từng nhánh con, ví dụ if -> [nhánh đúng, nhánh sai]
    total = covered = 0
    missing = []
    for bid, counts in info["b"].items():
        branch = info["branchMap"][bid]
        for arm, count in enumerate(counts):
            total += 1
            if count > 0:
                covered += 1
            else:
                missing.append([branch["loc"]["start"]["line"], arm, branch["type"]])
    result.branch_coverage = round(100.0 * covered / total, 1) if total else 100.0
    result.missing_branches = missing


def describe_missing(source: str, result: TestResult, limit: int = 25) -> str:
    """Mô tả dòng / nhánh chưa phủ (nhánh của Istanbul: [dòng, thứ tự nhánh con, loại])."""
    lines = source.splitlines()

    def code_at(n):
        return lines[n - 1].strip() if 0 < n <= len(lines) else ""

    parts = [f"- Dòng {n} chưa chạy: `{code_at(n)}`" for n in result.missing_lines[:limit]]
    for line, arm, kind in result.missing_branches[:limit]:
        if line in result.missing_lines:
            continue
        if kind == "if":
            which = "nhánh ĐÚNG (vào thân if)" if arm == 0 else "nhánh SAI (bỏ qua if / vào else)"
        elif kind == "cond-expr":
            which = "nhánh ĐÚNG" if arm == 0 else "nhánh SAI"
        elif kind == "binary-expr":
            which = f"vế thứ {arm + 1}"
        elif kind == "switch":
            which = f"case thứ {arm + 1}"
        elif kind == "default-arg":
            parts.append(f"- Trường hợp BỎ TRỐNG tham số (dùng giá trị mặc định) ở dòng {line} (`{code_at(line)}`) "
                         "chưa được gọi")
            continue
        else:
            which = f"nhánh thứ {arm + 1}"
        parts.append(f"- {which} của {BRANCH_TYPES.get(kind, kind)} ở dòng {line} (`{code_at(line)}`) "
                     "chưa được đi qua")
    return "\n".join(parts) if parts else "(không có)"


# ============================================================================ MUTATION (StrykerJS)
_STRYKER_CACHE = {}   # (mã nguồn, code test) -> danh sách mutant đã chạy: chấm held-out + toàn bộ chỉ chạy Stryker 1 lần


def _mutated_line(source_lines: list, loc: dict, replacement: str) -> str:
    """Dòng code sau đột biến: thay đoạn [start, end] (dòng/cột tính từ 1) bằng `replacement`."""
    start, end = loc["start"], loc["end"]
    first = source_lines[start["line"] - 1]
    last = source_lines[end["line"] - 1]
    return first[:start["column"] - 1] + " ".join(replacement.split()) + last[end["column"] - 1:]


def _run_stryker(source_file: Path, test_code: str, timeout: int):
    """Chạy Stryker trên toàn bộ mutant. Trả về (danh sách Mutant, lỗi)."""
    key = (source_file.read_text(encoding="utf-8"), test_code)
    if key in _STRYKER_CACHE:
        return _STRYKER_CACHE[key], ""
    work_dir = _prepare_dir(source_file, test_code, with_coverage=False)
    try:
        config = {
            "testRunner": "jest", "plugins": ["@stryker-mutator/jest-runner"],
            "mutate": [source_file.name], "coverageAnalysis": "perTest",
            "jest": {"configFile": "jest.config.json", "enableFindRelatedTests": False},
            "reporters": ["json"], "jsonReporter": {"fileName": "mutation.json"},
            "concurrency": 4, "timeoutMS": timeout * 1000, "tempDirName": ".stryker-tmp",
            "cleanTempDir": "always", "logLevel": "error",
        }
        (work_dir / "stryker.config.json").write_text(json.dumps(config), encoding="utf-8")
        proc = run_subprocess(["node", str(STRYKER_BIN), "run", "stryker.config.json"], work_dir, STRYKER_TIMEOUT,
                              extra_env=_node_env())
        report = work_dir / "mutation.json"
        if proc is None:
            return None, f"Stryker chạy quá {STRYKER_TIMEOUT} giây"
        if not report.exists():
            return None, "Stryker lỗi: " + tail(ANSI.sub("", proc.stdout + proc.stderr), 800)
        data = json.loads(report.read_text(encoding="utf-8"))
        source_lines = key[0].splitlines()
        mutants = []
        for m in next(iter(data["files"].values()))["mutants"]:
            status = STRYKER_STATUS.get(m["status"])
            if status is None:
                continue
            line = m["location"]["start"]["line"]
            mutants.append(Mutant(id=int(m["id"]), line=line, original=source_lines[line - 1],
                                  mutated=_mutated_line(source_lines, m["location"], m.get("replacement", "")),
                                  status=status))
        mutants.sort(key=lambda mu: mu.id)
        _STRYKER_CACHE[key] = mutants
        return mutants, ""
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_mutation_testing(source_file, test_code: str, max_mutants: int = 20, seed: int = 0, timeout: int = 30,
                         deselect=None, skip_failing: bool = False, exclude_ids=None) -> MutationResult:
    """Cùng ý nghĩa tham số với bản Python (xem python_adapter.run_mutation_testing).

    Khác biệt: Stryker chạy TẤT CẢ mutant rồi mới lấy mẫu `max_mutants` (cùng seed) -> kết quả tương đương.
    Test nghi bug (test.failing) được bỏ ra khi chạy mutation: trong Jest, test.failing sẽ "giết" mutant vô tình
    sửa đúng bug, còn pytest xfail(strict=False) thì không -> bỏ ra để hai ngôn ngữ đo như nhau.
    """
    start = time.time()
    source_file = Path(source_file)
    result = MutationResult()
    if not STRYKER_BIN.exists() or not (NODE_MODULES / "@stryker-mutator" / "jest-runner").exists():
        result.available = False
        result.error = "Chưa cài StrykerJS (chạy `npm install` ở thư mục gốc dự án)"
        return result

    drop = list(deselect or []) + js_edit.suspected_tests(test_code)
    if skip_failing:
        first = run_tests(source_file, test_code, with_coverage=False, deselect=drop)
        drop += [t.name for t in first.failing_tests()]
    code = js_edit.remove_tests(test_code, drop) if drop else test_code

    baseline = run_tests(source_file, code, with_coverage=False)
    if not baseline.ok:
        result.error = "Bộ test chưa pass trên code gốc nên không thể chạy mutation testing"
        return result

    mutants, error = _run_stryker(source_file, code, timeout)
    if mutants is None:
        result.available = False          # Stryker lỗi -> "không khả dụng", agent vẫn chạy tiếp
        result.error = error
        return result
    mutants = [Mutant(m.id, m.line, m.original, m.mutated, m.status) for m in mutants
               if m.id not in set(exclude_ids or [])]
    result.sampled_from = len(mutants)
    if max_mutants is not None and len(mutants) > max_mutants:
        mutants = sorted(random.Random(seed).sample(mutants, max_mutants), key=lambda m: m.id)
    finish_mutation_result(result, mutants)
    result.duration = round(time.time() - start, 1)
    return result


# ============================================================================ NHÃN MODULE (cho bộ nhớ)
def module_tags(source: str) -> list:
    """Nhãn đặc điểm module bằng regex (không có parser JS) — cùng bộ nhãn với Python để bộ nhớ dùng chung ý tưởng."""
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)   # bỏ comment/JSDoc
    tags = set()
    checks = {
        "class": r"\bclass\s+\w+",
        "exception": r"\bthrow\b|\btry\s*\{",
        "loop": r"\b(for|while)\s*\(|\.forEach\(",
        "compound_condition": r"&&|\|\|",
        "string": r"\.(split|trim|toLowerCase|toUpperCase|join|replace)\(",
        "float": r"Math\.round|toFixed|[\w)\]]\s*/\s*[\w(]",
        "dict": r"new Map\b|\{\s*\w+\s*:",
        "state": r"\bthis\.\w+\s*=[^=]",
    }
    for tag, pattern in checks.items():
        if re.search(pattern, code):
            tags.add(tag)
    if len(re.findall(r"\bif\s*\(", code)) >= 4:
        tags.add("branches")
    return sorted(tags)


# ============================================================================ ADAPTER
def _node_version() -> str:
    if shutil.which("node") is None:
        return ""
    proc = run_subprocess(["node", "--version"], ROOT_DIR, 20)
    return proc.stdout.strip().lstrip("v") if proc and proc.returncode == 0 else ""


def _package_version(name: str) -> str:
    path = NODE_MODULES / name / "package.json"
    if not path.exists():
        return ""
    return json.loads(path.read_text(encoding="utf-8")).get("version", "?")


class JavaScriptAdapter(LanguageAdapter):
    name = "javascript"
    display_name = "JavaScript/TypeScript"
    file_extensions = (".js", ".ts")
    test_framework = "Jest"
    coverage_tool = "Istanbul (có sẵn trong Jest)"
    mutation_tool = "StrykerJS"
    code_fence_tags = ("javascript", "js", "typescript", "ts", "jsx", "tsx")
    code_markers = ("test(", "import ", "require(")

    def check_environment(self) -> EnvironmentStatus:
        tools = {"node": _node_version(), "jest": _package_version("jest"),
                 "babel-jest": _package_version("babel-jest"),
                 "@babel/preset-typescript": _package_version("@babel/preset-typescript"),
                 "@stryker-mutator/core": _package_version("@stryker-mutator/core"),
                 "@stryker-mutator/jest-runner": _package_version("@stryker-mutator/jest-runner")}
        problems = []
        if not tools["node"]:
            problems.append("chưa cài Node.js (cần bản >= 22, tải ở https://nodejs.org)")
        elif int(tools["node"].split(".")[0]) < 22:
            problems.append(f"Node.js {tools['node']} quá cũ (cần >= 22)")
        for pkg in ("jest", "babel-jest", "@babel/preset-typescript"):
            if not tools[pkg]:
                problems.append(f"thiếu gói npm `{pkg}`")
        test_ok = not problems
        mutation_ok = test_ok and bool(tools["@stryker-mutator/core"] and tools["@stryker-mutator/jest-runner"])
        if test_ok and not mutation_ok:
            problems.append("thiếu StrykerJS -> không chạy được mutation testing")
        return EnvironmentStatus(ok=test_ok, mutation_available=mutation_ok, tools=tools, problems=problems,
                                 install_hint="cài Node.js >= 22, rồi chạy `npm install` ở thư mục gốc dự án")

    def test_file_path(self, source_file, out_dir=None) -> Path:
        source_file = Path(source_file)
        return Path(out_dir or source_file.parent) / _test_name(source_file)

    def prompt_hints(self, source_file=None) -> dict:
        is_ts = source_file is not None and Path(source_file).suffix == ".ts"
        return dict(TS_HINTS if is_ts else JS_HINTS)

    def run_tests(self, source_file, test_code, timeout=60, with_coverage=True, deselect=None) -> TestResult:
        return run_tests(source_file, test_code, timeout=timeout, with_coverage=with_coverage, deselect=deselect)

    def run_mutation(self, source_file, test_code, max_mutants=20, seed=0, timeout=30, deselect=None,
                     skip_failing=False, exclude_ids=None) -> MutationResult:
        return run_mutation_testing(source_file, test_code, max_mutants=max_mutants, seed=seed, timeout=timeout,
                                    deselect=deselect, skip_failing=skip_failing, exclude_ids=exclude_ids)

    def describe_missing(self, source, result, limit=25) -> str:
        return describe_missing(source, result, limit)

    # ---- đọc / sửa file test: bộ quét ngoặc (js_edit.py)
    def is_valid(self, code):
        return js_edit.is_valid(code)

    def test_names(self, code):
        return js_edit.test_names(code)

    def get_tests_code(self, code, names):
        return js_edit.get_tests_code(code, names)

    def remove_tests(self, code, names):
        return js_edit.remove_tests(code, names)

    def merge_tests(self, base, new, on_conflict="rename"):
        return js_edit.merge_tests(base, new, on_conflict=on_conflict)

    def add_suspected_marker(self, code, test_name, reason):
        return js_edit.add_suspected_marker(code, test_name, reason)

    def suspected_tests(self, code):
        return js_edit.suspected_tests(code)

    def unmark_suspected(self, code):
        return js_edit.unmark_suspected(code)

    def module_tags(self, source):
        return module_tags(source)
