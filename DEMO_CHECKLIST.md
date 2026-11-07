# DEMO CHECKLIST — chuẩn bị & kịch bản demo 5 phút (Python + JavaScript/TypeScript)

## A. Chuẩn bị (tối hôm trước)

- [ ] `git pull` / mở đúng thư mục dự án, kích hoạt môi trường: `.venv\Scripts\activate`
- [ ] `pip install -r requirements.txt` và `npm install` (nếu máy mới; cần Node.js 22+)
- [ ] `.env` có key còn hạn và đúng model. Kiểm tra nhanh 1 request:
      `python -m testgen.generator targets/python/calculator.py`
      - Model demo: `nvidia/nemotron-3.5-super-vl:free`. Model miễn phí trên OpenRouter hay bị rút (model cũ
        `nemotron-3-super-120b-a12b:free` đã trả lỗi 404) → **luôn thử lại vào tối hôm trước**.
      - `OPENROUTER_API_KEY=key1,key2,key3`: key lỗi 401/402/429 thì tự chuyển sang key sau. Quota miễn phí tính
        theo **tài khoản**: các key cùng tài khoản dùng chung quota, không cộng thêm.
      - Model miễn phí OpenRouter chỉ có **50 request/ngày** → **không** chạy thực nghiệm lớn trong ngày demo
        (mỗi lần chạy agent tốn 2–3 request).
- [ ] `pytest` → tất cả test của công cụ phải PASS (không tốn API; test JS cần Node).
- [ ] Có sẵn log để REPLAY: `dir logs` phải có ít nhất:
      - `grading_*` có SUSPECTED_BUG (bug 1: `letter_grade(80)`) — Python
      - `shipping_agent_js_*` có SUSPECTED_BUG (bug 3: `shippingFee(500)`) — **TypeScript**
      - `bank_account_agent_js_*` (bug 4, JS) — lần chạy bị dừng vì hết quota: minh hoạ agent **dừng êm**
      - `calculator_agent_mutation_*` có vòng `kill_mutants` (mutation 90.9% → 100%)
- [ ] `results/results.csv`, `results/summary_python.png` (+ `summary_javascript.png`, `language_comparison.png` nếu
      đã chạy thực nghiệm JS) — tab Kết quả thực nghiệm.
- [ ] Mở sẵn: `slides/bao_cao_cuoi_ky.html`, `slides/KICH_BAN_DEMO.md`, `BUGS.md`, `adapters/base.py`.
- [ ] Nhấn đúp `run_demo.bat` chạy thử một lần, để sẵn tab trình duyệt `http://127.0.0.1:8000`.
- [ ] Tắt thông báo, phóng to font trình duyệt (Ctrl + +) để người xem thấy rõ.

## B. Ngay trước khi demo (5 phút trước)

- [ ] `python server.py` đang chạy. Ô "Bộ công cụ Python" ở thanh bên hiện pytest, coverage.py, mutmut (không có dòng báo thiếu công cụ).
- [ ] Chọn ngôn ngữ **JavaScript/TypeScript** một lần để chắc thanh bên hiện "Jest + Istanbul + StrykerJS".
- [ ] Kiểm tra mạng. **Mất mạng / API lỗi → dùng chế độ REPLAY**, không cần hoảng.
- [ ] Đóng các cửa sổ chứa `.env` (không để lộ API key trên màn chiếu).

## C. Kịch bản demo

Thao tác và lời nói từng bước: **`slides/KICH_BAN_DEMO.md`** (nhắc lại MuTAP, chạy thật `ticket_price`, REPLAY
`calculator_agent_mutation` và `shipping_agent_js`, rồi sang slide 21). Cuối file đó có bảng thuật ngữ để trả lời khi thầy hỏi.

### Đoạn code dán vào ở bước chạy thật (đã thử: ~20 giây)
Sidebar: *Chạy mới* → *Dán code* → dán đoạn dưới → **bấm ra ngoài ô để xác nhận** → **Chạy agent**. Hỏi thầy trước:
"Thầy có thấy lỗi không?" (đặc tả nói `age >= 60` giá 70000, code viết `age <= 60` nên đúng 60 tuổi tính sai). Đây là một
lần chạy thật của LLM, kết quả mỗi lần có thể khác, nên không hứa trước là chắc chắn bắt được.

```python
def ticket_price(age):
    """Tính giá vé theo tuổi.

    - age < 0: ném ValueError
    - 0 <= age < 6: miễn phí (0)
    - 6 <= age < 18: 50000
    - 18 <= age < 60: 100000
    - age >= 60: 70000
    """
    if age < 0:
        raise ValueError("Tuổi không hợp lệ")
    if age < 6:
        return 0
    if age < 18:
        return 50000
    if age <= 60:
        return 100000
    return 70000
```

## D. Phương án dự phòng

| Sự cố | Cách xử lý |
|---|---|
| Một key hết quota | Không cần làm gì: agent tự chuyển sang key sau (dòng `[llm] Key 1/3 lỗi ...` chỉ hiện ở cửa sổ terminal) |
| Model bị rút / quá tải (404, 429 ở mọi key) | Sửa ô **Model** ở thanh bên thành `nvidia/nemotron-3-ultra-550b-a55b:free` (chậm hơn, 4–6 phút) hoặc dùng REPLAY |
| Mất mạng / hết quota cả 3 key | Chế độ **REPLAY từ log** (không cần mạng): `[python] user_module_app_20261031-233732` thay cho bước chạy thật |
| Máy demo chưa cài Node.js | Thanh bên báo thiếu công cụ + lệnh cài; demo phần Python, REPLAY log JS (không cần Node) |
| Giao diện không mở (cổng 8000 bận / lỗi server) | CLI: `python -m testgen.agent targets/javascript/shipping.ts --mutation` hoặc mở log JSON trong `logs/` |
| Hỏi "chạy code của em thử?" | Sidebar → *Dán code* → ngôn ngữ được **tự nhận diện** (chọn lại được) → đặt tên module → Chạy |
| Hỏi "thêm Java mất bao lâu?" | Mở `docs/THEM_NGON_NGU_MOI.md` (ước lượng 5–6 ngày, bảng phương thức cần viết) |
| Hỏi kết quả chi tiết | Mở `results/runs.csv` / tab thực nghiệm → *Dữ liệu thô* |
