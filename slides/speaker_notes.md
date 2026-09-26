# Lời thoại thuyết trình (10–15 phút) + câu hỏi vấn đáp

> Mẹo: nói chậm, mỗi slide ~1 phút. Slide 10 (kết quả) và 11 (demo) là quan trọng nhất — dành ~4-5 phút.

---

## Slide 0 — Tiêu đề (20 giây)
"Em xin chào thầy cô. Đề tài của em là xây dựng một **LLM agent tự sinh unit test cho Python**, có **vòng lặp tự cải
tiến** dựa trên hai loại phản hồi: **coverage** và **mutation testing**."

## Slide 1 — Vấn đề (1 phút)
"Viết unit test tốn thời gian nên hay bị bỏ qua. Hiện nay LLM viết test rất nhanh, nhưng có ba vấn đề: test có thể
không chạy được; có thể bỏ sót nhánh; và nguy hiểm nhất là test có thể **hợp thức hoá bug** — ví dụ code trả về C cho
điểm 80, LLM nhìn code rồi viết `assert == "C"`, test pass, bug bị che đi. Câu hỏi của em: làm sao để LLM tự kiểm tra
và cải thiện bộ test của nó?"

## Slide 2 — Hướng tiếp cận hiện có (1 phút)
"Có ba hướng. Thứ nhất là các công cụ tìm kiếm – tiến hoá như EvoSuite cho Java, Pynguin cho Python: coverage cao nhưng
assert chỉ 'chụp' lại hành vi hiện tại của code, nên không phát hiện được bug, và test khó đọc. Thứ hai là hỏi LLM một
lần: dễ đọc nhưng không kiểm chứng. Thứ ba — hướng nghiên cứu gần đây như CoverUp, MuTAP — kết hợp LLM với phản hồi
thực thi. Đồ án của em đi theo hướng thứ ba, và em tự cài đặt đơn giản để hiểu rõ từng bước."

## Slide 3 — Mục tiêu & phạm vi (40 giây)
"Mục tiêu: agent sinh test, chạy, đo, rồi dùng kết quả đo để tự sửa và bổ sung; xử lý oracle problem; và so sánh định
lượng 4 cấu hình. Phạm vi: Python, 5 module nhỏ tự viết có 2 bug cài sẵn, không dùng framework agent."

## Slide 4 — Kiến trúc (1 phút)
"Trung tâm là agent — thực chất là một vòng for với các if/else. Agent gửi prompt cho LLM, nhận code test, đưa cho
**Runner** chạy pytest trong tiến trình con có timeout và đo coverage. Khi coverage đủ, **Mutation** tạo các mutant và
chạy song song. **Memory** lưu kinh nghiệm vào JSON. Mọi vòng đều được ghi log JSON, giao diện Streamlit đọc log để
hiển thị hoặc phát lại."

## Slide 5 — Vòng lặp (1 phút 30)
"Thứ tự ưu tiên: sửa file hỏng trước, rồi xử lý test fail, rồi mới tăng coverage, cuối cùng là mutation. Điểm quan
trọng nhất là bước 4: khi một test fail, agent **không** tự động sửa test cho pass. Nó hỏi LLM: test này sai, hay code
có bug so với docstring? Nếu nghi bug, test được **giữ nguyên** và gắn nhãn xfail SUSPECTED_BUG, để bộ test vẫn chạy
xanh nhưng bằng chứng vẫn còn cho người review. Một chi tiết kỹ thuật: LLM chỉ trả về các hàm mới hoặc hàm đã sửa,
chương trình tự ghép bằng module `ast`, nên LLM không thể vô tình xoá test cũ hoặc gỡ nhãn."

## Slide 6 — Coverage (40 giây)
"Line coverage đo bao nhiêu phần trăm dòng được chạy; branch coverage đo bao nhiêu phần trăm nhánh True/False. Agent
không chỉ nói 'coverage 80%' mà gửi cho LLM chính xác dòng và nhánh nào chưa được đi qua, kèm nội dung dòng code."

## Slide 7 — Mutation (1 phút)
"Coverage 100% chưa chắc test tốt. Mutation testing sửa nhẹ code — ví dụ đổi `>= 90` thành `> 90` — rồi chạy lại bộ
test. Test với điểm 95 vẫn pass nên mutant 'sống sót'; phải có test đúng biên 90 mới giết được. Trong thực nghiệm, module calculator đạt
coverage 100% ngay từ đầu nhưng mutation score chỉ 90.9%; hai mutant ở biên của hàm clamp sống sót. Vì mutmut 3
không chạy trên Windows, em dùng bộ toán tử đột biến của mutmut 2.5.1 và tự viết phần chạy, giới hạn 20 mutant cho
nhanh."

## Slide 8 — Bộ nhớ (40 giây)
"Bộ nhớ là một file JSON lưu bài học sửa lỗi và mẫu test tốt, chỉ lưu khi đã được xác nhận là có tác dụng. Em muốn nói
rõ: đây là **học trong ngữ cảnh** — trọng số mô hình không đổi, chỉ là có thêm 'sổ tay kinh nghiệm' trong prompt."

## Slide 9 — Thiết lập thực nghiệm (1 phút)
"Bốn cấu hình A, B, C, D. Mọi bộ test đều được chấm lại bằng cùng một thước đo: cùng runner, cùng tập mutant với seed
cố định. Một bug được tính là phát hiện nếu có test fail trên code lỗi nhưng pass trên bản đã sửa — bản đã sửa này LLM
không bao giờ được thấy. Để tiết kiệm lượt gọi LLM, A và B được lấy từ các mốc trung gian của lần chạy C — vì A chính là
bước sinh đầu tiên của agent, và B là trạng thái lúc agent kết thúc phase coverage."

## Slide 10 — Kết quả (2 phút)
"Kết quả lượt chạy thứ nhất, 5 module. Thứ nhất, coverage đã khoảng 99% ngay từ lần sinh đầu — model này viết test khá
đầy đủ cho module nhỏ, nên phản hồi coverage gần như không có gì để cải thiện. Thứ hai, khác biệt thật nằm ở test fail:
baseline để lại trung bình 1,2 test fail mỗi module mà không biết do test sai hay code sai; agent đưa về 0, sửa các test
viết sai và gắn nhãn đúng cả 2 bug, không có nhãn sai. Thứ ba — điều em muốn nói thẳng — mutation feedback chỉ làm tăng
điểm trên chính những mutant đã đưa cho LLM; trên các mutant LLM chưa thấy thì không tăng. Lúc đầu em chấm lẫn cả hai
tập nên tưởng mutation giúp nhiều; sau khi review, em tách tập held-out và kết luận thay đổi. Cuối cùng, chi phí: số lần
gọi LLM tăng từ 1 lên 2,4 đến 3,2. Đây mới là 1 lần chạy trên 5 module nhỏ nên chỉ là quan sát ban đầu."

## Slide 11 — Demo (3-4 phút)
Theo `DEMO_CHECKLIST.md` mục C.

## Slide 12 — Hạn chế & hướng phát triển (1 phút 30)
"Em xin nêu các hạn chế: quy mô thực nghiệm nhỏ; LLM có thể phân loại sai; khi tối ưu mutation score, LLM có lúc viết
test kiểm tra chi tiết cài đặt như `result is value` — test đó giòn; hệ thống phụ thuộc docstring; bộ nhớ đơn giản.
Hướng phát triển: thực nghiệm trên dự án thật và so sánh trực tiếp với Pynguin; bộ nhớ dùng embedding; lọc mutant
tương đương; tích hợp CI."

## Slide 13 — Kết luận (30 giây)
"Tóm lại, phản hồi thực thi giúp bộ test chạy được, phủ đủ và giữ lại test phát hiện bug; mutation testing lộ ra assert
yếu. Cái giá là nhiều lần gọi LLM hơn, và con người vẫn cần review. Em cảm ơn thầy cô đã lắng nghe."

---

# 10 câu hỏi giảng viên có thể hỏi (kèm gợi ý trả lời)

**1. Agent của em khác gì so với hỏi ChatGPT viết test?**
→ ChatGPT sinh một lần, không chạy thử. Agent của em **chạy test thật**, đo coverage/mutation, và dùng kết quả đo làm
đầu vào cho lần sinh tiếp theo; đồng thời xử lý oracle problem bằng bước phân loại. Cấu hình A trong thực nghiệm chính
là "hỏi một lần" để so sánh.

**2. Oracle problem là gì, em giải quyết đến đâu?**
→ Là bài toán "làm sao biết kết quả đúng để viết assert". Em dùng docstring làm đặc tả, và khi test fail thì hỏi LLM
test sai hay code sai; nếu nghi code sai thì giữ test và gắn nhãn. Chỉ giải quyết **một phần**: nếu docstring mơ hồ hoặc
LLM phân loại sai thì vẫn sai. Em đo tỉ lệ nhãn đúng/sai (TP/FP) bằng bản code đã sửa.

**3. Làm sao em chắc LLM không "nhìn thấy" bug?**
→ Code mục tiêu không có comment nào về bug; `BUGS.md` và bản sửa `evaluation/fixed_targets/` không bao giờ được đưa vào
prompt (có thể kiểm tra trong `prompts.py` và log JSON). LLM chỉ thấy mã nguồn + docstring.

**4. Coverage 100% rồi sao còn cần mutation testing?**
→ Coverage đo code **có chạy qua** không; mutation đo assert **có đủ chặt** không. Ví dụ calculator: coverage 100% nhưng
2 mutant biên còn sống → nếu lập trình viên lỡ đổi `<` thành `<=` thì bộ test không phát hiện.

**5. Mutation testing chậm, em làm thế nào cho demo chạy kịp?**
→ Chỉ đột biến một module, lấy mẫu tối đa 20 mutant với seed cố định, chạy song song 4 tiến trình, pytest `-x` dừng
ngay khi có test fail, timeout mỗi mutant. Đánh đổi: điểm là ước lượng trên mẫu.

**6. Thiết kế ghép cặp A/B từ lần chạy C có công bằng không?**
→ A chính là bước sinh đầu tiên của agent (cùng prompt, cùng một lần gọi), B là trạng thái đúng lúc agent kết thúc phase
coverage — nếu chạy B riêng thì B cũng dừng ở đúng điểm đó. Cách này còn giảm nhiễu vì so sánh trên cùng một chuỗi trả lời
của LLM, và tiết kiệm khoảng một nửa số request (quan trọng khi model miễn phí chỉ cho 50 request/ngày).

**7. Bộ nhớ "tự học" có thật sự học không?**
→ Học theo nghĩa **in-context learning**: tích luỹ kinh nghiệm và đưa lại vào prompt; trọng số không đổi. Hiệu quả phụ
thuộc số lỗi gặp phải — với model mạnh ít lỗi thì bộ nhớ ít tác dụng, và thực nghiệm của em chưa đủ lớn để kết luận.

**8. Nếu LLM trả về code sai cú pháp hoặc xoá test cũ thì sao?**
→ Code được kiểm tra bằng `ast.parse` trước khi ghép; sai thì bỏ qua lần đó. LLM chỉ trả về hàm mới/đã sửa, chương trình
tự ghép nên không xoá được test cũ. Nếu file hỏng quá số lần cho phép, agent quay lui về phiên bản chạy được gần nhất.

**9. Vòng lặp có thể chạy mãi và tốn tiền không?**
→ Có 4 chốt chặn: số vòng tối đa, dừng khi không cải thiện sau 2 lần (patience), giới hạn số lần sửa mỗi test (quá thì
xoá test), timeout mỗi lần chạy pytest. Số lần gọi LLM được ghi lại và báo cáo trong thực nghiệm.

**10. Kết quả của em có tổng quát được không?**
→ Chưa. 5 module nhỏ do em tự viết, 2 bug tự cài, một model, số lần chạy ít. Kết quả cho thấy **xu hướng** và chứng minh
pipeline hoạt động; muốn tổng quát cần benchmark lớn hơn và so sánh với Pynguin — đó là hướng phát triển.
