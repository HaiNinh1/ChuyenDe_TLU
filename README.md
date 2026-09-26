# LLM Agent tự sinh unit test đa ngôn ngữ

> Đồ án môn học — *"LLM Agent tự sinh unit test đa ngôn ngữ với vòng lặp tự cải tiến dựa trên phản hồi coverage và
> mutation testing"*. Hiện thực cho **Python** và **JavaScript/TypeScript** theo kiến trúc **Adapter**.

Agent dùng LLM để sinh unit test cho một module, sau đó **tự cải tiến** bộ test qua nhiều vòng:

1. **Sinh** bộ test ban đầu từ mã nguồn + đặc tả (docstring / JSDoc).
2. **Chạy** test (thư mục tạm, có timeout) và **đo** line/branch coverage.
3. **Sửa**: file test lỗi cú pháp/import → LLM sửa; test fail → LLM phân loại *"test sai"* (sửa) hay
   *"nghi code có bug"* (giữ test, gắn nhãn `SUSPECTED_BUG`).
4. **Tăng coverage**: gửi các dòng/nhánh chưa phủ cho LLM viết thêm test.
5. **Mutation testing**: gửi các mutant còn sống cho LLM viết test "giết" chúng.
6. **Bộ nhớ tự học**: lưu bài học sửa lỗi và mẫu test tốt (JSON, **chia theo ngôn ngữ**), đưa vào prompt ở lần sau.

Không dùng framework agent (LangChain...): vòng lặp là một vòng `for` + `if/else` trong `testgen/agent.py`.
Agent **không biết** đang làm việc với ngôn ngữ nào — mọi việc phụ thuộc ngôn ngữ đi qua một `LanguageAdapter`:

| Ngôn ngữ | Đuôi file | Chạy test | Coverage | Mutation | Nhãn nghi bug |
|---|---|---|---|---|---|
| Python | `.py` | pytest | coverage.py (pytest-cov) | toán tử mutmut 2.5.1 + runner tự viết | `@pytest.mark.xfail` |
| JavaScript / TypeScript | `.js`, `.ts` | Jest | Istanbul (có sẵn trong Jest) | StrykerJS | `test.failing` |

Sơ đồ: `docs/agent_flow.md` (vòng lặp), `docs/KE_HOACH_REFACTOR.md` (kiến trúc trước/sau refactor).
Thêm ngôn ngữ mới (ví dụ Java): `docs/THEM_NGON_NGU_MOI.md`.

---

## Cấu trúc thư mục

```
adapters/                 KIẾN TRÚC ADAPTER — mỗi ngôn ngữ một "phích cắm"
  base.py                 lớp trừu tượng LanguageAdapter + dataclass kết quả dùng chung
  registry.py             đuôi file -> adapter; đoán ngôn ngữ của code dán vào
  python_adapter.py       pytest + coverage.py + mutmut      (python_edit.py: sửa file test bằng ast)
  javascript_adapter.py   Jest + Istanbul + StrykerJS         (js_edit.py: sửa file test bằng bộ quét ngoặc)
  common.py               chạy tiến trình con có timeout
testgen/                  vòng lặp agent + phần dùng chung (không biết ngôn ngữ)
  config.py               đọc .env
  llm_client.py           gọi LLM: openrouter | deepseek | openai | anthropic | ollama | mock; retry
  prompts.py              khung prompt chung (phần riêng của ngôn ngữ lấy từ adapter.prompt_hints())
  code_utils.py           tách code / LESSON / JSON khỏi câu trả lời LLM
  generator.py            BASELINE: sinh test một lần
  runner.py, mutation.py  "cổng chung": chọn adapter theo đuôi file + lệnh CLI
  memory.py               bộ nhớ tự học (JSON, chia theo ngôn ngữ)
  agent.py                VÒNG LẶP TỰ CẢI TIẾN
targets/python/           5 module Python (dễ -> khó), 2 bug cài sẵn
targets/javascript/       4 module JS/TS (dễ -> khó), 2 bug cài sẵn      (xem BUGS.md)
evaluation/fixed_targets/ bản đã sửa bug (chỉ dùng để chấm "phát hiện bug")
evaluate.py               thực nghiệm A/B/C/D trên cả hai ngôn ngữ -> results/
app.py                    giao diện demo Streamlit
tests/                    test của chính công cụ (LLM giả lập, không tốn API)
scripts/snapshot_python.py  chụp hành vi phần Python để chứng minh refactor không làm hỏng
generated_tests/ logs/ results/ memory/   đầu ra
slides/ docs/ HOC_TAP.md  slide, tài liệu, sổ tay học tập
package.json              công cụ Node.js (Jest, Babel, StrykerJS)
```

---

## Cài đặt

Yêu cầu: **Python 3.10+** và **Node.js 22+** (đã chạy thử trên Python 3.14, Node 24, Windows 11).
Chỉ dùng Python thì có thể bỏ qua phần Node.js — adapter JS sẽ báo "chưa cài" kèm hướng dẫn, phần Python vẫn chạy.

```bash
# Python
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt

# Node.js (cho JavaScript/TypeScript): cài Node 22+ từ https://nodejs.org rồi
npm install                       # cài Jest, Babel, StrykerJS vào node_modules/ theo package.json

copy .env.example .env            # Linux/macOS: cp .env.example .env
```

Mở `.env`, chọn nhà cung cấp và điền key:

| `LLM_PROVIDER` | Key cần điền | Model gợi ý |
|---|---|---|
| `openrouter` | `OPENROUTER_API_KEY` | `nvidia/nemotron-3-super-120b-a12b:free` (miễn phí, 50 request/ngày; nạp 10 USD → 1000 request/ngày) hoặc `z-ai/glm-5.2` (trả phí) |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5-20251001` |
| `ollama` | (không cần) | `qwen2.5-coder:7b` (cần cài Ollama) |
| `mock` | (không cần) | LLM giả lập, chỉ để thử pipeline — **không dùng làm kết quả** |

> **Lưu ý mutmut:** dự án ghim `mutmut==2.5.1` vì mutmut 3.x không chạy trên Windows. Chỉ dùng phần sinh mutant của
> mutmut; phần chạy mutant tự viết trong `adapters/python_adapter.py`.

---

## Cách chạy từng phần

Ngôn ngữ được **tự nhận diện theo đuôi file** — cùng một lệnh cho Python và JS/TS.

```bash
# 0) Kiểm tra công cụ (117 test, không tốn API, ~8 phút; test JS tự bỏ qua nếu chưa cài Node)
pytest

# 1) Baseline: sinh test một lần
python -m testgen.generator targets/python/grading.py
python -m testgen.generator targets/javascript/shipping.ts

# 2) Chạy test + đo coverage một bộ test có sẵn
python -m testgen.runner targets/python/grading.py generated_tests/baseline/test_grading.py
python -m testgen.runner targets/javascript/shipping.ts generated_tests/agent_js/shipping.test.ts

# 3) Mutation testing một bộ test
python -m testgen.mutation targets/javascript/shipping.ts generated_tests/agent_js/shipping.test.ts

# 4) Agent (vòng lặp tự cải tiến)
python -m testgen.agent targets/python/shopping_cart.py                      # chỉ coverage
python -m testgen.agent targets/python/calculator.py --mutation              # + mutation
python -m testgen.agent targets/javascript/bank_account.js --mutation --memory   # JS + mutation + bộ nhớ

# 5) Thực nghiệm: bước SINH lưu log logs/*_eval_*.json (chạy lại chỉ chạy phần còn thiếu), bước CHẤM ra results/
python evaluate.py --quick                          # thử nhanh: grading (Python) + shipping (TS), 1 lần
python evaluate.py --languages javascript --runs 1  # chỉ JavaScript
python evaluate.py --runs 3                         # đầy đủ: 5 module Python + 4 module JS, 3 lần
python evaluate.py --measure-only                   # không gọi LLM: chấm lại từ log + vẽ biểu đồ

# 6) Giao diện demo
streamlit run app.py

# Kiểm tra refactor không làm hỏng phần Python (so với ảnh chụp trước refactor)
python scripts/snapshot_python.py --out docs/thu.json --compare docs/baseline_truoc_refactor.json
```

Kết quả đầu ra:
- `generated_tests/<cấu hình>/test_<module>.py` hoặc `<module>.test.js|ts` — bộ test cuối cùng
- `logs/<module>_<cấu hình>_<thời gian>.json` — log từng vòng (REPLAY trên giao diện), có trường `language`
- `memory/memory.json` — bộ nhớ tự học (chia theo ngôn ngữ)
- `results/results.csv` (theo ngôn ngữ + cấu hình), `results/summary_<ngôn ngữ>.png`,
  `results/mutation_by_module_<ngôn ngữ>.png`, `results/language_comparison.png` — thực nghiệm

---

## Chạy demo

```bash
streamlit run app.py
```

- **Chạy mới:** chọn **ngôn ngữ** + module mẫu, hoặc **dán code** (ngôn ngữ được tự nhận diện, có thể chọn lại).
  Thanh bên hiện **công cụ đang dùng** và báo nếu chưa cài. Bật/tắt mutation, bộ nhớ → **Chạy agent**. Tab
  *Tiến trình* hiện từng vòng; tab *Biểu đồ* vẽ coverage/mutation qua các vòng; tab *Code test* xem code mỗi vòng,
  test `SUSPECTED_BUG` được **tô đỏ**, có chế độ xem *diff*.
- **REPLAY từ log:** phát lại một lần chạy đã lưu trong `logs/` (có log mẫu cho cả Python và JS) — **không cần
  mạng/API** (phương án dự phòng khi demo).
- **Kết quả thực nghiệm:** bảng + biểu đồ theo từng ngôn ngữ và biểu đồ so sánh hai ngôn ngữ.

Kịch bản demo 5 phút: xem `DEMO_CHECKLIST.md`.

---

## Kết quả & hạn chế

Xem `HOC_TAP.md` (GĐ7 cho Python, RF6 cho đa ngôn ngữ) để có số liệu, cách đo và **hạn chế**: quy mô thực nghiệm nhỏ
do giới hạn request của model miễn phí; mới hiện thực 2 ngôn ngữ (Java/Go là hướng phát triển); bộ quét ngoặc cho
JS không hiểu hết cú pháp (không gắn nhãn được test trong `describe`); LLM có thể phân loại sai; test "bám" chi tiết
cài đặt khi tối ưu mutation score; bộ nhớ chỉ là học trong ngữ cảnh...

## Đọc code theo thứ tự nào?

`adapters/base.py` → `adapters/registry.py` → `testgen/agent.py` (`__init__`, `run`, `_step`) →
`adapters/python_adapter.py` → `testgen/prompts.py` → `adapters/javascript_adapter.py` → `adapters/js_edit.py` →
`testgen/memory.py` → `evaluate.py` → `app.py`. Chi tiết: mục cuối `HOC_TAP.md`.
