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
