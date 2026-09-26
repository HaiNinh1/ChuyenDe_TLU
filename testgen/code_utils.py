"""Các hàm tiện ích xử lý câu trả lời LLM — DÙNG CHUNG cho mọi ngôn ngữ.

Tách code khỏi câu trả lời, đọc dòng LESSON, đọc JSON, đánh số dòng.
(Các hàm đọc/sửa file test theo cú pháp từng ngôn ngữ nằm trong adapters/: python_edit.py, js_edit.py.)
"""
import json
import re


# ----------------------------------------------------------------- đọc câu trả lời LLM
def extract_code(text: str, tags=("python", "py"), markers=("def test", "import ")) -> str:
    """Lấy code trong các khối ```<thẻ> ... ``` của câu trả lời LLM.

    tags: các thẻ ngôn ngữ chấp nhận (khối không có thẻ cũng được nhận) — adapter cung cấp,
          ví dụ Python ("python", "py"), JavaScript ("javascript", "js", "typescript", "ts").
    markers: LLM quên bọc code mà câu trả lời chứa một trong các dấu hiệu này -> dùng luôn cả câu trả lời.
    """
    pattern = r"```(?:" + "|".join(re.escape(t) for t in tags) + r")?[ \t]*\n(.*?)```"
    blocks = re.findall(pattern, text, flags=re.DOTALL)
    if blocks:
        return "\n\n".join(block.strip() for block in blocks).strip() + "\n"
    # LLM quên bọc code: nếu trông giống code thì dùng luôn
    if any(marker in text for marker in markers):
        return text.strip() + "\n"
    return ""


def extract_lesson(text: str) -> str:
    """Lấy dòng `LESSON: ...` (bài học) nếu LLM có viết."""
    match = re.search(r"LESSON:\s*(.+)", text)
    return match.group(1).strip() if match else ""


def extract_json(text: str) -> dict:
    """Lấy object JSON trong câu trả lời (LLM hay bọc JSON trong ```json``` hoặc viết thêm chữ xung quanh).

    Thử lần lượt từ mỗi dấu "{": raw_decode đọc đúng MỘT object JSON rồi dừng, nên chữ thừa (kể cả chữ có
    dấu ngoặc nhọn) trước/sau JSON không làm hỏng việc đọc.
    """
    decoder = json.JSONDecoder()
    for start in [i for i, ch in enumerate(text) if ch == "{"]:
        try:
            obj, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


# ---------------------------------------------------------------------- hiển thị
def number_lines(source: str) -> str:
    """Đánh số dòng cho mã nguồn để LLM hiểu "dòng 17" là dòng nào."""
    return "\n".join(f"{i:4d} | {line}" for i, line in enumerate(source.splitlines(), start=1))
