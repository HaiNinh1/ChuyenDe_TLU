"""VÒNG LẶP TỰ CẢI TIẾN — phần cốt lõi của dự án.

Ý tưởng: LLM viết test -> chương trình CHẠY test và ĐO -> đưa kết quả đo (phản hồi) lại cho LLM -> lặp.

Mỗi vòng (iteration):
    1. Chạy runner trên bộ test hiện tại -> RunResult (pass/fail, coverage...)
    2. Quyết định hành động theo thứ tự ưu tiên:
        a) File test không chạy được (syntax/import)   -> "fix_collection": LLM sửa cả file
        b) Có test FAIL                               -> "classify": LLM phân loại TEST_WRONG / SUSPECTED_BUG
                                                         + TEST_WRONG  -> LLM sửa đúng các hàm đó
                                                         + SUSPECTED_BUG -> GIỮ test, gắn nhãn xfail (không sửa!)
        c) Coverage chưa đạt ngưỡng                   -> "improve_coverage": đưa dòng/nhánh chưa phủ cho LLM
        d) (tuỳ chọn) Mutation score chưa đạt         -> "kill_mutants": đưa mutant còn sống cho LLM
        e) Đạt ngưỡng / không cải thiện / hết vòng    -> DỪNG
    3. Ghi log vòng này ra JSON.

Không dùng framework agent nào: toàn bộ "agent" chỉ là vòng for + if/else dưới đây.

Chạy thử:
    python -m testgen.agent targets/grading.py
    python -m testgen.agent targets/grading.py --max-iters 6 --line 95 --branch 90
"""
import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from . import code_utils as cu
from . import prompts
from .config import ROOT_DIR
from .generator import generate_tests
from .llm_client import LLMClient, LLMError
from .runner import RunResult, describe_missing, run_tests

LOGS_DIR = ROOT_DIR / "logs"
OUTPUT_DIR = ROOT_DIR / "generated_tests"


@dataclass
class AgentConfig:
    max_iterations: int = 8          # số vòng cải tiến tối đa (mỗi vòng tối đa 1-2 lần gọi LLM)
    line_threshold: float = 95.0     # ngưỡng line coverage (%)
    branch_threshold: float = 90.0   # ngưỡng branch coverage (%)
    patience: int = 2                # số lần cải tiến liên tiếp KHÔNG tăng chỉ số thì dừng
    max_fix_attempts: int = 2        # số lần sửa tối đa cho một test, quá thì xoá test đó
    test_timeout: int = 60           # giây, cho mỗi lần chạy pytest
    use_mutation: bool = False       # GĐ5: bật mutation testing sau khi xong phase coverage
    mutation_threshold: float = 80.0
    max_mutants: int = 20
    use_memory: bool = False         # GĐ6: dùng bộ nhớ bài học
    label: str = "agent"             # tên cấu hình (dùng đặt tên log / thư mục kết quả)


@dataclass
class IterationLog:
    """Thông tin một vòng lặp — được ghi ra JSON và hiển thị trên giao diện."""
    iteration: int
    phase: str                  # repair | coverage | mutation | done
    action: str                 # fix_collection | fix_tests | improve_coverage | kill_mutants | stop
    reason: str                 # giải thích bằng lời vì sao chọn hành động này
    test_code: str              # code test ĐƯỢC ĐÁNH GIÁ ở vòng này
    passed: int = 0
    failed: int = 0
    errors: int = 0
    xfailed: int = 0
    collection_error: str = ""
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    missing_lines: list = field(default_factory=list)
    missing_branches: list = field(default_factory=list)
    mutation_score: float = None
    mutants_total: int = 0
    mutants_killed: int = 0
    survived_mutants: list = field(default_factory=list)
    suspected: dict = field(default_factory=dict)       # {tên test: lý do}
    classifications: list = field(default_factory=list)  # kết quả phân loại của LLM ở vòng này
    removed_tests: list = field(default_factory=list)
    lesson: str = ""
    llm_calls_so_far: int = 0
    elapsed: float = 0.0


class TestGenAgent:
    __test__ = False  # báo pytest: đây không phải class test

    def __init__(self, module_path, client: LLMClient = None, config: AgentConfig = None,
                 memory=None, progress=None):
        self.module_path = Path(module_path)
        self.module_name = self.module_path.stem
        self.source = self.module_path.read_text(encoding="utf-8")
        self.client = client or LLMClient()
        self.config = config or AgentConfig()
        self.memory = memory                    # đối tượng Memory (GĐ6) hoặc None
        self.progress = progress or (lambda kind, payload: None)  # callback cho giao diện

        # --- trạng thái của agent ---
        self.code = ""                          # bộ test hiện tại
        self.suspected = {}                     # test nghi phát hiện bug: {tên: lý do}
        self.fix_attempts = {}                  # số lần đã sửa mỗi test
        self.collection_failures = 0            # số lần liên tiếp file test không chạy được
        self.last_good_code = ""                # phiên bản gần nhất chạy được (để quay lui)
        self.phase = "coverage"                 # coverage -> mutation -> done
        self.no_improve = 0                     # đếm số lần cải tiến không tăng chỉ số
        self.best_score = -1.0
        self.last_mutation = None               # MutationResult gần nhất (GĐ5)
        self.pending_lessons = []               # bài học chờ xác nhận (GĐ6)
        self.lessons_used = ""
        self.iterations = []
        self.stop_reason = ""
        self.start_time = 0.0

    # ================================================================ VÒNG LẶP CHÍNH
    def run(self) -> dict:
        self.start_time = time.time()
        self._message(f"Bắt đầu sinh test cho `{self.module_name}` ({self.config.label})")
        try:
            # Bước 1: sinh test ban đầu (giống hệt baseline, có thể kèm bài học từ bộ nhớ)
            self.lessons_used = self._lessons_for_initial()
            self.code = generate_tests(self.module_path, self.client, self.lessons_used)

            for it in range(self.config.max_iterations + 1):
                # Bước 2: chạy test và đo
                result = run_tests(self.module_path, self.code, timeout=self.config.test_timeout)
                entry = self._new_entry(it, result)

                if it == self.config.max_iterations:
                    self._finish(entry, "stop", f"Hết số vòng tối đa ({self.config.max_iterations})")
                    break

                # Bước 3-5: quyết định và thực hiện hành động
                if not self._step(entry, result):
                    break
        except LLMError as exc:
            # Lỗi gọi LLM (mất mạng, hết tiền...): dừng êm, giữ bộ test tốt nhất hiện có
            self.stop_reason = f"Lỗi gọi LLM: {exc}"
            self._message(self.stop_reason)
            if not self.code and self.last_good_code:
                self.code = self.last_good_code

        return self._save()

    def _step(self, entry: IterationLog, result: RunResult) -> bool:
        """Chọn và thực hiện MỘT hành động. Trả về False nếu cần dừng vòng lặp."""
        # (a) File test hỏng hoàn toàn -> sửa cả file
        if result.collection_error:
            self.collection_failures += 1
            if self.collection_failures > self.config.max_fix_attempts:
                if self.last_good_code:
                    self.code = self.last_good_code
                    self._finish(entry, "stop", "Không sửa được file test, quay lui về phiên bản chạy được gần nhất")
                else:
                    self._finish(entry, "stop", "Không sửa được file test")
                return False
            self._fix_collection(entry, result)
            return True
        self.collection_failures = 0
        self._confirm_lessons()  # các sửa lỗi trước đó đã thành công -> lưu bài học (GĐ6)

        # (b) Có test fail -> phân loại: test sai hay code có bug?
        failing = [t for t in result.failing_tests() if cu.base_test_name(t.name) not in self.suspected]
        if failing:
            self._handle_failures(entry, failing)
            return True
        self.last_good_code = self.code

        # (c) Phase coverage
        if self.phase == "coverage":
            reached = (result.line_coverage >= self.config.line_threshold
                       and result.branch_coverage >= self.config.branch_threshold)
            score = result.line_coverage + result.branch_coverage
            if not reached and self._improved(score):
                self._improve_coverage(entry, result)
                return True
            # Coverage đạt ngưỡng hoặc không cải thiện được nữa -> sang phase mutation (nếu bật)
            why = "Đạt ngưỡng coverage" if reached else f"Coverage không cải thiện sau {self.config.patience} lần thử"
            if not self.config.use_mutation:
                self._finish(entry, "stop", why)
                return False
            self._message(f"{why} -> chuyển sang mutation testing")
            self.phase, self.no_improve, self.best_score = "mutation", 0, -1.0

        # (d) Phase mutation (GĐ5)
        if self.phase == "mutation":
            return self._mutation_step(entry)

        self._finish(entry, "stop", "Hoàn tất")
        return False

    # ================================================================ CÁC HÀNH ĐỘNG
    def _fix_collection(self, entry: IterationLog, result: RunResult):
        entry.phase, entry.action = "repair", "fix_collection"
        entry.reason = "File test không chạy được (lỗi cú pháp / import / không có test) -> nhờ LLM sửa cả file"
        self._message(entry.reason)
        prompt = prompts.fix_collection_prompt(self.module_name, self.source, self.code,
                                               result.collection_error[-3000:],
                                               self._lessons_for_error(result.collection_error))
        answer = self.client.chat(prompts.SYSTEM_PROMPT, prompt, task="fix_collection")
        new_code = cu.extract_code(answer)
        entry.lesson = cu.extract_lesson(answer)
        if new_code:
            # Gắn lại nhãn SUSPECTED_BUG phòng khi LLM làm mất
            for name, reason in self.suspected.items():
                if cu.is_valid_python(new_code):
                    new_code = cu.add_suspected_marker(new_code, name, reason)
            self.code = new_code
            self._remember_fix(result.collection_error, entry.lesson)
        self._emit(entry)

    def _handle_failures(self, entry: IterationLog, failing):
        entry.phase, entry.action = "repair", "fix_tests"
        names = sorted({cu.base_test_name(t.name) for t in failing})
        failures_text = "\n\n".join(f"### {t.name}\n{t.message[:800]}" for t in failing)
        failing_code = cu.get_functions_code(self.code, names)

        # --- Oracle problem: hỏi LLM test sai hay code sai ---
        answer = self.client.chat(
            prompts.SYSTEM_PROMPT,
            prompts.classify_prompt(self.module_name, self.source, failing_code, failures_text),
            task="classify",
        )
        verdicts = {}
        for item in cu.extract_json(answer).get("verdicts", []):
            name = cu.base_test_name(str(item.get("test", "")))
            verdicts[name] = (str(item.get("verdict", "TEST_WRONG")).upper(), str(item.get("reason", "")))
        entry.classifications = [{"test": n, "verdict": v[0], "reason": v[1]} for n, v in verdicts.items()]

        to_fix, to_remove = [], []
        for name in names:
            verdict, reason = verdicts.get(name, ("TEST_WRONG", "LLM không phân loại -> coi là test sai"))
            if verdict == "SUSPECTED_BUG":
                # GIỮ NGUYÊN test, chỉ gắn nhãn -> không "sửa test cho khớp code"
                self.suspected[name] = reason
                self.code = cu.add_suspected_marker(self.code, name, reason)
                self._message(f"SUSPECTED_BUG: {name} — {reason}")
            elif self.fix_attempts.get(name, 0) >= self.config.max_fix_attempts:
                to_remove.append(name)
            else:
                self.fix_attempts[name] = self.fix_attempts.get(name, 0) + 1
                to_fix.append(name)

        if to_remove:
            self.code = cu.remove_functions(self.code, to_remove)
            entry.removed_tests = to_remove
            self._message(f"Xoá test sửa mãi không được: {', '.join(to_remove)}")

        if to_fix:
            fix_failures = "\n\n".join(f"### {t.name}\n{t.message[:800]}" for t in failing
                                       if cu.base_test_name(t.name) in to_fix)
            answer = self.client.chat(
                prompts.SYSTEM_PROMPT,
                prompts.fix_tests_prompt(self.module_name, self.source, cu.get_functions_code(self.code, to_fix),
                                         fix_failures, self._lessons_for_error(fix_failures)),
                task="fix_tests",
            )
            entry.lesson = cu.extract_lesson(answer)
            self._merge(cu.extract_code(answer), on_conflict="replace")
            self._remember_fix(fix_failures, entry.lesson)

        n_bug = sum(1 for c in entry.classifications if c["verdict"] == "SUSPECTED_BUG")
        entry.reason = (f"{len(names)} test fail -> LLM phân loại: {n_bug} nghi bug (giữ + gắn nhãn), "
                        f"{len(to_fix)} test sai (sửa), {len(to_remove)} xoá")
        self._message(entry.reason)
        self._emit(entry)

    def _improve_coverage(self, entry: IterationLog, result: RunResult):
        entry.phase, entry.action = "coverage", "improve_coverage"
        entry.reason = (f"Coverage line {result.line_coverage}% / branch {result.branch_coverage}% "
                        f"chưa đạt ngưỡng {self.config.line_threshold}/{self.config.branch_threshold}% "
                        f"-> đưa {len(result.missing_lines)} dòng, {len(result.missing_branches)} nhánh chưa phủ cho LLM")
        self._message(entry.reason)
        prompt = prompts.coverage_prompt(self.module_name, cu.number_lines(self.source), self.code,
                                         result.line_coverage, result.branch_coverage,
                                         describe_missing(self.source, result))
        answer = self.client.chat(prompts.SYSTEM_PROMPT, prompt, task="improve_coverage")
        self._merge(cu.extract_code(answer), on_conflict="rename")
        self._emit(entry)

    def _mutation_step(self, entry: IterationLog) -> bool:
        """Phase mutation — được cài đặt ở GĐ5."""
        self._finish(entry, "stop", "Mutation testing chưa được cài đặt")
        return False

    # ================================================================ TIỆN ÍCH
    def _merge(self, new_code: str, on_conflict: str):
        """Ghép code LLM trả về vào bộ test; bỏ qua nếu code rỗng hoặc sai cú pháp."""
        if not new_code:
            self._message("LLM không trả về code -> bỏ qua")
            return
        try:
            self.code = cu.merge_tests(self.code, new_code, on_conflict=on_conflict)
        except SyntaxError as exc:
            self._message(f"Code LLM trả về sai cú pháp ({exc.msg}) -> bỏ qua lần này")

    def _improved(self, score: float) -> bool:
        """Cập nhật bộ đếm "không cải thiện". Trả về True nếu còn nên tiếp tục cải tiến."""
        if score > self.best_score + 0.01:
            self.best_score = score
            self.no_improve = 0
        else:
            self.no_improve += 1
        return self.no_improve < self.config.patience

    def _new_entry(self, it: int, result: RunResult) -> IterationLog:
        entry = IterationLog(
            iteration=it, phase=self.phase, action="", reason="", test_code=self.code,
            passed=result.passed, failed=result.failed, errors=result.errors, xfailed=result.xfailed,
            collection_error=result.collection_error[:2000],
            line_coverage=result.line_coverage, branch_coverage=result.branch_coverage,
            missing_lines=result.missing_lines, missing_branches=result.missing_branches,
        )
        if self.last_mutation is not None:
            entry.mutation_score = self.last_mutation.score
            entry.mutants_total = self.last_mutation.total
            entry.mutants_killed = self.last_mutation.killed
        self.iterations.append(entry)
        self._message(f"Vòng {it}: {result.passed} pass, {result.failed + result.errors} fail, "
                      f"{result.xfailed} nghi bug | line {result.line_coverage}% | branch {result.branch_coverage}%")
        return entry

    def _finish(self, entry: IterationLog, action: str, reason: str):
        entry.phase, entry.action, entry.reason = "done", action, reason
        self.stop_reason = reason
        self._message(f"DỪNG: {reason}")
        self._emit(entry)

    def _emit(self, entry: IterationLog):
        entry.suspected = dict(self.suspected)
        entry.llm_calls_so_far = self.client.call_count
        entry.elapsed = round(time.time() - self.start_time, 1)
        self.progress("iteration", asdict(entry))

    def _message(self, text: str):
        print(f"[agent] {text}")
        self.progress("message", text)

    # ----------------------------------------------- bộ nhớ (được hoàn thiện ở GĐ6)
    def _lessons_for_initial(self) -> str:
        return ""

    def _lessons_for_error(self, error_text: str) -> str:
        return ""

    def _remember_fix(self, error_text: str, lesson: str):
        pass

    def _confirm_lessons(self):
        pass

    # ================================================================ LƯU KẾT QUẢ
    def _save(self) -> dict:
        final = self.iterations[-1] if self.iterations else None
        summary = {
            "module": self.module_name,
            "module_path": str(self.module_path),
            "label": self.config.label,
            "config": asdict(self.config),
            "llm": {"provider": self.client.settings.provider, "model": self.client.settings.model},
            "stop_reason": self.stop_reason,
            "iterations": [asdict(e) for e in self.iterations],
            "final_test_code": self.code,
            "suspected_bugs": dict(self.suspected),
            "lessons_used": self.lessons_used,
            "final": {
                "line_coverage": final.line_coverage if final else 0.0,
                "branch_coverage": final.branch_coverage if final else 0.0,
                "passed": final.passed if final else 0,
                "failed": (final.failed + final.errors) if final else 0,
                "xfailed": final.xfailed if final else 0,
                "mutation_score": self.last_mutation.score if self.last_mutation else None,
                "num_iterations": max(0, len(self.iterations) - 1),
            },
            "stats": {**self.client.stats(), "total_seconds": round(time.time() - self.start_time, 1)},
            "source_code": self.source,
        }
        # Log JSON (dùng cho REPLAY trên giao diện)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = LOGS_DIR / f"{self.module_name}_{self.config.label}_{stamp}.json"
        log_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["log_path"] = str(log_path)
        # File test cuối cùng
        out_dir = OUTPUT_DIR / self.config.label
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"test_{self.module_name}.py").write_text(self.code, encoding="utf-8")
        self._message(f"Đã lưu log: {log_path.name}")
        return summary


def main():
    parser = argparse.ArgumentParser(description="Agent sinh test với vòng lặp tự cải tiến")
    parser.add_argument("module", help="đường dẫn module, ví dụ targets/grading.py")
    parser.add_argument("--max-iters", type=int, default=8)
    parser.add_argument("--line", type=float, default=95.0, help="ngưỡng line coverage")
    parser.add_argument("--branch", type=float, default=90.0, help="ngưỡng branch coverage")
    parser.add_argument("--label", default="agent")
    args = parser.parse_args()

    config = AgentConfig(max_iterations=args.max_iters, line_threshold=args.line,
                         branch_threshold=args.branch, label=args.label)
    summary = TestGenAgent(args.module, config=config).run()
    print("\n=== KẾT QUẢ ===")
    print(json.dumps({k: summary[k] for k in ("stop_reason", "final", "suspected_bugs", "stats")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
