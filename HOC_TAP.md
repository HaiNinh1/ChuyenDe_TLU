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

---

## GĐ4 — Vòng lặp tự cải tiến (`agent.py`) — PHẦN CỐT LÕI

### (a) Đã làm gì và tại sao
`testgen/agent.py`, lớp `TestGenAgent`, hàm `run()` là **một vòng `for` + các `if/else`** (không framework):

```
code = LLM sinh test ban đầu
for vòng in 0..max_iterations:
    kết_quả = runner.run_tests(code)            # đo
    ghi log vòng này
    if file test hỏng (syntax/import):  code = LLM sửa cả file
    elif có test fail:                  LLM phân loại -> TEST_WRONG: sửa | SUSPECTED_BUG: giữ + gắn nhãn
    elif coverage < ngưỡng và còn tăng: code += LLM viết thêm test cho dòng/nhánh chưa phủ
    else: DỪNG
```

Các quyết định thiết kế quan trọng:
1. **Thứ tự ưu tiên:** sửa file hỏng → xử lý test fail → tăng coverage. Không tăng coverage khi bộ test còn "đỏ".
2. **LLM chỉ trả về hàm mới/hàm đã sửa; chương trình tự ghép** (`code_utils.merge_tests`). Nhờ vậy LLM không thể
   vô tình xoá test cũ hoặc gỡ nhãn SUSPECTED_BUG.
3. **Xử lý oracle problem:** khi test fail, LLM được hỏi *"test viết sai hay code có bug?"* (trả về JSON).
   - `TEST_WRONG` → sửa đúng hàm đó (tối đa `max_fix_attempts` lần, quá thì xoá test).
   - `SUSPECTED_BUG` → **giữ nguyên test**, gắn `@pytest.mark.xfail(reason="SUSPECTED_BUG: ...")`.
     Bộ test vẫn "xanh" để vòng lặp đi tiếp, nhưng test được giữ lại làm bằng chứng cho con người xem.
4. **Điều kiện dừng:** đạt ngưỡng (mặc định line 95%, branch 90%), **không cải thiện** sau `patience=2` lần thử,
   hết `max_iterations`, hoặc lỗi LLM (dừng êm, giữ bộ test tốt nhất). Có **quay lui** về phiên bản chạy được
   gần nhất nếu file test hỏng mãi không sửa được.
5. **Log JSON từng vòng** (`logs/<module>_<cấu hình>_<thời gian>.json`): code test, số pass/fail, coverage,
   dòng chưa phủ, phân loại của LLM, số lần gọi LLM... → dùng để phân tích và **REPLAY** trên giao diện.
6. Sơ đồ luồng: `docs/agent_flow.md` (mermaid).

**Kết quả chạy thật** (`shopping_cart.py`, model nemotron miễn phí): vòng 0 có 1 test fail → LLM phân loại
**SUSPECTED_BUG** với lý do *"docstring nói số lượng về 0 thì xoá sản phẩm, nhưng code chỉ xoá khi < 0"* → đúng
**bug 2**. Test được giữ nguyên (`assert "apple" not in cart.items`) và gắn nhãn. Vòng 1: line 97.7%, branch 95%
→ đạt ngưỡng, dừng. Tổng 2 lần gọi LLM, ~55 giây. (Một lần chạy, chưa phải thống kê — xem GĐ7.)

### (b) Khái niệm quan trọng
- **Agent (tác tử) theo nghĩa của đồ án:** chương trình lặp *quan sát → quyết định → hành động*. Quan sát = kết quả
  runner; quyết định = các `if` trong `_step()`; hành động = gọi LLM với prompt phù hợp. "Tự cải tiến" = kết quả
  đo được dùng làm đầu vào cho lần sinh tiếp theo (vòng phản hồi, feedback loop).
- **Oracle problem:** test fail có 2 khả năng: test sai hoặc code sai. Nếu agent cứ "sửa test cho pass" thì sẽ
  hợp thức hoá bug (test `assert letter_grade(80) == "C"`). Ví dụ trong đồ án: test biên của `remove_item`
  fail → LLM đọc docstring → kết luận code sai → giữ test.
- **xfail trong pytest:** "dự kiến fail". Test xfail mà fail → báo `x` (không tính lỗi); nếu sau này sửa bug và test
  pass → báo `X` (XPASS). Dùng `strict=False` để test tham số hoá không bị tính lỗi khi một số trường hợp pass.
- **Early stopping (dừng sớm) với patience:** giống khi train mô hình học máy: chỉ số không tăng sau `patience`
  lần thì dừng để tiết kiệm lần gọi LLM (= tiền + thời gian).

### (c) File liên quan
`testgen/agent.py` (đọc `run()` và `_step()` trước), `testgen/code_utils.py` (`merge_tests`, `add_suspected_marker`),
`docs/agent_flow.md`, `tests/test_agent.py` (kịch bản mock đi qua đủ các nhánh), `logs/*.json`

### (d) Lệnh tự chạy thử
```bash
python -m testgen.agent targets/shopping_cart.py --max-iters 6
python -m testgen.agent targets/grading.py --line 100 --branch 100      # ngưỡng khắt khe hơn -> nhiều vòng hơn
pytest tests/test_agent.py -v                                          # kiểm tra vòng lặp bằng LLM giả lập
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Nếu LLM phân loại sai (test sai mà bảo là bug) thì sao?** → Đó là hạn chế có thật: agent có thể giữ lại một
   test sai và gắn nhãn nghi bug (false positive). Vì vậy nhãn chỉ là *"nghi ngờ"*, cần người kiểm tra. GĐ7 đo tỉ lệ
   này bằng cách chạy lại test trên bản code đã sửa: test SUSPECTED_BUG pass trên bản sửa = nghi đúng.
2. **Vì sao không để LLM tự quyết định mọi thứ (ví dụ kiểu ReAct/tool-calling)?** → Luồng điều khiển cố định bằng
   code thì dễ hiểu, dễ kiểm thử (test bằng mock), dự đoán được chi phí; LLM chỉ làm phần nó giỏi: viết/sửa test,
   đọc hiểu docstring.
3. **Làm sao biết vòng lặp không chạy mãi?** → Ba chốt chặn: `max_iterations`, `patience` (không cải thiện thì dừng),
   giới hạn số lần sửa mỗi test (`max_fix_attempts`), cộng timeout cho mỗi lần chạy pytest.

---

## GĐ5 — Mutation testing

### (a) Đã làm gì và tại sao
- `testgen/mutation.py`:
  - `generate_mutants(source)`: dùng **toán tử đột biến của mutmut 2.5.1** (`list_mutations`, `mutate`) để sinh mọi
    mutant; bỏ các mutant chỉ đổi docstring (so sánh cây AST sau khi bỏ docstring).
  - `run_mutation_testing(module, tests, max_mutants=20, seed=0)`: kiểm tra bộ test pass trên code gốc → lấy mẫu
    tối đa `max_mutants` mutant (seed cố định) → mỗi mutant chạy pytest `-x` trong thư mục tạm riêng, **4 tiến trình
    song song** → tính mutation score.
  - `skip_failing=True`: khi ĐO để so sánh (GĐ7), bỏ qua các test đang fail trên code gốc.
- `agent.py`: thêm **phase mutation** chạy SAU phase coverage (khi coverage đạt ngưỡng hoặc không tăng nữa). Mutant còn
  sống (tối đa 6) được mô tả dạng `dòng 40: if value < low: -> if value <= low:` và gửi cho LLM viết test "giết" chúng.
  Dừng khi mutation score ≥ ngưỡng (mặc định 80%), không còn mutant sống, hoặc không cải thiện.
- Giới hạn phạm vi cho demo: chỉ đột biến **một module**, tối đa 20 mutant, mỗi mutant timeout 30 s → ~5-10 giây/lần.

**Vì sao không gọi thẳng lệnh `mutmut run`?** mutmut 3.x không chạy trên Windows; mutmut 2 CLI chạy được nhưng không
giới hạn số mutant, lưu cache SQLite riêng và in ra màn hình khó phân tích. Dùng thư viện sinh mutant của mutmut + runner
tự viết (~60 dòng) thì kiểm soát được hoàn toàn và vẫn dùng đúng bộ toán tử chuẩn.

**Kết quả chạy thật:**
- `grading.py` (agent + mutation): vòng 0 phát hiện **bug 1** (LLM phân loại SUSPECTED_BUG: *"docstring nói 80 → B
  nhưng code trả C vì dùng > 80"*), coverage 97.5/96.9%, mutation score 95% → dừng. 2 lần gọi LLM.
- `calculator.py` (ngưỡng mutation 100%): coverage 100% ngay từ đầu nhưng mutation 90.9% — 2 mutant còn sống đều
  ở **biên** của `clamp` (`value < low` → `value <= low`, `value > high` → `value >= high`). LLM viết thêm 2 test → **100%**.
  **Nhưng phải nhìn kỹ (trung thực):** hai mutant này *gần như tương đương* — khi `value == low`, bản gốc trả `value`,
  mutant trả `low`, mà hai số này bằng nhau! LLM đã "giết" chúng bằng một class tự chế và `assert result is value`
  (kiểm tra **danh tính object**) — một chi tiết cài đặt mà docstring **không hề quy định**. Test như vậy "giòn"
  (brittle): nếu ai đó viết lại `clamp` đúng đặc tả nhưng trả `low` thì test fail oan.
  → Bài học: **tối ưu mù quáng theo mutation score có thể sinh test bám vào chi tiết cài đặt** (overfitting).
  Đây là hạn chế cần nêu trong báo cáo; ngưỡng mặc định 80% (không phải 100%) một phần vì lý do này.
- Chạy `python -m testgen.mutation` trên test baseline của `grading.py`: mutant `elif score > 80` → `elif score >= 80`
  **sống sót** — mutant này thực chất là *bản sửa của bug 1*! (test bắt bug bị bỏ qua vì đang fail).

### (b) Khái niệm quan trọng
- **Mutant và "giết" mutant:** ví dụ `letter_grade` có `if score >= 90: return "A"`. Mutant đổi thành `score > 90`.
  Test `letter_grade(95) == "A"` pass với cả hai → mutant **sống**. Test `letter_grade(90) == "A"` pass với bản gốc
  nhưng FAIL với mutant (mutant trả "B") → mutant **bị giết**.
  Ý chính: test phải kiểm tra **đúng biên** và **đúng giá trị** thì mới giết được mutant.
- **Mutation score = mutant bị giết / tổng mutant.** Đo "độ nhạy" của bộ test: nếu code bị sửa sai một chút, bộ test
  có kêu không? Coverage chỉ đo "code có được chạy không".
- **Toán tử đột biến của mutmut:** đổi so sánh (`<` ↔ `<=`), số (`0` → `1`), toán tử (`+` → `-`), `and` ↔ `or`,
  chuỗi (`"A"` → `"XXAXX"`), giá trị mặc định tham số, `break` ↔ `continue`...
- **Mutant tương đương (equivalent mutant):** thay đổi cú pháp nhưng không đổi hành vi → không test nào giết được.
  Không thể tự động phát hiện hoàn toàn (bài toán không quyết định được) → mutation score 100% không phải lúc nào cũng
  đạt được; prompt cho phép LLM bỏ qua mutant tương đương.
- **Lấy mẫu với seed cố định:** 77 mutant × ~1 s là quá lâu cho demo → lấy 20 mutant ngẫu nhiên, nhưng `seed=0` để mọi
  cấu hình được chấm trên **cùng một tập** mutant (so sánh công bằng).

### (c) File liên quan
`testgen/mutation.py`, `testgen/agent.py` (`_mutation_step`), `testgen/prompts.py` (`mutation_prompt`),
`tests/test_mutation.py`

### (d) Lệnh tự chạy thử
```bash
python -m testgen.mutation targets/grading.py generated_tests/baseline/test_grading.py
python -m testgen.agent targets/calculator.py --mutation --max-mutants 30
pytest tests/test_mutation.py -v
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Coverage 100% rồi thì cần mutation testing làm gì?** → Ví dụ `calculator.clamp`: coverage 100% nhưng 2 mutant biên
   sống sót, tức nếu lập trình viên lỡ viết `<=` thay `<` thì bộ test không phát hiện. Mutation đo *chất lượng assert*,
   coverage chỉ đo *code có chạy qua không*.
2. **Mutation testing rất chậm, em giải quyết thế nào?** → Chỉ đột biến module đang test, lấy mẫu tối đa N mutant,
   chạy song song 4 tiến trình, pytest `-x` dừng ngay khi có test fail, timeout mỗi mutant. Đánh đổi: điểm là ước lượng
   trên mẫu, không phải toàn bộ mutant.
3. **Mutation score 100% có phải luôn tốt?** → Không hẳn. Ví dụ `clamp`: để đạt 100%, LLM viết test kiểm tra
   `result is value` — chi tiết cài đặt ngoài đặc tả. Có những mutant (gần) tương đương mà muốn giết phải "bám" vào
   cách cài đặt. Nên đặt ngưỡng hợp lý (80%) và người review cần xem các test sinh ra ở phase mutation.
4. **Vì sao chạy mutation SAU khi đạt coverage?** → Mutant ở dòng chưa được test chạy tới chắc chắn sống sót — gửi cho
   LLM chỉ lặp lại việc tăng coverage mà tốn thêm thời gian. Tăng coverage trước (rẻ), rồi mới "mài" chất lượng assert.
