"""Bộ nhớ "tự học" đơn giản, lưu trong một file JSON (không dùng vector database).

Lưu 2 loại kinh nghiệm:
1. BÀI HỌC SỬA LỖI (lessons): khi LLM sửa một lỗi THÀNH CÔNG (lần chạy sau lỗi biến mất), lưu lại
   loại lỗi (vd. ImportError) + một câu bài học do chính LLM rút ra (dòng `LESSON:` trong câu trả lời).
2. MẪU TEST TỐT (good_tests): các test mới đã làm TĂNG coverage hoặc GIẾT được mutant.

Khi sinh test cho module mới: chọn vài bài học + mẫu test "liên quan" (dựa trên nhãn đặc điểm của module
như `class`, `exception`, `branches`... — do adapter của ngôn ngữ tính, xem LanguageAdapter.module_tags)
và chèn vào prompt.

"Học" ở đây là HỌC TRONG NGỮ CẢNH (in-context learning): mô hình LLM KHÔNG thay đổi trọng số,
chỉ nhận thêm kinh nghiệm cũ trong prompt. Xem giải thích và giới hạn trong HOC_TAP.md (GĐ6).
"""
import json
import re
from datetime import datetime
from pathlib import Path

from .config import ROOT_DIR

MEMORY_FILE = ROOT_DIR / "memory" / "memory.json"
MAX_LESSONS = 50       # giới hạn kích thước bộ nhớ (bài học cũ ít dùng nhất bị xoá trước)
MAX_GOOD_TESTS = 30


def error_type(error_text: str) -> str:
    """Lấy tên loại lỗi đầu tiên trong thông báo, ví dụ 'ImportError', 'AssertionError'."""
    match = re.search(r"\b([A-Z]\w*(?:Error|Exception))\b", error_text or "")
    return match.group(1) if match else "Other"


def _words(text: str) -> set:
    return set(re.findall(r"\w+", text.lower()))


class Memory:
    def __init__(self, path: Path = MEMORY_FILE):
        self.path = Path(path)
        self.data = {"lessons": [], "good_tests": []}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def lessons(self) -> list:
        return self.data["lessons"]

    @property
    def good_tests(self) -> list:
        return self.data["good_tests"]

    # ------------------------------------------------------------------ GHI
    def add_lesson(self, error_text: str, lesson: str, module: str, tags: list):
        """Lưu bài học sửa lỗi. Bài học gần giống bài đã có -> chỉ tăng bộ đếm (tránh trùng lặp)."""
        lesson = (lesson or "").strip()
        if len(lesson) < 10 or "(mock)" in lesson:
            return
        etype = error_type(error_text)
        for old in self.lessons:
            overlap = len(_words(old["text"]) & _words(lesson)) / max(1, len(_words(old["text"]) | _words(lesson)))
            if old["error_type"] == etype and overlap > 0.6:
                old["times_seen"] += 1
                return
        self.lessons.append({
            "error_type": etype, "text": lesson, "module": module, "tags": tags,
            "times_seen": 1, "times_used": 0, "created": datetime.now().isoformat(timespec="seconds"),
        })
        if len(self.lessons) > MAX_LESSONS:
            self.lessons.sort(key=lambda x: (x["times_seen"] + x["times_used"], x["created"]))
            del self.lessons[0]

    def add_good_test(self, code: str, module: str, tags: list, reason: str):
        """Lưu một mẫu test tốt (giới hạn độ dài để prompt không phình to)."""
        code = code.strip()
        if not code or len(code.splitlines()) > 25:
            return
        if any(t["code"] == code for t in self.good_tests):
            return
        self.good_tests.append({"module": module, "tags": tags, "reason": reason, "code": code,
                                "created": datetime.now().isoformat(timespec="seconds")})
        if len(self.good_tests) > MAX_GOOD_TESTS:
            del self.good_tests[0]

    # ------------------------------------------------------------------ ĐỌC
    def relevant_lessons(self, tags: list, error_text: str = "", k: int = 5) -> list:
        """Chọn k bài học liên quan nhất: trùng loại lỗi (+3), trùng nhãn module (+1 mỗi nhãn), hay gặp (+0.1)."""
        etype = error_type(error_text) if error_text else None
        scored = []
        for lesson in self.lessons:
            score = len(set(tags) & set(lesson["tags"])) + 0.1 * lesson["times_seen"]
            if etype and lesson["error_type"] == etype:
                score += 3
            scored.append((score, lesson))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [lesson for _, lesson in scored[:k]]

    def relevant_good_tests(self, tags: list, exclude_module: str = "", k: int = 2) -> list:
        """Chọn k mẫu test của module KHÁC có nhiều nhãn chung nhất."""
        candidates = [t for t in self.good_tests if t["module"] != exclude_module and set(tags) & set(t["tags"])]
        candidates.sort(key=lambda t: len(set(tags) & set(t["tags"])), reverse=True)
        return candidates[:k]

    def format_for_prompt(self, module: str, tags: list, error_text: str = "", with_examples: bool = True,
                          fence: str = "python") -> str:
        """Tạo đoạn văn bản chèn vào prompt. Rỗng nếu bộ nhớ chưa có gì liên quan."""
        lessons = self.relevant_lessons(tags, error_text)
        parts = []
        for lesson in lessons:
            lesson["times_used"] += 1
            parts.append(f"- [{lesson['error_type']}] {lesson['text']}")
        if with_examples:
            for example in self.relevant_good_tests(tags, exclude_module=module):
                parts.append(f"- Mẫu test tốt ({example['reason']}, từ module {example['module']}):\n"
                             f"```{fence}\n{example['code']}\n```")
        return "\n".join(parts)

    def stats(self) -> dict:
        return {"lessons": len(self.lessons), "good_tests": len(self.good_tests)}
