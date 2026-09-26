"""Lớp trừu tượng LanguageAdapter + các dataclass kết quả DÙNG CHUNG cho mọi ngôn ngữ.

Ý tưởng (design pattern Adapter / Strategy):
- Vòng lặp agent chỉ biết "chạy test", "đo coverage", "chạy mutation", "ghép test mới vào file"...
  mà KHÔNG biết đó là pytest hay Jest.
- Mỗi ngôn ngữ viết một lớp con của LanguageAdapter, "dịch" các yêu cầu chung đó sang công cụ riêng:
      PythonAdapter      -> pytest + coverage.py + mutmut
      JavaScriptAdapter  -> Jest + Istanbul + StrykerJS
- Mọi adapter trả về CÙNG các dataclass bên dưới -> agent, evaluate.py, app.py dùng chung được.

Muốn thêm ngôn ngữ mới: xem docs/THEM_NGON_NGU_MOI.md.
"""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ============================================================================ KẾT QUẢ DÙNG CHUNG
@dataclass
class EnvironmentStatus:
    """Kết quả check_environment(): công cụ đã cài đủ chưa."""
    ok: bool                                        # chạy test + coverage được không
    mutation_available: bool = False                # chạy mutation testing được không
    tools: dict = field(default_factory=dict)       # {tên công cụ: phiên bản hoặc "" nếu thiếu}
    problems: list = field(default_factory=list)    # mô tả từng vấn đề
    install_hint: str = ""                          # lệnh cài đặt gợi ý

    def message(self) -> str:
        if not self.problems:
            return "Đủ công cụ: " + ", ".join(f"{k} {v}" for k, v in self.tools.items())
        return "Thiếu công cụ:\n- " + "\n- ".join(self.problems) + (f"\nCách cài: {self.install_hint}"
                                                                     if self.install_hint else "")


@dataclass
class TestCaseResult:
    __test__ = False  # báo pytest: đây không phải class test
    name: str        # tên test, ví dụ "test_letter_grade_b_range" hoặc "test_x[1-2]" (JS: tiêu đề của test)
    outcome: str     # passed | failed | error | skipped | xfailed
    message: str = ""


@dataclass
class CoverageResult:
    """Kết quả đo coverage cho MỘT file mã nguồn."""
    line_coverage: float = 0.0      # %
    branch_coverage: float = 0.0    # %
    missing_lines: list = field(default_factory=list)      # [12, 15, ...]
    missing_branches: list = field(default_factory=list)   # định dạng tuỳ adapter, xem describe_missing()


@dataclass
class TestResult:
    """Kết quả chạy bộ test (kèm coverage nếu có đo). Tên cũ: RunResult."""
    __test__ = False
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    xfailed: int = 0                # test nghi bug (pytest: xfail, Jest: test.failing) đang fail đúng như dự kiến
    collection_error: str = ""      # khác rỗng nếu file test không chạy được (syntax/import/không có test)
    timed_out: bool = False
    line_coverage: float = 0.0      # %
    branch_coverage: float = 0.0    # %
    missing_lines: list = field(default_factory=list)
    missing_branches: list = field(default_factory=list)
    tests: list = field(default_factory=list)              # list[TestCaseResult]
    output: str = ""                # phần cuối output của công cụ test (để gửi cho LLM khi cần)
    duration: float = 0.0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors + self.skipped + self.xfailed

    @property
    def ok(self) -> bool:
        """Bộ test chạy được và không có test nào fail/error."""
        return not self.collection_error and self.failed == 0 and self.errors == 0 and self.total > 0

    @property
    def coverage(self) -> CoverageResult:
        return CoverageResult(self.line_coverage, self.branch_coverage, self.missing_lines, self.missing_branches)

    def failing_tests(self) -> list:
        return [t for t in self.tests if t.outcome in ("failed", "error")]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["total"] = self.total
        return data


RunResult = TestResult  # tên cũ (trước refactor), giữ lại để code/test cũ vẫn chạy


@dataclass
class Mutant:
    id: int
    line: int                 # số dòng (tính từ 1) bị đột biến
    original: str             # dòng code gốc
    mutated: str              # dòng code sau đột biến
    status: str = "pending"   # killed | survived | timeout
    source: str = field(default="", repr=False)  # toàn bộ mã nguồn mutant (không ghi vào log)

    def describe(self) -> str:
        return f"Mutant #{self.id}, dòng {self.line}: `{self.original.strip()}`  ->  `{self.mutated.strip()}`"


@dataclass
class MutationResult:
    total: int = 0
    killed: int = 0
    survived: int = 0
    timeout: int = 0
    score: float = 0.0            # %
    sampled_from: int = 0         # tổng số mutant sinh được trước khi lấy mẫu
    duration: float = 0.0
    error: str = ""
    mutants: list = field(default_factory=list)
    available: bool = True        # False: công cụ mutation chưa cài / không chạy được -> agent bỏ qua phase mutation

    def survivors(self) -> list:
        return [m for m in self.mutants if m.status == "survived"]

    def to_dict(self) -> dict:
        return {
            "total": self.total, "killed": self.killed, "survived": self.survived, "timeout": self.timeout,
            "score": self.score, "sampled_from": self.sampled_from, "duration": self.duration, "error": self.error,
            "mutants": [{"id": m.id, "line": m.line, "original": m.original, "mutated": m.mutated,
                         "status": m.status} for m in self.mutants],
        }


def finish_mutation_result(result: MutationResult, mutants: list) -> MutationResult:
    """Đếm killed/survived/timeout và tính điểm (dùng chung cho mọi adapter)."""
    result.mutants = mutants
    result.total = len(mutants)
    result.killed = sum(1 for m in mutants if m.status == "killed")
    result.timeout = sum(1 for m in mutants if m.status == "timeout")
    result.survived = sum(1 for m in mutants if m.status == "survived")
    result.score = round(100.0 * (result.killed + result.timeout) / result.total, 1) if result.total else 100.0
    return result


# ============================================================================ LỚP TRỪU TƯỢNG
class LanguageAdapter(ABC):
    """Giao diện chung mà agent dùng để làm việc với MỘT ngôn ngữ lập trình."""

    name = ""                 # tên máy đọc: "python", "javascript"
    display_name = ""         # tên hiển thị: "Python", "JavaScript/TypeScript"
    file_extensions = ()      # đuôi file mã nguồn hỗ trợ, ví dụ (".py",)
    test_framework = ""       # hiển thị trên giao diện: "pytest"
    coverage_tool = ""        # "coverage.py"
    mutation_tool = ""        # "mutmut 2.5.1"
    code_fence_tags = ()      # thẻ khối code chấp nhận khi tách code khỏi câu trả lời LLM, ví dụ ("python", "py")
    code_markers = ()         # dấu hiệu "đây là code" khi LLM quên bọc khối, ví dụ ("def test", "import ")

    # ------------------------------------------------------------------ môi trường & quy ước
    @abstractmethod
    def check_environment(self) -> EnvironmentStatus:
        """Kiểm tra công cụ đã cài chưa. Không ném lỗi: trả về EnvironmentStatus kèm hướng dẫn cài."""

    @abstractmethod
    def test_file_path(self, source_file, out_dir=None) -> Path:
        """Quy ước tên/vị trí file test, ví dụ grading.py -> test_grading.py; cart.js -> cart.test.js."""

    def module_name(self, source_file) -> str:
        """Tên module dùng trong prompt và tên log (mặc định: tên file bỏ đuôi)."""
        return Path(source_file).stem

    @abstractmethod
    def prompt_hints(self, source_file=None) -> dict:
        """Các đoạn hướng dẫn riêng cho LLM (framework, cú pháp import, nhãn nghi bug...). Xem prompts.py."""

    # ------------------------------------------------------------------ chạy & đo
    @abstractmethod
    def run_tests(self, source_file, test_code: str, timeout: int = 60, with_coverage: bool = True,
                  deselect=None) -> TestResult:
        """Chạy bộ test (thư mục tạm, có timeout). deselect: tên các test cần bỏ qua."""

    def get_coverage(self, source_file, test_code: str, timeout: int = 60) -> CoverageResult:
        """Line %, branch %, dòng/nhánh chưa phủ (coverage được đo cùng lúc khi chạy test)."""
        return self.run_tests(source_file, test_code, timeout=timeout).coverage

    @abstractmethod
    def run_mutation(self, source_file, test_code: str, max_mutants: int = 20, seed: int = 0, timeout: int = 30,
                     deselect=None, skip_failing: bool = False, exclude_ids=None) -> MutationResult:
        """Mutation testing. Công cụ không khả dụng -> MutationResult(available=False, error=...), KHÔNG ném lỗi."""

    def describe_missing(self, source: str, result: TestResult, limit: int = 25) -> str:
        """Mô tả dòng/nhánh chưa phủ bằng lời để đưa vào prompt (adapter có thể viết lại cho định dạng nhánh riêng)."""
        lines = source.splitlines()
        parts = [f"- Dòng {n} chưa chạy: `{lines[n - 1].strip() if 0 < n <= len(lines) else ''}`"
                 for n in result.missing_lines[:limit]]
        return "\n".join(parts) if parts else "(không có)"

    # ------------------------------------------------------------------ đọc / sửa file test
    @abstractmethod
    def is_valid(self, code: str) -> bool:
        """Code test có đúng cú pháp (ở mức adapter kiểm tra được) không."""

    @abstractmethod
    def test_names(self, code: str) -> list:
        """Tên các test cấp cao nhất trong file (ném SyntaxError nếu không phân tích được)."""

    @abstractmethod
    def get_tests_code(self, code: str, names) -> str:
        """Mã nguồn của các test có tên trong `names`."""

    @abstractmethod
    def remove_tests(self, code: str, names) -> str:
        """Xoá các test có tên trong `names`."""

    @abstractmethod
    def merge_tests(self, base: str, new: str, on_conflict: str = "rename") -> str:
        """Ghép test mới vào file. on_conflict: "rename" (bổ sung) | "replace" (sửa). Ném SyntaxError nếu `new` hỏng."""

    @abstractmethod
    def add_suspected_marker(self, code: str, test_name: str, reason: str) -> str:
        """Gắn nhãn SUSPECTED_BUG lên test (giữ nguyên nội dung test, chỉ đánh dấu "dự kiến fail")."""

    @abstractmethod
    def suspected_tests(self, code: str) -> list:
        """Tên các test đang mang nhãn SUSPECTED_BUG."""

    def test_line_spans(self, code: str) -> dict:
        """{tên test: (dòng đầu, dòng cuối)} tính từ 1 — giao diện dùng để tô màu test. Mặc định: không biết."""
        return {}

    def base_test_name(self, name: str) -> str:
        """Tên test trong báo cáo -> tên test trong file (Python: bỏ phần tham số "[...]")."""
        return name

    def unmark_suspected(self, code: str) -> str:
        """Bỏ nhãn nghi bug (dùng khi chấm trên bản code ĐÃ SỬA bug). Mặc định: giữ nguyên."""
        return code

    def module_tags(self, source: str) -> list:
        """Nhãn đặc điểm của module (class, exception, loop...) để bộ nhớ tìm kinh nghiệm liên quan."""
        return []

    def describe_tools(self) -> str:
        return f"{self.display_name}: {self.test_framework} + {self.coverage_tool} + {self.mutation_tool}"
