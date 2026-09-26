# DEMO CHECKLIST — chuẩn bị & kịch bản demo 5 phút (Python + JavaScript/TypeScript)

## A. Chuẩn bị (tối hôm trước)

- [ ] `git pull` / mở đúng thư mục dự án, kích hoạt môi trường: `.venv\Scripts\activate`
- [ ] `pip install -r requirements.txt` và `npm install` (nếu máy mới; cần Node.js 22+)
- [ ] `.env` có key còn hạn và đúng model. Kiểm tra nhanh 1 request:
      `python -m testgen.generator targets/python/calculator.py`
      - Model miễn phí OpenRouter chỉ có **50 request/ngày** → **không** chạy thực nghiệm lớn trong ngày demo.
- [ ] `pytest` → tất cả test của công cụ phải PASS (không tốn API; test JS cần Node).
- [ ] Có sẵn log để REPLAY: `dir logs` phải có ít nhất:
      - `grading_*` có SUSPECTED_BUG (bug 1: `letter_grade(80)`) — Python
      - `shipping_agent_js_*` có SUSPECTED_BUG (bug 3: `shippingFee(500)`) — **TypeScript**
      - `bank_account_agent_js_*` (bug 4, JS) — lần chạy bị dừng vì hết quota: minh hoạ agent **dừng êm**
      - `calculator_agent_mutation_*` có vòng `kill_mutants` (mutation 90.9% → 100%)
- [ ] `results/results.csv`, `results/summary_python.png` (+ `summary_javascript.png`, `language_comparison.png` nếu
      đã chạy thực nghiệm JS) — tab Kết quả thực nghiệm.
- [ ] Mở sẵn: `slides/slides.md` (Marp), `BUGS.md`, `targets/javascript/shipping.ts`, `adapters/base.py`.
- [ ] Chạy thử `streamlit run app.py` một lần, để sẵn tab trình duyệt `http://localhost:8501`.
- [ ] Tắt thông báo, phóng to font trình duyệt (Ctrl + +) để người xem thấy rõ.

## B. Ngay trước khi demo (5 phút trước)

- [ ] `streamlit run app.py` đang chạy. Thanh bên hiện "🔧 Python: pytest + ..." (không có dòng báo thiếu công cụ).
- [ ] Chọn ngôn ngữ **JavaScript/TypeScript** một lần để chắc thanh bên hiện "Jest + Istanbul + StrykerJS".
- [ ] Kiểm tra mạng. **Mất mạng / API lỗi → dùng chế độ REPLAY**, không cần hoảng.
- [ ] Đóng các cửa sổ chứa `.env` (không để lộ API key trên màn chiếu).

## C. Kịch bản 5 phút

| Thời gian | Làm gì | Nói gì |
|---|---|---|
| 0:00–0:30 | Mở `adapters/base.py` (hoặc slide kiến trúc Adapter) | "Agent chỉ nói chuyện với một giao diện chung. Mỗi ngôn ngữ là một adapter: Python dùng pytest + mutmut, JS/TS dùng Jest + Stryker." |
| 0:30–2:15 | Sidebar: *Chạy mới* → Ngôn ngữ **JavaScript/TypeScript** → module `shipping.ts` → bật *Mutation* → **Chạy agent** | "Cùng một vòng lặp, giờ chạy trên TypeScript. Vòng 0: Jest chạy test, Istanbul đo coverage. Có test fail ở biên 500 → LLM phân loại *nghi code có bug* → agent GIỮ test, đổi thành `test.failing`, không sửa cho khớp code." |
| | *(Nếu mạng chậm/lỗi quá 30 giây)* *REPLAY từ log* → chọn `[javascript] shipping_agent_js_*` → **Phát lại** | "Em phát lại một lần chạy đã ghi log — dữ liệu y hệt lần chạy thật." |
| 2:15–2:50 | Tab **Code test** → chỉ vào đoạn **tô đỏ** | "Test `shippingFee(500)` được giữ và gắn nhãn `// SUSPECTED_BUG` + `test.failing` — tương đương `xfail` bên pytest." |
| 2:50–3:40 | REPLAY `[python] grading_*` hoặc chọn *Python* → `grading.py` | "Phần Python vẫn chạy như trước refactor: em đã chứng minh bằng ảnh chụp hành vi — 8 prompt giống từng ký tự, trạng thái từng mutant giống hệt." |
| 3:40–4:30 | Tab **Kết quả thực nghiệm** → biểu đồ so sánh hai ngôn ngữ (nếu có) | Đọc 2-3 con số chính theo từng ngôn ngữ. Nói rõ số lần chạy và model; phần nào chưa đủ số liệu thì nói thẳng. |
| 4:30–5:00 | Kết | "Kiến trúc Adapter: thêm ngôn ngữ = viết 1 lớp, không sửa vòng lặp. Java/Go là hướng phát triển (đã phác thảo JUnit + JaCoCo + PIT)." |

## D. Phương án dự phòng

| Sự cố | Cách xử lý |
|---|---|
| Mất mạng / API lỗi 429 / hết quota | Chế độ **REPLAY từ log** (không cần mạng) |
| Máy demo chưa cài Node.js | Thanh bên báo thiếu công cụ + lệnh cài; demo phần Python, REPLAY log JS (không cần Node) |
| Streamlit không mở | CLI: `python -m testgen.agent targets/javascript/shipping.ts --mutation` hoặc mở log JSON trong `logs/` |
| Hỏi "chạy code của em thử?" | Sidebar → *Dán code* → ngôn ngữ được **tự nhận diện** (chọn lại được) → đặt tên module → Chạy |
| Hỏi "thêm Java mất bao lâu?" | Mở `docs/THEM_NGON_NGU_MOI.md` (ước lượng 5–6 ngày, bảng phương thức cần viết) |
| Hỏi kết quả chi tiết | Mở `results/runs.csv` / tab thực nghiệm → *Dữ liệu thô* |
