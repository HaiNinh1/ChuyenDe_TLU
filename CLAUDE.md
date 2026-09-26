# CLAUDE.md — Bộ nhớ dự án cho các phiên làm việc sau

## Mục tiêu
Đồ án môn học (sinh viên CS năm cuối, demo cuối kỳ):
**"LLM Agent tự sinh unit test cho Python với vòng lặp tự cải tiến dựa trên phản hồi coverage và mutation testing"**.
Đề bài gốc đầy đủ: `docs/DE_BAI.md`.

## Công nghệ
- Python 3.10+ (máy dev đang dùng 3.14, Windows 11), pytest, pytest-cov/coverage.py
- Mutation: dùng **toán tử đột biến của mutmut 2.5.1** (`mutmut.list_mutations/mutate`) + runner tự viết.
  Lý do: mutmut 3.x không chạy trên Windows; CLI mutmut 2 chạy được nhưng không giới hạn số mutant được.
- LLM: đọc từ `.env` (`LLM_PROVIDER`, `LLM_MODEL`, key). Hỗ trợ openrouter, deepseek, openai, anthropic, ollama, mock.
  Mặc định đang dùng OpenRouter + `z-ai/glm-5.2` (key trong `.env`, KHÔNG commit).
- Demo: Streamlit (`app.py`), biểu đồ matplotlib, slide Marp (`slides/`).

## Quy tắc (bắt buộc)
1. Code đơn giản, dễ đọc cho sinh viên. KHÔNG dùng LangChain hay framework agent — tự viết vòng lặp.
2. Comment tiếng Việt ở chỗ quan trọng.
3. Git: commit sau MỖI giai đoạn, message rõ ràng. Không commit `.env`.
4. Sau mỗi giai đoạn tự chạy kiểm tra (`pytest` cho test của công cụ trong `tests/`), lỗi thì tự sửa.
5. Sau mỗi giai đoạn thêm một mục vào `HOC_TAP.md`: (a) đã làm gì & tại sao, (b) khái niệm quan trọng + ví dụ,
   (c) file liên quan, (d) lệnh tự chạy thử, (e) 2-3 câu hỏi giảng viên có thể hỏi + gợi ý trả lời.
6. Trung thực: không phóng đại kết quả, ghi rõ hạn chế. Không bịa số liệu; kết quả mock không được trình bày như kết quả thật.
7. Bug cài sẵn trong `targets/` chỉ ghi trong `BUGS.md`, KHÔNG comment trong code. Bản đã sửa nằm ở `evaluation/fixed_targets/` (chỉ dùng để chấm "phát hiện bug").

## Cấu trúc chính
- `targets/` — code mục tiêu cần sinh test
- `testgen/` — công cụ: `config.py`, `llm_client.py`, `prompts.py`, `code_utils.py`, `generator.py`, `runner.py`, `mutation.py`, `memory.py`, `agent.py`
- `tests/` — test của chính công cụ (chạy bằng `pytest`, dùng LLM mock)
- `generated_tests/`, `logs/`, `memory/`, `results/` — đầu ra
- `evaluate.py` (thực nghiệm), `app.py` (Streamlit), `slides/`, `docs/`

## Tiến độ các giai đoạn
Xem các mục trong `HOC_TAP.md` và `git log`.
