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

---

## GĐ6 — Bộ nhớ "tự học" (`memory.py`)

### (a) Đã làm gì và tại sao
`testgen/memory.py`, lớp `Memory`, lưu trong **một file JSON** `memory/memory.json` (không dùng vector database):
1. **Bài học sửa lỗi** (`lessons`): mỗi lần nhờ LLM sửa lỗi, prompt yêu cầu thêm một dòng `LESSON: ...` (quy tắc chung).
   Bài học **chỉ được lưu khi vòng sau xác nhận lỗi đã hết** (`_confirm_lessons`) → không "học" điều sai.
   Bài học gần trùng (cùng loại lỗi, >60% từ giống nhau) chỉ tăng bộ đếm `times_seen`.
2. **Mẫu test tốt** (`good_tests`): test mới làm **tăng coverage** hoặc **giết được mutant** (đo ở vòng sau) được lưu
   lại (≤ 25 dòng, tối đa 30 mẫu).
3. **Truy xuất:** `module_tags()` phân tích AST để gắn nhãn module (`class`, `state`, `exception`, `branches`,
   `compound_condition`, `string`, `float`, `dict`, `loop`). Chọn bài học có điểm cao nhất:
   `điểm = số nhãn trùng + 3 (nếu cùng loại lỗi đang gặp) + 0.1 × số lần gặp`. Mẫu test chỉ lấy từ **module khác**.
4. **Dùng ở đâu:** prompt sinh ban đầu (bài học + 2 mẫu test) và prompt sửa lỗi (bài học cùng loại lỗi).
5. Bật bằng `AgentConfig(use_memory=True)` hoặc `python -m testgen.agent ... --memory`.

### (b) "Học" ở đây theo nghĩa nào? (quan trọng — nói rõ khi thuyết trình)
- **KHÔNG phải học máy theo nghĩa huấn luyện:** trọng số LLM **không thay đổi**. Không fine-tune, không gradient.
- Đây là **học trong ngữ cảnh (in-context learning) + bộ nhớ kinh nghiệm (episodic memory)**: kinh nghiệm cũ được
  *lưu ra ngoài* rồi *đưa lại vào prompt*. Giống sinh viên ghi sổ tay "lỗi hay mắc" rồi đọc lại trước khi làm bài —
  bộ não không đổi, nhưng có thêm ghi chú.
- Ví dụ: lần 1 LLM viết `from grading import calc_grade` (tên không tồn tại) → ImportError → sửa thành công, LESSON:
  *"Chỉ import những tên thực sự có trong module"*. Lần 2 với module khác, câu này nằm sẵn trong prompt.

**Giới hạn (trung thực):**
1. Tìm kiếm theo **nhãn + từ khoá**, không hiểu ngữ nghĩa → có thể chọn bài học không liên quan hoặc bỏ sót.
2. Bài học do chính LLM viết → có thể chung chung ("hãy viết test cẩn thận") hoặc sai; chỉ lọc bằng điều kiện
   "lỗi đã hết ở vòng sau", không kiểm chứng được bài học có *đúng lý do* hay không.
3. Với model mạnh, lỗi ít xảy ra → **ít bài học** → tác dụng nhỏ. Hiệu quả thật phải đo ở GĐ7 (cấu hình D vs C).
4. Prompt dài thêm → tốn token; bộ nhớ có giới hạn kích thước và xoá bài ít dùng nhất.
5. Không có cơ chế "quên" bài học sai ngoài giới hạn kích thước.

### (c) File liên quan
`testgen/memory.py`, `testgen/agent.py` (các hàm `_lessons_for_initial`, `_remember_fix`, `_confirm_lessons`,
`_confirm_good_tests`), `testgen/prompts.py` (`_lessons_block`, yêu cầu `LESSON:`), `tests/test_memory.py`,
`memory/memory.json` (sinh ra khi chạy)

### (d) Lệnh tự chạy thử
```bash
pytest tests/test_memory.py -v
python -m testgen.agent targets/safe_parser.py --memory
python -m testgen.agent targets/text_utils.py --memory     # xem mục lessons_used trong log JSON
python -c "import json; print(json.dumps(json.load(open('memory/memory.json', encoding='utf-8')), ensure_ascii=False, indent=2))"
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Hệ thống có thực sự "tự học" không?** → Có theo nghĩa *tích luỹ kinh nghiệm và dùng lại qua prompt*
   (in-context learning); không theo nghĩa cập nhật trọng số mô hình. Em nói rõ giới hạn này.
2. **Vì sao không dùng vector database / embedding?** → Quy mô nhỏ (vài chục bài học), yêu cầu đề bài đơn giản dễ hiểu;
   nhãn AST + khớp loại lỗi là đủ và giải thích được. Hướng phát triển: embedding để tìm theo ngữ nghĩa.
3. **Làm sao tránh học điều sai?** → Chỉ lưu bài học khi lần chạy sau xác nhận lỗi đã hết; mẫu test chỉ lưu khi chỉ số
   (coverage/mutation) thực sự tăng. Vẫn còn rủi ro (bài học đúng kết quả nhưng sai lý do) — là hạn chế.

---

## GĐ7 — Thực nghiệm (`evaluate.py`)

### (a) Đã làm gì và tại sao
So sánh 4 cấu hình trên 5 module: **A** baseline · **B** agent + coverage · **C** B + mutation · **D** C + bộ nhớ.
`evaluate.py` tách **2 bước**:
1. **SINH** (gọi LLM): chạy agent cấu hình C và D, mỗi lần lưu một log `logs/<module>_eval_C|D_<thời gian>.json`.
   - **Thiết kế ghép cặp:** A = bộ test ban đầu của lần chạy C (cùng prompt, cùng *một* lần gọi); B = trạng thái của C
     đúng lúc phase coverage kết thúc (agent B sẽ dừng đúng ở đó). Agent lưu các mốc này (`snapshots`) → **một lần chạy
     C cho ra A, B, C** → tiết kiệm ~50% request, và so sánh trên *cùng* chuỗi trả lời của LLM (giảm nhiễu).
   - D chạy riêng; bộ nhớ **rỗng ở đầu mỗi lần lặp**, các module chạy lần lượt để bộ nhớ tích luỹ.
   - Lần chạy bị dừng do lỗi LLM **không được tính**; chạy lại lệnh sẽ chỉ chạy phần còn thiếu (qua nhiều ngày được).
2. **CHẤM** (không gọi LLM): đọc log, chấm lại **mọi** cấu hình bằng cùng một thước đo:
   - line/branch coverage; số test fail;
   - **mutation score held-out**: loại khỏi tập chấm mọi mutant đã được đưa vào prompt của C/D → không bị thổi phồng
     (cột `mutation_all` = trên mọi mutant, để thấy mức chênh);
   - **phát hiện bug**: có test fail/xfail trên code lỗi **và** pass trên bản đã sửa;
     **gắn nhãn đúng**: có test SUSPECTED_BUG pass trên bản đã sửa (TP), ngược lại là FP.

   Xuất `results/runs.csv`, `results/results.csv`, `results/results_by_module.csv`, `results/summary.png`,
   `results/mutation_by_module.png`.

**Chuyện có thật khi làm (bài học quan trọng):** phiên bản đầu của `evaluate.py` chấm mutation trên tập mutant *chứa*
chính các mutant đã đưa cho LLM "giết" (cùng seed → cùng mẫu). Một **reviewer độc lập** (agent review code) phát hiện
lỗi này. Sau khi sửa (chấm trên mutant held-out), kết luận **đổi hẳn** — xem kết quả bên dưới. Đây là lỗi kinh điển
"đánh giá trên dữ liệu huấn luyện" (data leakage) giống trong học máy. Reviewer cũng tìm ra vài lỗi khác đã được sửa
(ghép code đổi tên nhầm fixture, mất nhãn SUSPECTED khi LLM trả lại test thiếu decorator, không quay lui khi file test
cuối bị hỏng, đọc JSON sai khi có dấu `{` thừa). Em đã kiểm tra log lượt 1: các lỗi này **không xảy ra** trong lượt đó,
nên log vẫn hợp lệ và chỉ cần chấm lại.

### Kết quả (lượt 1: 5 module × 1 lần, model `nvidia/nemotron-3-super-120b-a12b:free` qua OpenRouter)

| Cấu hình | Line % | Branch % | Mutation held-out % | Mutation mọi mutant % | Test fail còn lại | Bug có test fail | Bug được gắn nhãn đúng | Nhãn sai (FP) | Gọi LLM TB | Thời gian TB (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| A Baseline | 99.0 | 98.4 | 89.1 | 80.7 | 1.2 / module | 2/2 | 0/2 | 0 | 1.0 | 22 |
| B + coverage | 99.0 | 98.4 | 91.8 | 83.0 | 0 | 2/2 | **2/2** | 0 | 2.4 | 41 |
| C + mutation | 99.0 | 98.4 | 91.8 | 86.0 | 0 | 2/2 | **2/2** | 0 | 2.6 | 51 |
| D + memory | 99.0 | 98.4 | 91.8 | 88.1 | 0 | 2/2 | **2/2** | 0 | 3.2 | 122 |

**Đọc kết quả một cách trung thực:**
1. **Coverage gần như bão hoà ngay từ lần sinh đầu** (99% / 98%) với model này và các module nhỏ → phản hồi coverage
   hầu như không có gì để cải thiện. Phần chưa phủ ở `grading`/`shopping_cart` là dòng *code chết* do bug.
2. **Giá trị thật của vòng lặp là xử lý test fail:** baseline để lại trung bình 1.2 test fail/module *không phân loại*
   (người dùng không biết test sai hay code sai). B/C/D đưa về **0 test fail**, sửa các test viết sai, và **gắn nhãn
   đúng cả 2 bug** (3 test SUSPECTED_BUG, cả 3 đều pass trên bản đã sửa → **0 nhãn sai** trong lượt này).
3. **Mutation feedback (C so với B):** trên mutant **LLM chưa thấy** thì **không tăng** (91.8 = 91.8); chỉ tăng trên *mọi*
   mutant (83.0 → 86.0), tức phần tăng chủ yếu nằm ở **chính các mutant đã đưa cho LLM**. Với dữ liệu hiện có, em
   **không** kết luận được mutation feedback giúp test "chặt" hơn một cách tổng quát.
4. **Bộ nhớ (D so với C):** không khác biệt trên held-out; tốn thêm gọi LLM/thời gian (một phần do ngẫu nhiên: D ở
   `safe_parser` chạy 4 vòng kill_mutants). Với 1 lần chạy, không thể tách tác dụng bộ nhớ khỏi độ ngẫu nhiên của LLM.
5. **Chi phí:** số lần gọi LLM tăng từ 1 (A) lên 2.4–3.2; thời gian tăng 2–5 lần. Chi phí tiền = 0 (model miễn phí).

**Hạn chế của thực nghiệm (bắt buộc nêu khi báo cáo):**
- Mới **1 lần chạy** (đề bài yêu cầu 3): model miễn phí chỉ cho **50 request/ngày**, một lượt đầy đủ tốn ~30 request.
  Hai lượt còn lại chạy tiếp bằng `python evaluate.py --runs 3` ở các ngày sau (lệnh tự chạy phần còn thiếu).
- 5 module nhỏ tự viết, 2 bug tự cài, 1 model → **không có ý nghĩa thống kê**, chỉ là quan sát ban đầu.
- Tập held-out đã bỏ đi các mutant "khó" (những mutant sống sót mới được đưa cho LLM) → điểm held-out của **mọi** cấu
  hình đều cao hơn điểm trên mọi mutant; so sánh *giữa các cấu hình* vẫn công bằng vì dùng chung một tập.
- Mutation score là ước lượng trên tối đa 40 mutant lấy mẫu (seed cố định).

### (b) Khái niệm quan trọng
- **Nhóm đối chứng / baseline:** muốn nói "vòng lặp có ích" phải so với cách đơn giản nhất (A).
- **Ablation study (thí nghiệm bỏ bớt thành phần):** B → C → D mỗi bước thêm đúng một thành phần, để biết thành phần nào
  đóng góp gì.
- **Rò rỉ dữ liệu đánh giá (data leakage):** chấm trên chính những mutant đã "mớm" cho LLM giống cho học sinh làm bài
  kiểm tra trùng bài tập về nhà. Cách chữa: tách **held-out** (tập LLM chưa thấy).
- **Thiết kế ghép cặp (paired design):** so sánh các cấu hình trên cùng một "đối tượng" (cùng lần sinh đầu) → giảm nhiễu.
- **Precision của nhãn nghi bug:** TP / (TP + FP). Lượt này 3/3 — nhưng mẫu quá nhỏ để tin tưởng tuyệt đối.

### (c) File liên quan
`evaluate.py` (đọc `generate`, `measure`, `measure_all`), `testgen/agent.py` (`_snapshot`, `shown_mutant_ids`),
`testgen/mutation.py` (`exclude_ids`), `results/*.csv`, `results/*.png`, `logs/*_eval_*.json`, `tests/test_evaluate.py`

### (d) Lệnh tự chạy thử
```bash
python evaluate.py --measure-only       # không tốn API: chấm lại từ log có sẵn, vẽ lại biểu đồ
python evaluate.py --quick              # tốn ~6 request: 1 module grading
python evaluate.py --runs 3             # chạy tiếp lượt 2, 3 (~30 request/lượt) — nên chạy vào các ngày khác nhau
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Coverage của baseline đã 99%, vậy agent có ích gì?** → Với model này và module nhỏ, coverage không phải điểm khác
   biệt. Khác biệt nằm ở **test fail**: baseline để lại test fail không phân loại; agent phân loại, sửa test sai và gắn
   nhãn đúng 2/2 bug, 0 nhãn sai. Với module lớn/phức tạp hơn, phần coverage có thể quan trọng hơn — chưa kiểm chứng.
2. **Vì sao mutation score held-out của C không cao hơn B?** → Test do LLM viết để giết mutant cụ thể thường chỉ nhắm
   đúng mutant đó (đúng biên đó), không làm các assert khác chặt hơn. Ngoài ra cỡ mẫu nhỏ. Em báo cáo đúng như đo được,
   kèm cả số trên mọi mutant để thấy sự khác nhau.
3. **Tại sao chỉ chạy 1 lần thay vì 3?** → Giới hạn 50 request/ngày của model miễn phí; công cụ đã hỗ trợ chạy tiếp
   (`--runs 3`). Em ghi rõ đây là hạn chế và kết luận chỉ mang tính quan sát.

---

## GĐ8 — Giao diện demo (`app.py`, Streamlit)

### (a) Đã làm gì và tại sao
- **Thanh bên:** chọn *Chạy mới* (module mẫu trong `targets/` hoặc **dán code Python** → lưu vào `workspace/user_code/`)
  hoặc *REPLAY từ log*; bật/tắt mutation, bộ nhớ; chỉnh số vòng, ngưỡng; chọn nhà cung cấp/model (có `mock`).
- **Tab Tiến trình:** agent gọi hàm callback `progress(kind, payload)` mỗi khi có thông báo hoặc xong một vòng → giao
  diện hiện ngay thẻ của vòng đó (pass/fail, coverage, mutation, hành động, phân loại của LLM, mutant còn sống, LESSON)
  và biểu đồ cập nhật trực tiếp.
- **Tab Biểu đồ:** matplotlib — line/branch coverage và mutation score qua các vòng + bảng số liệu.
- **Tab Code test:** kéo thanh chọn vòng để xem code ở từng vòng; test SUSPECTED_BUG **tô đỏ**; chế độ **diff** so với
  vòng trước; nút tải file test.
- **Tab Kết quả thực nghiệm:** bảng `results/*.csv` + ảnh biểu đồ.
- **REPLAY:** đọc log JSON và phát lại từng vòng (không gọi LLM, không cần mạng) — phương án dự phòng khi demo.
- Kiểm thử giao diện tự động bằng `streamlit.testing.AppTest` (`tests/test_app.py`) + kiểm tra bằng mắt qua trình duyệt
  (đã sửa: code bị mất thụt lề khi hiển thị bằng markdown → chuyển sang `st.html` với font monospace).

### (b) Khái niệm quan trọng
- **Mô hình chạy của Streamlit:** mỗi lần người dùng thao tác, **toàn bộ script chạy lại từ đầu**. Dữ liệu cần giữ giữa
  các lần (kết quả agent) phải cất trong `st.session_state`.
- **Callback:** agent không biết gì về giao diện; nó chỉ gọi `progress(...)`. Giao diện truyền vào một hàm vẽ ra màn hình.
  Nhờ vậy cùng một agent dùng được cho CLI, test, và Streamlit (tách lớp logic và lớp hiển thị).
- **Replay từ log:** vì mọi vòng đều được ghi đầy đủ (code, số liệu, lý do), có thể tái hiện lần chạy mà không cần LLM.

### (c) File liên quan
`app.py`, `tests/test_app.py`, `logs/*.json`

### (d) Lệnh tự chạy thử
```bash
streamlit run app.py
pytest tests/test_app.py -v
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Nếu lúc demo mất mạng thì sao?** → Chế độ REPLAY phát lại log JSON đã lưu, dữ liệu y hệt lần chạy thật.
2. **Làm sao giao diện cập nhật từng vòng khi agent đang chạy?** → Agent gọi callback sau mỗi vòng; callback ghi vào các
   "chỗ trống" (`st.empty`, `st.status`) nên Streamlit vẽ lại phần đó ngay, không cần chờ agent chạy xong.
3. **Người dùng dán code bất kỳ có an toàn không?** → Code và test chạy trong tiến trình con có timeout, trong thư mục tạm;
   nhưng **không** phải sandbox bảo mật (code vẫn chạy với quyền của máy). Chỉ dùng cho demo với code tin cậy.

---

## GĐ9 — Slide và tài liệu thuyết trình

### (a) Đã làm gì và tại sao
- `slides/slides.md` (**Marp**, 15 slide, ~12–15 phút): tiêu đề → vấn đề → hướng tiếp cận hiện có (EvoSuite/Pynguin,
  LLM một lần, LLM + phản hồi như CoverUp/MuTAP) → mục tiêu & phạm vi → kiến trúc → vòng lặp → coverage (ví dụ
  `pass_status`) → mutation (ví dụ `letter_grade(90)` giết mutant `> 90`) → bộ nhớ → thiết lập thực nghiệm → kết quả
  (bảng + biểu đồ `results/summary.png`) → demo → hạn chế & hướng phát triển → kết luận.
- `slides/speaker_notes.md`: lời thoại từng slide + **10 câu hỏi vấn đáp** kèm gợi ý trả lời.
- Đã render thử ra ảnh bằng Marp CLI để kiểm tra không slide nào tràn chữ (đã sửa slide kết quả bị tràn).
- Nguyên tắc: ít chữ, mỗi slide một ý; số liệu trên slide **khớp đúng** `results/results.csv`; nói rõ hạn chế.

### (b) Khái niệm quan trọng
- **Marp:** viết slide bằng Markdown, mỗi slide cách nhau bởi `---`. Xuất PDF/PPTX/HTML bằng extension
  "Marp for VS Code" hoặc lệnh `npx @marp-team/marp-cli`. Lợi ích: slide nằm trong git cùng code, dễ sửa số liệu.
- **Kể chuyện bằng số liệu trung thực:** trình bày cả kết quả "không như kỳ vọng" (mutation không cải thiện trên
  held-out) và cách mình phát hiện ra (review, tách tập held-out) — giảng viên đánh giá cao tư duy phản biện hơn là
  con số đẹp.

### (c) File liên quan
`slides/slides.md`, `slides/speaker_notes.md`, `results/summary.png`, `DEMO_CHECKLIST.md`

### (d) Lệnh tự chạy thử
```bash
npx @marp-team/marp-cli@latest --no-stdin slides/slides.md --allow-local-files -o slides/slides.html   # xem trên trình duyệt
npx @marp-team/marp-cli@latest --no-stdin slides/slides.md --allow-local-files --pdf -o slides/slides.pdf
```
(Hoặc mở `slides/slides.md` trong VS Code với extension "Marp for VS Code" → Export Slide Deck.)

### (e) Câu hỏi giảng viên có thể hỏi
Xem 10 câu hỏi trong `slides/speaker_notes.md`. Ba câu nên luyện kỹ nhất:
1. Oracle problem là gì và em giải quyết đến đâu?
2. Vì sao mutation feedback không cải thiện trên mutant held-out?
3. "Tự học" ở đây theo nghĩa nào?

---

## GĐ10 — Hoàn thiện & kiểm tra lại từ đầu

### (a) Đã làm gì và tại sao
- `README.md` đầy đủ (giới thiệu, cài đặt, bảng nhà cung cấp LLM, cách chạy từng phần, cách chạy demo, thứ tự đọc code).
- `DEMO_CHECKLIST.md`: chuẩn bị tối hôm trước, 5 phút trước demo, **kịch bản 5 phút** theo từng mốc thời gian, phương án
  dự phòng (REPLAY khi mất mạng/hết quota).
- **Chạy lại toàn bộ từ đầu trên bản clone sạch** (thư mục mới, `python -m venv`, `pip install -r requirements.txt`):
  1. `.env` **không** có trong repo (key không bị lộ) ✔
  2. `pytest` → **64/64 test pass** (mock, không tốn API) ✔
  3. LLM thật: `testgen.generator` → `testgen.runner` → `testgen.mutation` → `testgen.agent --mutation --memory` ✔
     (agent lại phát hiện bug 2 ở `shopping_cart`, sửa 2 test sai, học 1 bài học, mutation 85% → dừng)
  4. `evaluate.py --measure-only` tái lập **đúng y** `results/results.csv` đã commit ✔
  5. Giao diện: kiểm tra bằng `AppTest` (trong pytest) + mở trình duyệt thật, chụp màn hình các tab ✔
- Quét mã: không còn TODO/stub/test bị bỏ qua (chỉ 1 `pytest.skip` có điều kiện khi thư mục logs trống).

### (b) Khái niệm quan trọng
- **Tái lập (reproducibility):** người khác clone repo, cài theo README, chạy lệnh → ra đúng kết quả. Vì vậy log thô
  (`logs/*_eval_*.json`) được commit: bước CHẤM có thể chạy lại bất kỳ lúc nào mà không cần LLM.
- **Review độc lập:** người viết code dễ "mù" với lỗi của chính mình. Lượt review ở GĐ7 tìm ra lỗi đánh giá quan trọng
  nhất của cả dự án.

### (c) File liên quan
`README.md`, `DEMO_CHECKLIST.md`, `CLAUDE.md`

### (d) Lệnh tự chạy thử
```bash
pytest                              # 64 test, ~2 phút
python evaluate.py --measure-only   # tái lập bảng kết quả
streamlit run app.py                # demo
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Làm sao thầy/cô kiểm chứng kết quả của em?** → Log thô của từng lần chạy nằm trong `logs/`; lệnh
   `python evaluate.py --measure-only` chấm lại từ log và ra đúng bảng trong báo cáo.
2. **Em đã kiểm thử công cụ của mình thế nào?** → 64 test dùng LLM giả lập theo kịch bản (đi qua mọi nhánh của vòng lặp),
   test runner/mutation trên module thật, test giao diện bằng AppTest; cộng một lượt review code độc lập.

---

# TỔNG KẾT CUỐI CÙNG

## Đã làm được
- Agent hoàn chỉnh **sinh → chạy → đo → sửa/bổ sung**, tự viết bằng vòng `for` + `if/else` (không framework).
- Hỗ trợ 6 nhà cung cấp LLM qua `.env`: OpenRouter, DeepSeek, OpenAI, Anthropic, Ollama, mock.
- Runner cô lập (subprocess + timeout + thư mục tạm), đo line/branch coverage chính xác từ JSON.
- **Oracle problem:** phân loại TEST_WRONG / SUSPECTED_BUG; test nghi bug được giữ và gắn nhãn xfail.
  Kết quả thật: gắn nhãn đúng **cả 2 bug cài sẵn**, 0 nhãn sai (lượt 1).
- Mutation testing chạy được trên Windows (toán tử mutmut 2.5.1 + runner song song, giới hạn mutant).
- Bộ nhớ tự học (JSON) có cơ chế xác nhận trước khi lưu.
- Thực nghiệm A/B/C/D có thiết kế ghép cặp, **chấm held-out**, chạy tiếp được qua nhiều ngày, tái lập được.
- Giao diện Streamlit có REPLAY; slide Marp 15 trang + lời thoại + 10 câu hỏi; 64 test cho chính công cụ.

## Hạn chế (nói thẳng khi bảo vệ)
1. **Thực nghiệm mới 1 lượt** (đề yêu cầu 3) do model miễn phí giới hạn 50 request/ngày; key OpenRouter được cấp gần hết
   credit nên không dùng được `z-ai/glm-5.2`. → Chạy `python evaluate.py --runs 3` vào 2 ngày tiếp theo (~30 request/lượt),
   rồi cập nhật số liệu trên slide 10 và bảng GĐ7.
2. Coverage bão hoà ngay từ đầu với module nhỏ → chưa thấy rõ tác dụng của phản hồi coverage.
3. Mutation feedback **không** cải thiện trên mutant held-out; tối ưu mutation có thể sinh test bám chi tiết cài đặt.
4. Bộ nhớ chưa cho thấy tác dụng đo được; "học" chỉ là in-context learning.
5. Phụ thuộc docstring; LLM có thể phân loại sai; 5 module tự viết, 1 model → không tổng quát.
6. Chạy code người dùng dán vào **không** phải sandbox bảo mật.

## Thứ tự nên đọc code để hiểu dự án nhanh nhất
1. `targets/grading.py` + `BUGS.md` — hiểu "đề bài" và bug cài sẵn (5 phút)
2. `testgen/prompts.py` — LLM được yêu cầu những gì (10 phút)
3. `testgen/generator.py` — baseline, 20 dòng (3 phút)
4. `testgen/runner.py` — `run_tests()`, `parse_junit()`, `parse_coverage()` (15 phút)
5. **`testgen/agent.py` — `run()` rồi `_step()`**, sau đó `_handle_failures()` (oracle problem) (30 phút) ← quan trọng nhất
6. `testgen/code_utils.py` — `merge_tests()`, `add_suspected_marker()` (15 phút)
7. `testgen/mutation.py` — `generate_mutants()`, `run_mutation_testing()` (15 phút)
8. `testgen/memory.py` (10 phút)
9. `evaluate.py` — `generate()`, `measure()`, `shown_mutants()` (15 phút)
10. `app.py` — chỉ cần hiểu callback `on_progress` và chế độ REPLAY (10 phút)
11. `tests/test_agent.py` — kịch bản mock cho thấy toàn bộ vòng lặp trong ~60 dòng (đọc cùng lúc với bước 5 rất dễ hiểu)

---

# PHẦN 2 — REFACTOR ĐA NGÔN NGỮ (nhánh `multi-language`)

Đề tài mới: *"LLM Agent tự sinh unit test **đa ngôn ngữ** với vòng lặp tự cải tiến dựa trên phản hồi coverage và
mutation testing"*. Kiến trúc Adapter, hiện thực Python + JavaScript/TypeScript. Ưu tiên số một: **không làm hỏng
phần Python đang chạy tốt**.

## RF1 — Phân tích & chụp baseline trước refactor (chưa sửa code)

### (a) Đã làm gì và tại sao
- Tạo nhánh `multi-language` (nhánh `main` giữ nguyên bản chỉ-Python đã hoàn chỉnh, có thể quay về bất kỳ lúc nào).
- Đọc toàn bộ code, liệt kê **16 chỗ gắn chặt với Python** (gọi pytest, định dạng coverage.py, mutmut, `ast`,
  prompt nhắc pytest, đường dẫn `targets/<module>.py`...) → `docs/KE_HOACH_REFACTOR.md` (bảng + sơ đồ mermaid
  trước/sau + thứ tự làm + rủi ro).
- Viết `scripts/snapshot_python.py` để **chụp hành vi phần Python** thành `docs/baseline_truoc_refactor.json`:
  1. mã băm 8 prompt, 2. chạy lại bộ test trong log thực nghiệm (grading, shopping_cart) → pass/fail/coverage/dòng
  chưa phủ + trạng thái **từng mutant**, 3. agent với LLM giả lập theo kịch bản, 4. agent với LLM thật trên `grading`.
- Chạy script 2 lần liên tiếp: phần tất định (1-3) **giống hệt nhau** → dùng được làm mốc so sánh.
- Kết quả LLM thật trước refactor (`grading`, bật mutation): 3 lần gọi LLM, hành động `fix_tests → stop`,
  line 97,5% / branch 96,9%, mutation 95% (19/20), 2 test gắn nhãn nghi bug: `test_letter_grade_B` (đúng bug cài sẵn)
  và `test_final_score_rounding` (**nhãn sai** — LLM hiểu nhầm cách làm tròn số thực, docstring không quy định).
- Ghi nhận thêm: 64/64 test công cụ pass; mã băm `results/results.csv` để sau này kiểm tra `--measure-only` tái lập đúng.
- Sự cố trung thực: script bản đầu quên trả lại thư mục log sau phần giả lập nên **file log của lần chạy LLM thật bị
  mất** (số liệu tóm tắt vẫn được lưu). Đã sửa script.

### (b) Khái niệm quan trọng
- **Coupling (độ gắn kết):** module A "gắn chặt" với B khi A gọi thẳng chi tiết của B. Agent cũ gọi thẳng pytest,
  mutmut, `ast` → muốn thêm ngôn ngữ phải sửa vòng lặp ở hàng chục chỗ.
- **Regression test / "ảnh chụp" hành vi (snapshot/golden master):** trước khi sửa code cũ, ghi lại đầu ra của nó với
  đầu vào cố định; sau khi sửa, chạy lại và so sánh. Refactor = đổi cấu trúc **mà không đổi hành vi**, nên đầu ra phải
  giống hệt.
- **Phần tất định vs không tất định:** LLM cho kết quả khác nhau mỗi lần → không so "giống hệt" được. Vì vậy tách
  riêng: prompt, runner, mutation, agent + LLM giả lập (tất định, phải giống hệt) và agent + LLM thật (chỉ so tương đương).

### (c) File liên quan
`docs/KE_HOACH_REFACTOR.md`, `scripts/snapshot_python.py`, `docs/baseline_truoc_refactor.json`

### (d) Lệnh tự chạy thử
```bash
git branch                                   # đang ở multi-language
python scripts/snapshot_python.py --out docs/thu.json --compare docs/baseline_truoc_refactor.json   # không tốn API
python scripts/snapshot_python.py --out docs/thu.json --llm         # + 1 lần agent LLM thật (~3 request)
```

### (e) Câu hỏi giảng viên có thể hỏi
1. **Làm sao em chắc refactor không làm hỏng phần Python?** → Chụp hành vi trước refactor (prompt, kết quả chạy test,
   trạng thái từng mutant, agent với LLM giả lập) rồi so **giống hệt** sau mỗi bước; cộng 64 test của công cụ và tái lập
   đúng file kết quả thực nghiệm cũ.
2. **Sao không so luôn kết quả agent với LLM thật?** → LLM không tất định (cùng prompt có thể trả lời khác), nên chỉ so
   "tương đương": chạy đủ bước, chỉ số cùng mức. Phần có thể so chính xác thì so chính xác.
3. **Vì sao phải so cả mã băm prompt?** → Chỉ cần đổi một dấu cách/xuống dòng, LLM đã có thể cư xử khác; khi đó số liệu
   thực nghiệm cũ không còn so sánh công bằng với số liệu mới.

---

## RF2 — Lớp trừu tượng `LanguageAdapter` + registry

### (a) Đã làm gì và tại sao
- Tạo thư mục `adapters/`:
  - `base.py`: lớp trừu tượng **`LanguageAdapter`** (ABC) với các phương thức `check_environment()`,
    `test_file_path()`, `prompt_hints()`, `run_tests() -> TestResult`, `get_coverage() -> CoverageResult`,
    `run_mutation() -> MutationResult`, và nhóm thao tác sửa file test (`merge_tests`, `add_suspected_marker`,
    `remove_tests`, `suspected_tests`...). Agent sẽ chỉ gọi các phương thức này.
  - **Dataclass dùng chung** cho mọi ngôn ngữ: `TestResult` (chính là `RunResult` cũ, giữ tên cũ làm bí danh),
    `TestCaseResult`, `CoverageResult`, `Mutant`, `MutationResult` (thêm cờ `available` cho trường hợp công cụ mutation
    chưa cài), `EnvironmentStatus`.
  - `registry.py`: `adapter_for_file()` chọn adapter theo đuôi file; `detect_language()` đoán ngôn ngữ của code dán vào.
- `testgen/runner.py`, `testgen/mutation.py` **không định nghĩa dataclass nữa** mà import từ `adapters/base.py`
  (di chuyển, không viết lại). Hàm đếm điểm mutation chuyển thành `finish_mutation_result()` dùng chung.
- Chưa đổi hành vi nào: Bước 3 mới chuyển logic Python vào adapter.

### (b) Khái niệm quan trọng
- **Lớp trừu tượng (Abstract Base Class):** khai báo "hợp đồng" — các phương thức mọi lớp con BẮT BUỘC phải có.
  `LanguageAdapter()` không tạo được đối tượng (ném `TypeError`); lớp con thiếu phương thức cũng không tạo được.
  ```python
  class LanguageAdapter(ABC):
      @abstractmethod
      def run_tests(self, source_file, test_code, ...) -> TestResult: ...
  ```
- **Registry (sổ đăng ký):** một từ điển `{tên ngôn ngữ: adapter}`. Chỗ duy nhất biết "đuôi `.js` thì dùng adapter
  nào". Thêm ngôn ngữ = thêm một dòng `register(...)`.
- **Dataclass dùng chung = "ngôn ngữ chung" giữa các module:** dù pytest hay Jest, kết quả đều là
  `TestResult(passed, failed, line_coverage, ...)` → agent, `evaluate.py`, giao diện không cần biết công cụ nào đã chạy.

### (c) File liên quan
`adapters/base.py`, `adapters/registry.py`, `adapters/__init__.py`, `tests/test_adapters_base.py` (adapter giả `.fake`
chứng minh giao diện đủ để cắm một ngôn ngữ mới), `testgen/runner.py`, `testgen/mutation.py`

### (d) Lệnh tự chạy thử
```bash
pytest tests/test_adapters_base.py -v
python scripts/snapshot_python.py --out docs/thu.json --compare docs/baseline_truoc_refactor.json
# -> "Phần tất định GIỐNG HỆT"
```
Kết quả kiểm tra bước này: phần tất định **giống hệt** baseline; `pytest` 73/73 pass (64 cũ + 9 mới).

### (e) Câu hỏi giảng viên có thể hỏi
1. **Vì sao dùng lớp trừu tượng mà không chỉ viết vài hàm `if language == "python"`?** → `if/else` theo ngôn ngữ sẽ
   rải khắp agent, thêm ngôn ngữ phải sửa mọi chỗ. Lớp trừu tượng gom mọi khác biệt vào một lớp con; Python kiểm tra
   giúp lớp con có đủ phương thức.
2. **`run_tests` đã trả coverage rồi, sao còn `get_coverage`?** → Với cả pytest và Jest, coverage được đo cùng lần chạy
   test (rẻ hơn chạy 2 lần). `get_coverage` là phương thức tiện ích theo đúng giao diện, mặc định lấy từ `run_tests`.
3. **Tại sao giữ tên `RunResult`?** → Để code và test cũ vẫn chạy trong lúc refactor từng bước (không "đập đi xây lại").
