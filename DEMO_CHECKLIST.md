# DEMO CHECKLIST — chuẩn bị & kịch bản demo 5 phút

## A. Chuẩn bị (tối hôm trước)

- [ ] `git pull` / mở đúng thư mục dự án, kích hoạt môi trường: `.venv\Scripts\activate`
- [ ] `pip install -r requirements.txt` (nếu máy mới)
- [ ] `.env` có key còn hạn và đúng model. Kiểm tra nhanh 1 request:
      `python -m testgen.generator targets/calculator.py`
      - Model miễn phí OpenRouter chỉ có **50 request/ngày** → **không** chạy thực nghiệm lớn trong ngày demo.
- [ ] `pytest` → tất cả test của công cụ phải PASS (không tốn API).
- [ ] Có sẵn log để REPLAY: `dir logs` phải có ít nhất:
      - một log `grading_*` có SUSPECTED_BUG (bug 1: `letter_grade(80)`)
      - một log `shopping_cart_*` có SUSPECTED_BUG (bug 2: `remove_item`)
      - một log `calculator_agent_mutation_*` có vòng `kill_mutants` (mutation 90.9% → 100%)
- [ ] `results/summary.png` và `results/results.csv` đã có (tab Kết quả thực nghiệm).
- [ ] Mở sẵn: `slides/slides.md` (Marp, VS Code extension "Marp for VS Code" → Export PDF), `BUGS.md`, `targets/grading.py`.
- [ ] Chạy thử `streamlit run app.py` một lần, để sẵn tab trình duyệt `http://localhost:8501`.
- [ ] Tắt thông báo, phóng to font trình duyệt (Ctrl + +) để người xem thấy rõ.

## B. Ngay trước khi demo (5 phút trước)

- [ ] `streamlit run app.py` đang chạy.
- [ ] Kiểm tra mạng. **Mất mạng / API lỗi → dùng chế độ REPLAY**, không cần hoảng.
- [ ] Đóng các cửa sổ chứa `.env` (không để lộ API key trên màn chiếu).

## C. Kịch bản 5 phút

| Thời gian | Làm gì | Nói gì |
|---|---|---|
| 0:00–0:40 | Mở `targets/grading.py` (tab *Mã nguồn module*) | "Đây là code cần test. Docstring là đặc tả: điểm 80 phải được B. Trong code có một bug cài sẵn — LLM không được biết." |
| 0:40–2:30 | Sidebar: *Chạy mới* → module `grading` → bật *Mutation testing* → **Chạy agent** | Trong lúc chạy: "Vòng 0: LLM sinh test, runner chạy pytest và đo coverage. Có 1 test fail → agent hỏi LLM: test sai hay code sai? LLM trả lời *nghi code có bug* → agent GIỮ test, gắn nhãn, không sửa test cho khớp code." |
| | *(Nếu mạng chậm/lỗi quá 30 giây)* chuyển *REPLAY từ log* → chọn log `grading_agent_mutation_*` → **Phát lại** | "Để tiết kiệm thời gian em phát lại một lần chạy đã ghi log — dữ liệu y hệt lần chạy thật." |
| 2:30–3:15 | Tab **Code test** → kéo thanh vòng → chỉ vào đoạn **tô đỏ** | "Test `letter_grade(80) == 'B'` được giữ và gắn nhãn SUSPECTED_BUG kèm lý do LLM giải thích: code dùng `> 80` thay vì `>= 80`." Bật *diff* để thấy test được thêm ở vòng sau. |
| 3:15–4:00 | REPLAY log `calculator_agent_mutation_*` → tab **Biểu đồ** | "Coverage 100% ngay từ đầu nhưng mutation score chỉ 90.9%: 2 mutant ở biên `clamp` sống sót. Agent đưa mutant cho LLM, nó viết thêm test → 100%. Nhưng em phát hiện test này kiểm tra `is` — bám chi tiết cài đặt, đó là một hạn chế." |
| 4:00–4:45 | Tab **Kết quả thực nghiệm** | Đọc 2-3 con số chính từ bảng (coverage, mutation score, tỉ lệ phát hiện bug, số lần gọi LLM của A/B/C/D). Nói rõ số lần chạy và model. |
| 4:45–5:00 | Kết | "Vòng lặp phản hồi giúp giữ test phát hiện bug thay vì hợp thức hoá bug, và mutation giúp lộ các assert yếu; đổi lại tốn thêm lần gọi LLM." |

## D. Phương án dự phòng

| Sự cố | Cách xử lý |
|---|---|
| Mất mạng / API lỗi 429 / hết quota | Chế độ **REPLAY từ log** (không cần mạng) |
| Streamlit không mở | Chạy CLI: `python -m testgen.agent targets/grading.py --mutation` hoặc mở log JSON trong `logs/` |
| Hỏi "chạy code của em thử?" | Sidebar → *Dán code Python* → đặt tên module → Chạy (nhắc: code nên có docstring mô tả hành vi đúng) |
| Hỏi kết quả chi tiết | Mở `results/runs.csv` / tab thực nghiệm → *Dữ liệu thô* |
