# LLM Agent tự sinh unit test cho Python

> Đồ án môn học — *"LLM Agent tự sinh unit test cho Python với vòng lặp tự cải tiến dựa trên phản hồi coverage và
> mutation testing"*.

Agent dùng LLM để sinh unit test (pytest) cho một module Python, sau đó **tự cải tiến** bộ test qua nhiều vòng:

1. **Sinh** bộ test ban đầu từ mã nguồn + docstring (đặc tả).
2. **Chạy** test (pytest, trong thư mục tạm, có timeout) và **đo** line/branch coverage.
3. **Sửa**: file test lỗi cú pháp/import → LLM sửa; test fail → LLM phân loại *"test sai"* (sửa) hay
   *"nghi code có bug"* (giữ test, gắn nhãn `SUSPECTED_BUG`).
4. **Tăng coverage**: gửi các dòng/nhánh chưa phủ cho LLM viết thêm test.
5. **Mutation testing**: gửi các mutant còn sống cho LLM viết test "giết" chúng.
6. **Bộ nhớ tự học**: lưu bài học sửa lỗi và mẫu test tốt (JSON), đưa vào prompt ở lần sau.

Không dùng framework agent (LangChain...): vòng lặp là một vòng `for` + `if/else` trong `testgen/agent.py`.

Sơ đồ luồng (mermaid): `docs/agent_flow.md`.

---

## Cấu trúc thư mục

```
targets/                  5 module mục tiêu (dễ -> khó), có 2 bug cài sẵn (xem BUGS.md)
testgen/                  mã nguồn công cụ
  config.py               đọc .env
  llm_client.py           gọi LLM: openrouter | deepseek | openai | anthropic | ollama | mock; retry
  prompts.py              toàn bộ prompt
  code_utils.py           tách code khỏi câu trả lời LLM, ghép/sửa/xoá hàm test bằng ast, nhãn SUSPECTED_BUG
  generator.py            BASELINE: sinh test một lần
  runner.py               chạy pytest + coverage -> RunResult
  mutation.py             mutation testing (toán tử mutmut 2.5.1 + runner song song)
  memory.py               bộ nhớ tự học (JSON)
  agent.py                VÒNG LẶP TỰ CẢI TIẾN
evaluate.py               thực nghiệm A/B/C/D -> results/
app.py                    giao diện demo Streamlit
tests/                    test của chính công cụ (dùng LLM giả lập, không tốn API)
evaluation/fixed_targets/ bản đã sửa bug (chỉ dùng để chấm "phát hiện bug")
generated_tests/          test do LLM sinh ra
logs/                     log JSON từng lần chạy agent (dùng cho REPLAY)
results/                  runs.csv, results.csv, biểu đồ PNG
slides/                   slide Marp + lời thoại
docs/                     đề bài gốc, sơ đồ luồng
HOC_TAP.md                sổ tay học tập: giải thích từng giai đoạn + câu hỏi vấn đáp
```

---

## Cài đặt

Yêu cầu: Python 3.10+ (đã chạy thử trên Python 3.14, Windows 11).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
copy .env.example .env            # Linux/macOS: cp .env.example .env
```

Mở `.env`, chọn nhà cung cấp và điền key:

| `LLM_PROVIDER` | Key cần điền | Model gợi ý |
|---|---|---|
| `openrouter` | `OPENROUTER_API_KEY` | `nvidia/nemotron-3-super-120b-a12b:free` (miễn phí, 50 request/ngày) hoặc `z-ai/glm-5.2` (trả phí) |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5-20251001` |
| `ollama` | (không cần) | `qwen2.5-coder:7b` (cần cài Ollama) |
| `mock` | (không cần) | LLM giả lập, chỉ để thử pipeline — **không dùng làm kết quả** |

> **Lưu ý mutmut:** dự án ghim `mutmut==2.5.1` vì mutmut 3.x không chạy trên Windows. Chỉ dùng phần sinh mutant của
> mutmut; phần chạy mutant tự viết trong `testgen/mutation.py`.

---

## Cách chạy từng phần

```bash
# 0) Kiểm tra công cụ (không tốn API, ~1 phút)
pytest

# 1) Baseline: sinh test một lần
python -m testgen.generator targets/grading.py
pytest generated_tests/baseline/test_grading.py

# 2) Runner: chạy test + đo coverage
python -m testgen.runner targets/grading.py generated_tests/baseline/test_grading.py

# 3) Mutation testing một bộ test
python -m testgen.mutation targets/grading.py generated_tests/baseline/test_grading.py

# 4) Agent (vòng lặp tự cải tiến)
python -m testgen.agent targets/shopping_cart.py                         # chỉ coverage
python -m testgen.agent targets/calculator.py --mutation                 # + mutation
python -m testgen.agent targets/safe_parser.py --mutation --memory       # + bộ nhớ

# 5) Thực nghiệm: bước SINH lưu log logs/*_eval_*.json (chạy lại chỉ chạy phần còn thiếu), bước CHẤM ra results/
python evaluate.py --quick                 # thử nhanh: module grading, 1 lần
python evaluate.py --runs 3                # đầy đủ: 5 module x 4 cấu hình x 3 lần
python evaluate.py --measure-only          # không gọi LLM: chấm lại từ log + vẽ biểu đồ

# 6) Giao diện demo
streamlit run app.py
```

Kết quả đầu ra:
- `generated_tests/<cấu hình>/test_<module>.py` — bộ test cuối cùng
- `logs/<module>_<cấu hình>_<thời gian>.json` — log từng vòng (REPLAY trên giao diện)
- `memory/memory.json` — bộ nhớ tự học
- `results/results.csv`, `results/summary.png`, `results/mutation_by_module.png` — thực nghiệm

---

## Chạy demo

```bash
streamlit run app.py
```

- **Chạy mới:** chọn module mẫu (hoặc dán code có docstring) → bật/tắt mutation, bộ nhớ → **Chạy agent**. Tab
  *Tiến trình* hiện từng vòng; tab *Biểu đồ* vẽ coverage/mutation qua các vòng; tab *Code test* xem code mỗi vòng,
  test `SUSPECTED_BUG` được **tô đỏ**, có chế độ xem *diff*.
- **REPLAY từ log:** phát lại một lần chạy đã lưu trong `logs/` — **không cần mạng/API** (phương án dự phòng khi demo).
- **Kết quả thực nghiệm:** bảng + biểu đồ từ `results/`.

Kịch bản demo 5 phút: xem `DEMO_CHECKLIST.md`.

---

## Kết quả & hạn chế

Xem `HOC_TAP.md` (mục GĐ7) để có số liệu, cách đo và **hạn chế** (quy mô thực nghiệm nhỏ do giới hạn request của model
miễn phí, LLM có thể phân loại sai, test "bám" chi tiết cài đặt khi tối ưu mutation score, bộ nhớ chỉ là học trong
ngữ cảnh...).

## Đọc code theo thứ tự nào?

`targets/grading.py` → `testgen/prompts.py` → `testgen/generator.py` → `testgen/runner.py` → `testgen/agent.py`
(`run`, `_step`) → `testgen/code_utils.py` → `testgen/mutation.py` → `testgen/memory.py` → `evaluate.py` → `app.py`.
