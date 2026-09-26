# CLAUDE.md — Bộ nhớ dự án cho các phiên làm việc sau

## Mục tiêu
Đồ án môn học (sinh viên CS năm cuối, demo cuối kỳ):
**"LLM Agent tự sinh unit test đa ngôn ngữ với vòng lặp tự cải tiến dựa trên phản hồi coverage và mutation testing"**.
Hiện thực 2 ngôn ngữ theo kiến trúc **Adapter**: Python và JavaScript/TypeScript. Java/Go là hướng phát triển.
Đề bài gốc (bản chỉ-Python): `docs/DE_BAI.md`. Kế hoạch refactor đa ngôn ngữ: `docs/KE_HOACH_REFACTOR.md`.

## Công nghệ
- Python 3.10+ (máy dev: 3.14, Windows 11); Node.js 22+ (máy dev: 24) cho phần JS/TS (`npm install`).
- **Python**: pytest + pytest-cov/coverage.py + **toán tử đột biến của mutmut 2.5.1** (`mutmut.list_mutations/mutate`)
  + runner tự viết (mutmut 3.x không chạy trên Windows).
- **JS/TS**: Jest 30 + babel-jest (preset-env + preset-typescript, không kiểm tra kiểu) + Istanbul + StrykerJS 10.
  Nhãn nghi bug: `// SUSPECTED_BUG: ...` + `test.failing(...)`. Thư mục tạm chạy Jest nằm trong `workspace/js_runs/`
  (để Node tìm thấy `node_modules/`).
- LLM: đọc từ `.env` (`LLM_PROVIDER`, `LLM_MODEL`, key). Hỗ trợ openrouter, deepseek, openai, anthropic, ollama, mock.
  `.env` đang dùng OpenRouter + `nvidia/nemotron-3-super-120b-a12b:free` (50 request/ngày; key KHÔNG commit).
- Demo: Streamlit (`app.py`), biểu đồ matplotlib, slide Marp (`slides/`).

## Quy tắc (bắt buộc)
1. Code đơn giản, dễ đọc cho sinh viên. KHÔNG dùng LangChain hay framework agent — tự viết vòng lặp.
2. Comment tiếng Việt ở chỗ quan trọng.
3. Git: commit sau MỖI bước, message rõ ràng. Không commit `.env`, `node_modules/`.
4. Sau mỗi bước tự chạy kiểm tra: `pytest` (test của công cụ) **và** kiểm tra hồi quy phần Python:
   `python scripts/snapshot_python.py --out <tạm>.json --compare docs/baseline_truoc_refactor.json` → phải
   "Phần tất định GIỐNG HỆT" (prompt Python giống từng ký tự, runner/mutation/agent-mock giống hệt).
5. Sau mỗi bước thêm một mục vào `HOC_TAP.md`: (a) đã làm gì & tại sao, (b) khái niệm quan trọng + ví dụ,
   (c) file liên quan, (d) lệnh tự chạy thử, (e) 2-3 câu hỏi giảng viên có thể hỏi + gợi ý trả lời.
6. Trung thực: không phóng đại kết quả, ghi rõ hạn chế. Không bịa số liệu; kết quả mock không được trình bày như kết quả thật.
7. Bug cài sẵn trong `targets/` chỉ ghi trong `BUGS.md`, KHÔNG comment trong code. Bản đã sửa nằm ở
   `evaluation/fixed_targets/<ngôn ngữ>/` (chỉ dùng để chấm "phát hiện bug").
8. Không dùng heredoc bash có dấu `\` để sửa file (bị nuốt ký tự) — dùng Edit/Write hoặc script Python trong scratchpad.

## Cấu trúc chính
- `adapters/` — `base.py` (LanguageAdapter + dataclass chung), `registry.py`, `python_adapter.py` + `python_edit.py`,
  `javascript_adapter.py` + `js_edit.py` (bộ quét ngoặc), `common.py`
- `testgen/` — `agent.py` (vòng lặp, chỉ gọi `self.adapter.*`), `prompts.py` (khung chung + `hints`), `generator.py`,
  `runner.py`/`mutation.py` (cổng chung + CLI), `memory.py` (chia theo ngôn ngữ), `llm_client.py`, `config.py`, `code_utils.py`
- `targets/python/` (5 module, bug 1-2), `targets/javascript/` (4 module, bug 3-4)
- `tests/` — test của công cụ (LLM mock; test JS tự skip nếu chưa cài Node)
- `generated_tests/`, `logs/`, `memory/`, `results/` — đầu ra; `evaluate.py`, `app.py`, `slides/`, `docs/`, `scripts/`

## Tiến độ
- GĐ0–GĐ10 (bản chỉ-Python) xong trên nhánh `main`.
- Refactor đa ngôn ngữ trên nhánh `multi-language`: RF1–RF7 xong (xem `HOC_TAP.md` PHẦN 2). Việc còn lại:
  - Thực nghiệm JS cần LLM thật: `python evaluate.py --languages javascript --runs 1` (~30 request/lượt), rồi Python
    lượt 2–3 và JS lượt 2–3 (`python evaluate.py --runs 3`). Model miễn phí giới hạn 50 request/ngày
    (nạp 10 USD vào OpenRouter → 1000 request/ngày). Sau đó cập nhật bảng RF6 trong HOC_TAP, slide kết quả, lời thoại.
  - Chỉ gợi ý merge `multi-language` vào `main` khi mọi thứ ổn (Bước 9).
- Thiết kế thực nghiệm: bước SINH (log `logs/*_eval_C|D_*.json`, có trường `language`; log cũ không có = Python) tách
  bước CHẤM (`--measure-only`, mutation held-out: loại các mutant đã đưa vào prompt). Không được chấm mutation trên tập
  mutant LLM đã thấy.
