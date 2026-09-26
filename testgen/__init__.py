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
