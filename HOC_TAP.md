# HỌC TẬP — Nhật ký dự án "LLM Agent tự sinh unit test"

File này là "sổ tay học tập": sau mỗi giai đoạn (GĐ) có một mục gồm
(a) đã làm gì và tại sao, (b) khái niệm quan trọng, (c) file cần đọc, (d) lệnh tự chạy thử,
(e) câu hỏi giảng viên có thể hỏi kèm gợi ý trả lời.

> Đề bài gốc (nội dung ban đầu của file này) được giữ nguyên tại `docs/DE_BAI.md`.

---

## GĐ0 — Khởi tạo dự án

### (a) Đã làm gì và tại sao
- Tạo cấu trúc thư mục, tách rõ **đối tượng được test** (`targets/`), **công cụ** (`testgen/`),
  **test của chính công cụ** (`tests/`) và **đầu ra** (`generated_tests/`, `logs/`, `results/`).
  Tách như vậy để không lẫn "test do LLM sinh" với "test kiểm tra công cụ của mình".
- Tạo môi trường ảo `.venv` và `requirements.txt` để ai cũng cài được đúng thư viện.
- `.env.example` + `.env`: cấu hình LLM (nhà cung cấp, model, key) nằm ngoài code → đổi nhà cung cấp
  chỉ cần sửa `.env`, không sửa code. `.env` nằm trong `.gitignore` để **không lộ API key** lên git.
- `pytest.ini`: đặt `testpaths = tests` để lệnh `pytest` chỉ chạy test của công cụ, không vô tình chạy
  các file test do LLM sinh ra.
- `CLAUDE.md`: lưu mục tiêu + quy tắc để các phiên làm việc sau vẫn nhớ.
- Giữ đề bài gốc ở `docs/DE_BAI.md`.

**Phát hiện quan trọng khi khởi tạo:** `mutmut` bản mới (3.x) **không chạy trên Windows** (nó báo
"please use the WSL" vì cần `os.fork`). Vì vậy dự án ghim `mutmut==2.5.1` và chỉ dùng **phần sinh mutant**
của mutmut (hàm `list_mutations`, `mutate`), còn phần chạy test cho từng mutant thì tự viết. Lợi ích phụ:
ta giới hạn được số mutant để demo chạy nhanh (CLI của mutmut không làm được việc này).

### (b) Khái niệm quan trọng
- **Môi trường ảo (virtualenv):** một thư mục chứa Python + thư viện riêng cho dự án, tránh xung đột
  phiên bản với dự án khác. Ví dụ: dự án A cần `pytest 7`, dự án B cần `pytest 9` → mỗi dự án một `.venv`.
- **Biến môi trường & file `.env`:** thay vì viết `api_key = "sk-..."` trong code (nguy hiểm khi push
  lên GitHub), ta viết `OPENROUTER_API_KEY=sk-...` trong `.env` và code đọc bằng `os.getenv(...)`.
- **Tách cấu hình khỏi code:** muốn đổi từ OpenRouter sang DeepSeek chỉ cần đổi `LLM_PROVIDER=deepseek`.

### (c) File liên quan
`requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `CLAUDE.md`, `README.md`

### (d) Lệnh tự chạy thử
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
git log --oneline
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Vì sao không để API key trong code?** → Key trong code sẽ bị lộ khi commit/push; ai có key có thể
   dùng tiền của mình. `.env` + `.gitignore` giữ key ở máy local.
2. **Vì sao dùng mutmut 2.5.1 mà không phải bản mới nhất?** → mutmut 3 không hỗ trợ Windows. Em chỉ dùng
   bộ toán tử đột biến của mutmut 2 và tự viết phần chạy để giới hạn số mutant và phạm vi (1 module).
3. **Vì sao cần `pytest.ini` với `testpaths`?** → Để phân biệt test của công cụ với test do LLM sinh
   (các test sinh ra import module theo tên và chỉ chạy đúng trong thư mục tạm do runner tạo).

---

## GĐ1 — Code mục tiêu (`targets/`)

### (a) Đã làm gì và tại sao
Viết 5 module nhỏ, độ khó tăng dần, để agent có "đề bài" sinh test:

| Module | Độ khó | Đặc điểm cần test |
|--------|--------|-------------------|
| `calculator.py` | dễ | hàm tính toán, 1 vòng lặp, ném ngoại lệ đơn giản |
| `text_utils.py` | dễ-TB | xử lý chuỗi, trường hợp biên (chuỗi rỗng, khoảng trắng) |
| `grading.py` | TB | **nhiều nhánh if/elif**, điều kiện kép (`and`) → branch coverage có ý nghĩa |
| `safe_parser.py` | TB-khó | **try/except**, class exception riêng, `raise ... from ...` |
| `shopping_cart.py` | khó | **class có trạng thái**: kết quả phụ thuộc chuỗi thao tác trước đó |

- Mỗi hàm có **docstring mô tả đặc tả** (hành vi đúng). Đây là "nguồn sự thật" để LLM viết assert —
  nếu không có đặc tả, LLM chỉ có thể viết test "chụp lại" hành vi hiện tại của code (kể cả khi code sai).
- Cài **2 bug** (xem `BUGS.md`), **không comment trong code**: lỗi biên ở `letter_grade(80)` và lỗi
  không xoá sản phẩm khi số lượng về 0 ở `ShoppingCart.remove_item`.
- Tạo bản đã sửa ở `evaluation/fixed_targets/` để GĐ7 chấm tự động "bộ test có phát hiện bug không".
- `tests/test_targets.py` kiểm tra các module import được và bug hoạt động đúng như mô tả.

### (b) Khái niệm quan trọng
- **Đặc tả (specification) vs cài đặt (implementation):** đặc tả nói code *nên* làm gì (docstring),
  cài đặt là code *thực sự* làm gì. Bug = chỗ hai thứ này khác nhau.
  Ví dụ: docstring nói `80 -> "B"`, code trả `"C"` → bug.
- **Oracle problem (bài toán "trọng tài"):** khi sinh test tự động, làm sao biết *kết quả đúng* là gì để viết
  `assert`? Nếu LLM nhìn code rồi viết `assert letter_grade(80) == "C"` thì test PASS nhưng lại
  "hợp thức hoá" bug. Vì vậy prompt sẽ yêu cầu LLM viết assert theo **docstring**, không theo code.
- **Line coverage vs branch coverage:**
  ```python
  def f(x):
      if x > 0:      # 1 dòng, 2 nhánh (True/False)
          x = -x
      return x
  ```
  Test `f(5)` chạy **mọi dòng** (line coverage 100%) nhưng chỉ đi nhánh True → branch coverage 50%.
  Cần thêm `f(-1)` để phủ nhánh False.
- **Code chết (dead code):** dòng không bao giờ chạy được. Bug 2 tạo ra code chết (`del self.items[name]`),
  nên coverage tối đa của `shopping_cart.py` < 100% — một "manh mối" có thể dẫn tới bug.

### (c) File liên quan
`targets/*.py`, `BUGS.md`, `evaluation/fixed_targets/`, `tests/test_targets.py`

### (d) Lệnh tự chạy thử
```bash
pytest -v tests/test_targets.py
python -c "import sys; sys.path.insert(0,'targets'); import grading; print(grading.letter_grade(80))"
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Vì sao không comment vị trí bug trong code?** → LLM đọc toàn bộ code; nếu có comment "BUG ở đây" thì
   việc "phát hiện" là giả. Bug chỉ được ghi trong `BUGS.md`, file này không bao giờ đưa vào prompt.
2. **Coverage 100% có đảm bảo không còn bug không?** → Không. Bug 1 là ví dụ: test `letter_grade(85)` phủ
   nhánh `"B"` nhưng không lộ bug. Cần test đúng giá trị biên (80). Đây là lý do dự án dùng thêm mutation testing.
3. **Vì sao chọn module có độ khó tăng dần?** → Để thấy agent xử lý thế nào khi code có nhiều nhánh, ngoại lệ,
   và trạng thái; kết quả thực nghiệm có thể so sánh theo độ khó.

---

## GĐ2 — Baseline: sinh test một lần

### (a) Đã làm gì và tại sao
- `testgen/config.py`: đọc `.env` → đối tượng `Settings` (provider, model, key, base_url...).
- `testgen/llm_client.py`: lớp `LLMClient` với **một hàm duy nhất `chat(system, user, task)`**. Bên trong
  chọn cách gọi theo nhà cung cấp:
  - **OpenRouter, DeepSeek, OpenAI** dùng chung giao thức OpenAI → chỉ khác `base_url` + key (1 hàm).
  - **Anthropic** dùng SDK `anthropic`; **Ollama** gọi HTTP `POST /api/chat`.
  - **mock**: LLM giả lập, trả lời theo kịch bản → dùng cho unit test, chạy offline, không tốn tiền.
  - Có **retry** (thử lại 3 lần, chờ 2s, 4s...) cho lỗi mạng/quá tải; **không** thử lại với lỗi 401/402/404
    (sai key, hết tiền, sai model) vì thử lại vô ích.
  - Ghi lại mỗi lần gọi (`history`): thời gian, token, chi phí → dùng làm chỉ số thực nghiệm.
- `testgen/prompts.py`: toàn bộ prompt ở một chỗ. Prompt hệ thống yêu cầu **assert theo docstring**.
- `testgen/code_utils.py`: tách code khỏi câu trả lời LLM (```python```), ghép/thay/xoá hàm test bằng `ast`,
  gắn nhãn `SUSPECTED_BUG` (dùng ở GĐ4).
- `testgen/generator.py`: **baseline** = gọi LLM **một lần**, lưu `generated_tests/baseline/test_<module>.py`.
- `generated_tests/conftest.py`: để chạy trực tiếp test sinh ra bằng `pytest generated_tests/...`.
- Test của công cụ: `tests/test_code_utils.py`, `tests/test_llm_client.py` (dùng mock, không tốn API).

**Sự cố thực tế & cách xử lý (ghi trung thực):** key OpenRouter được cung cấp gần như **hết credit** (lỗi 402
khi gọi `z-ai/glm-5.2`). Các model miễn phí (`:free`) bị giới hạn **50 request/ngày** và đôi khi bị 429
(quá tải). Model miễn phí chạy được: `nvidia/nemotron-3-super-120b-a12b:free` (~20 s/lần gọi) → đặt trong `.env`.
Hệ quả: thực nghiệm GĐ7 phải chạy quy mô nhỏ hoặc cần nạp credit / dùng key DeepSeek.

**Kết quả thử thật:** baseline cho `grading.py` sinh 143 dòng test; chạy thì 1 test fail ở
`assert grading.letter_grade(80) == "B"` → chính là **bug 1**. Nhưng baseline **không phân biệt** được
"test sai" hay "code sai" — nó chỉ đưa ra một file test, fail thì người dùng tự xem. Đó là việc của agent (GĐ4).

### (b) Khái niệm quan trọng
- **System prompt vs user prompt:** system = "vai trò + luật chơi" cố định (bạn là kỹ sư test, assert theo
  docstring...); user = dữ liệu cụ thể của lần gọi (mã nguồn module).
- **Retry với exponential backoff:** lỗi tạm thời (mạng, 429 quá tải) thường tự hết sau vài giây. Chờ 2s, rồi 4s,
  rồi 8s... để không "dội" server. Ví dụ: lần 1 lỗi 429 → chờ 2s → lần 2 thành công.
- **Adapter pattern (mẫu thiết kế):** phần còn lại của chương trình chỉ biết `client.chat(...)`, không cần biết
  bên dưới là OpenRouter hay Ollama → đổi nhà cung cấp không phải sửa agent.
- **Vì sao parse bằng `ast` thay vì regex?** `ast.parse(code)` cho biết chính xác hàm `test_b` bắt đầu/kết thúc
  ở dòng nào (kể cả decorator), không bị nhầm bởi chuỗi hay comment chứa chữ `def test_`.
- **Baseline (mốc so sánh):** muốn chứng minh vòng lặp tự cải tiến có ích, phải so với cách đơn giản nhất
  (sinh một lần). Không có baseline thì không biết cải thiện bao nhiêu.

### (c) File liên quan
`testgen/config.py`, `testgen/llm_client.py`, `testgen/prompts.py`, `testgen/code_utils.py`,
`testgen/generator.py`, `tests/test_code_utils.py`, `tests/test_llm_client.py`, `generated_tests/baseline/`

### (d) Lệnh tự chạy thử
```bash
pytest                                                   # test của công cụ (mock, không tốn API)
python -m testgen.generator targets/grading.py           # sinh test baseline (gọi LLM thật, 1 request)
pytest generated_tests/baseline/test_grading.py          # chạy test vừa sinh
# đổi nhà cung cấp: sửa LLM_PROVIDER / LLM_MODEL trong .env, ví dụ LLM_PROVIDER=deepseek
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Làm sao đổi sang nhà cung cấp LLM khác?** → Sửa `LLM_PROVIDER`, `LLM_MODEL`, key trong `.env`. Code agent
   chỉ gọi `client.chat()`; nếu là nhà cung cấp mới hoàn toàn thì thêm một hàm `_call_xxx` trong `llm_client.py`.
2. **Retry có nguy hiểm không (tốn tiền gấp 3)?** → Chỉ retry lỗi *tạm thời*; lỗi xác định (sai key, hết tiền)
   báo ngay. Mỗi lần gọi được ghi lại nên số lần gọi thật được thống kê chính xác.
3. **Mock LLM dùng để làm gì, có dùng để lấy kết quả không?** → Chỉ để kiểm thử pipeline (vòng lặp, ghép code,
   runner) một cách lặp lại được và miễn phí. Tuyệt đối không dùng làm kết quả thực nghiệm.

---

## GĐ3 — Runner: chạy test & đo coverage

### (a) Đã làm gì và tại sao
`testgen/runner.py` có hàm `run_tests(module_path, test_code, timeout)` trả về dataclass `RunResult`:
số test pass/fail/error/xfail, thông báo lỗi từng test, **line coverage**, **branch coverage**, danh sách
**dòng chưa chạy** và **nhánh chưa đi**, lỗi thu thập (syntax/import), có bị timeout không.

Cách làm:
1. Kiểm tra cú pháp bằng `ast.parse` trước — sai cú pháp thì báo ngay, không cần chạy pytest.
2. Tạo **thư mục tạm** chỉ chứa `<module>.py` + `test_<module>.py`.
3. Chạy `python -m pytest ... --junitxml=report.xml --cov=<module> --cov-branch --cov-report=json:cov.json`
   bằng `subprocess.run(..., timeout=60)`.
4. Đọc **file máy đọc được** (XML của pytest, JSON của coverage) thay vì "đọc chữ" trên màn hình → chắc chắn,
   không phụ thuộc định dạng in ra.
5. Dựa vào **mã thoát** của pytest: 0 pass hết, 1 có fail, 2 lỗi thu thập, 5 không có test.

`describe_missing()` đổi danh sách số dòng thành câu mô tả kèm code, ví dụ
`- Nhánh từ dòng 2 (if x > 0:) sang dòng 4 (if x < 0:) chưa được đi qua` → đưa vào prompt ở GĐ4.

Thử với test baseline của `grading.py`: 17 pass, 1 fail (bug 1), line 100%, branch 100%, ~0.8 giây.

### (b) Khái niệm quan trọng
- **Subprocess + timeout (cô lập):** test do LLM viết có thể chứa `while True`. Nếu chạy chung tiến trình, chương
  trình treo luôn. Chạy tiến trình con thì sau 60 giây ta "giết" nó và báo lỗi timeout.
- **coverage.py đo thế nào?** Nó gắn "hàm theo dõi" (trace function) vào trình thông dịch Python; mỗi khi một dòng
  được thực thi, nó ghi lại. Với `--cov-branch`, nó ghi thêm các **cặp (dòng nguồn → dòng đích)** đã đi qua.
  Ví dụ `[2, 4]` trong `missing_branches` = "chưa có lần nào từ dòng 2 nhảy sang dòng 4" (tức điều kiện ở dòng 2
  chưa bao giờ False). Số âm như `[5, -1]` = nhánh "thoát khỏi hàm".
- **JUnit XML:** định dạng báo cáo test chuẩn công nghiệp (Jenkins, GitLab CI đều đọc được). Mỗi `<testcase>` có
  thể chứa `<failure>`, `<error>`, `<skipped>`.
- **failed vs error trong pytest:** *failed* = assert sai; *error* = lỗi ngoài assert, ví dụ fixture hỏng.
- **Tại sao coverage vẫn đo khi test fail?** Coverage chỉ đo "dòng nào đã chạy", không quan tâm assert đúng hay sai.

### (c) File liên quan
`testgen/runner.py`, `tests/test_runner.py`

### (d) Lệnh tự chạy thử
```bash
python -m testgen.runner targets/grading.py generated_tests/baseline/test_grading.py
pytest tests/test_runner.py -v
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Vì sao không import và chạy test trực tiếp trong chương trình?** → Không cô lập được: test lỗi/treo/sửa trạng
   thái toàn cục sẽ phá chương trình chính; coverage cũng bị lẫn. Subprocess + thư mục tạm cho kết quả sạch.
2. **Line coverage và branch coverage khác nhau thế nào? Chỉ số nào quan trọng hơn?** → Branch mạnh hơn: 100% branch
   kéo theo 100% line (với code thông thường) nhưng ngược lại thì không (`if` không có `else`). Agent dùng cả hai.
3. **Làm sao runner biết test lỗi import hay test sai?** → Mã thoát 2 + lỗi trong phase thu thập ⇒ lỗi import/syntax
   (cả file hỏng); mã thoát 1 + `<failure>` trong XML ⇒ từng test sai. Hai loại được agent xử lý khác nhau.
