"""testgen — LLM Agent tự sinh unit test cho Python.

Các module chính (đọc theo thứ tự này để hiểu nhanh):
    config.py      đọc cấu hình từ .env
    llm_client.py  gọi LLM (nhiều nhà cung cấp, có retry)
    prompts.py     toàn bộ prompt gửi cho LLM
    code_utils.py  tách code từ câu trả lời LLM, ghép/sửa hàm test
    generator.py   BASELINE: sinh test một lần
    runner.py      chạy pytest + đo coverage
    mutation.py    mutation testing (toán tử của mutmut)
    memory.py      bộ nhớ "tự học" (JSON)
    agent.py       VÒNG LẶP TỰ CẢI TIẾN (cốt lõi)
"""
import sys

# Windows: khi in ra file/pipe, Python mặc định dùng bảng mã cp1252 -> lỗi với tiếng Việt.
# Chuyển stdout/stderr sang UTF-8 để lệnh print() không bao giờ làm chương trình dừng.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
