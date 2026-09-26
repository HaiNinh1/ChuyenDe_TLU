
Tôi là sinh viên CS năm cuối, cần hoàn thành đồ án môn học để demo cuối kỳ. Hãy xây dựng TOÀN BỘ dự án dưới đây từ đầu đến cuối, tự làm liên tục qua các giai đoạn, không cần dừng lại hỏi tôi trừ khi thực sự bị chặn (ví dụ thiếu API key).

# ĐỀ TÀI

"LLM Agent tự sinh unit test cho Python với vòng lặp tự cải tiến dựa trên phản hồi coverage và mutation testing"

# CÔNG NGHỆ

- Python 3.10+, pytest, pytest-cov/coverage.py, mutmut
- LLM: [Anthropic API / OpenAI API / Ollama local], đọc cấu hình từ file .env (API key, tên model), thiết kế để dễ đổi nhà cung cấp
- Giao diện demo: Streamlit
- Biểu đồ: matplotlib
- Slide: Marp (markdown)

# QUY TẮC CHUNG

1. Code đơn giản, dễ đọc, phù hợp trình độ sinh viên. Không dùng framework agent phức tạp (LangChain, v.v.), tự viết vòng lặp để tôi hiểu rõ.
2. Comment tiếng Việt ở những chỗ quan trọng.
3. Dùng git: khởi tạo repo, commit sau MỖI giai đoạn với message rõ ràng.
4. Sau mỗi giai đoạn, tự chạy kiểm tra để chắc chắn code chạy được rồi mới sang giai đoạn tiếp. Nếu lỗi thì tự sửa.
5. Duy trì file HOC_TAP.md: sau mỗi giai đoạn ghi thêm một mục gồm (a) đã làm gì và tại sao, (b) khái niệm quan trọng giải thích dễ hiểu kèm ví dụ, (c) các file liên quan cần đọc, (d) lệnh để tôi tự chạy thử, (e) 2-3 câu hỏi giảng viên có thể hỏi kèm gợi ý trả lời.
6. Tạo file CLAUDE.md lưu mục tiêu và quy tắc này để các phiên sau vẫn nhớ.
7. Trung thực: không phóng đại kết quả, ghi rõ hạn chế.

# CÁC GIAI ĐOẠN

## GĐ0 - Khởi tạo

Cấu trúc thư mục, requirements.txt, .env.example, README.md, CLAUDE.md, HOC_TAP.md, .gitignore.

## GĐ1 - Code mục tiêu (targets/)

4-5 module Python nhỏ, độ khó tăng dần: hàm tính toán đơn giản, xử lý chuỗi, nhiều nhánh if/else, xử lý ngoại lệ, một class có trạng thái. Cố tình cài 1-2 bug nhỏ, ghi vào BUGS.md (không comment trong code).

## GĐ2 - Baseline sinh test một lần

llm_client.py (gọi LLM, có retry), prompts.py (các prompt), generator.py (sinh test một lần, lưu vào generated_tests/). Đây là mốc so sánh.

## GĐ3 - Runner

runner.py: chạy pytest qua subprocess có timeout; thu thập pass/fail/error, thông báo lỗi, line coverage, branch coverage, danh sách dòng chưa cover. Trả về dataclass.

## GĐ4 - Vòng lặp tự cải tiến (cốt lõi)

agent.py:

1. Sinh test ban đầu
2. Chạy runner
3. Lỗi syntax/import/test sai → gửi lỗi cho LLM sửa
4. Coverage chưa đạt ngưỡng → gửi dòng/nhánh chưa cover cho LLM bổ sung test
5. Tối đa N vòng, dừng sớm khi đạt ngưỡng hoặc không cải thiện
6. Ghi log từng vòng ra JSON
   Xử lý oracle problem đơn giản: khi test fail, yêu cầu LLM phân loại "test viết sai" hay "nghi code có bug"; nếu nghi bug thì giữ test lại và đánh dấu SUSPECTED_BUG thay vì sửa test cho khớp code. Vẽ sơ đồ luồng bằng mermaid lưu vào docs/.

## GĐ5 - Mutation testing

Tích hợp mutmut sau khi đạt ngưỡng coverage. Đưa mutant còn sống cho LLM viết thêm test. Giới hạn phạm vi (chỉ chạy trên module đang test, giới hạn số mutant) để chạy đủ nhanh cho demo.

## GĐ6 - Bộ nhớ "tự học"

memory.py: lưu lỗi thường gặp + cách sửa thành công, và mẫu test tốt vào JSON. Khi sinh test cho module mới, đưa vài bài học liên quan vào prompt. Không dùng vector database. Giải thích rõ trong HOC_TAP.md đây là "học" theo nghĩa nào và giới hạn của nó.

## GĐ7 - Thực nghiệm

evaluate.py so sánh trên tất cả module:

- A: Baseline
- B: Agent + coverage
- C: Agent + coverage + mutation
- D: C + memory
  Đo: line/branch coverage, mutation score, số vòng, số lần gọi LLM, thời gian, có phát hiện bug cài sẵn không. Mỗi cấu hình chạy 3 lần, lấy trung bình. Xuất results/results.csv và biểu đồ PNG trong results/.
  Nếu chi phí API là vấn đề, thêm tham số để chạy thử nhanh với ít module/ít lần.

## GĐ8 - Giao diện demo

app.py (Streamlit):

- Chọn module mẫu hoặc dán code Python
- Chạy agent, hiển thị tiến trình từng vòng
- Biểu đồ coverage/mutation score qua các vòng
- Xem code test sinh ra ở mỗi vòng, highlight test SUSPECTED_BUG
- Tab kết quả thực nghiệm
- Chế độ REPLAY chạy lại từ log đã lưu (phòng mất mạng/API lỗi khi demo)

## GĐ9 - Slide và tài liệu thuyết trình

slides/slides.md (Marp), 12-15 slide cho 10-15 phút: tiêu đề; vấn đề; hướng tiếp cận hiện có (Pynguin/EvoSuite, hướng dùng LLM); mục tiêu và phạm vi; kiến trúc; vòng lặp tự cải tiến; coverage và mutation testing bằng ví dụ; bộ nhớ; thiết lập thực nghiệm; kết quả (chèn biểu đồ từ results/); demo; hạn chế và hướng phát triển; kết luận. Ít chữ mỗi slide, ngôn ngữ đơn giản.
Kèm slides/speaker_notes.md: lời thoại từng slide + 10 câu hỏi giảng viên có thể hỏi kèm gợi ý trả lời.

## GĐ10 - Hoàn thiện

- README.md đầy đủ: giới thiệu, cài đặt, cách chạy từng phần, cách chạy demo
- DEMO_CHECKLIST.md: các bước chuẩn bị và kịch bản demo 5 phút
- Chạy lại toàn bộ từ đầu để chắc mọi thứ hoạt động
- Tổng kết cuối cùng cho tôi: đã làm được gì, hạn chế, và thứ tự tôi nên đọc code để hiểu dự án nhanh nhất

Bắt đầu từ GĐ0.
