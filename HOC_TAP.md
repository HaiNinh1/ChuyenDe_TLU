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
