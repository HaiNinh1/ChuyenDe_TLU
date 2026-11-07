# Script thuyết trình cuối kỳ

Đi kèm slide: `slides/bao_cao_cuoi_ky.html` (30 trang, mỗi trang tĩnh, bấm một lần sang một trang).

- **Điều khiển:** mũi tên phải hoặc Space sang trang sau, mũi tên trái về trang trước, F toàn màn hình.
- **Thời lượng dự kiến:** khoảng 24 phút nói, cộng 3 đến 5 phút demo. Thời gian ghi ở từng trang chỉ là ước lượng, em nên đọc thử một lần có bấm giờ.
- **Trước khi vào phòng:** điền tên, MSSV, giảng viên ở trang 1 (mở file HTML bằng trình soạn thảo, tìm dòng "Sinh viên").
- **Nếu cần rút còn khoảng 20 phút nói:** đọc lướt trang 6, 9, 10, 13, 18, 20 trong khoảng 15 giây mỗi trang, phần còn lại giữ nguyên.

---

## GIỚI THIỆU

### Trang 1. Bìa (40 giây)

Em xin chào thầy/cô. Đề tài của em là **LLM Agent tự sinh unit test đa ngôn ngữ, với vòng lặp tự cải tiến dựa trên phản hồi coverage và mutation testing**.

Nói ngắn gọn, em xây dựng một chương trình dùng mô hình ngôn ngữ lớn, gọi tắt là LLM, để tự viết unit test cho code Python và JavaScript/TypeScript.

Điểm chính là chương trình không tin ngay test do LLM viết. Nó chạy test thật, đo chất lượng, rồi đưa kết quả đo lại cho LLM để sửa và viết thêm, lặp qua nhiều vòng. Bài nghiên cứu nền tảng của em là MuTAP, đăng năm 2024.

### Trang 2. Giới thiệu đề tài (50 giây)

Thầy/cô có thể hình dung chương trình qua ba khối.

Đầu vào là một file code cần test, trong đó có docstring hoặc JSDoc. Em dùng phần mô tả này làm đặc tả, tức là code phải làm gì.

Ở giữa là agent. Mỗi vòng, LLM viết test, chương trình chạy test thật và đo coverage, mutation score, rồi chọn vấn đề cần xử lý trước và đưa vào prompt của vòng sau.

Đầu ra là bộ test chạy được, danh sách những test nghi code có bug để người kiểm tra xem lại, và log từng vòng.

Phạm vi đã làm gồm hai ngôn ngữ, 9 module tự viết có 4 bug cài sẵn, và một LLM miễn phí. So với bài nền tảng, em có ba điểm khác ghi ở góc phải, em sẽ giải thích ở phần sau.

### Trang 3. Nội dung trình bày (20 giây)

Bài của em đi theo đúng thứ tự các câu hỏi trên bảng: đề tài giải quyết vấn đề gì, đo chất lượng test bằng gì, dựa vào nghiên cứu nào, rút ra phương pháp gì, làm cụ thể như thế nào, kết quả ra sao, và cuối cùng là kết luận. Phần demo nằm ngay sau phần hệ thống.

---

## PHẦN 1. BÀI TOÁN

### Trang 4. Bối cảnh (50 giây)

Viết unit test tốn nhiều thời gian nên hay bị bỏ qua, và LLM có thể viết test rất nhanh. Nhưng test do LLM viết có ba rủi ro.

Một là không chạy được, do sai cú pháp hoặc sai import. Hai là bỏ sót nhánh hoặc trường hợp biên. Ba là viết sai, và nguy hiểm nhất là test viết theo đúng code đang sai.

Bảng phía dưới là một số quan sát từ nghiên cứu. TestPilot đạt trung vị 70,2 % statement coverage và 52,8 % branch coverage trên 25 gói npm. Ở Meta, TestGen-LLM chỉ có 75 % test build được và 25 % làm tăng coverage. Zhao và cộng sự năm 2026 ghi nhận code có bug có thể dẫn dắt sai LLM.

Vì vậy, vấn đề của đề tài là: làm sao để test do LLM viết chạy được, đủ chặt, và không che giấu bug trong code.

### Trang 5. Ví dụ xuyên suốt (50 giây)

Em lấy một ví dụ có thật trong tập dữ liệu, và sẽ dùng nó trong cả bài.

Hàm `letter_grade` đổi điểm số sang điểm chữ. Đặc tả nói từ 80 đến dưới 90 là B, nhưng code viết `score > 80`, thiếu một dấu bằng. Bảng bên phải cho thấy 85 và 79 đều đúng, chỉ riêng đúng 80 điểm là sai: phải ra B nhưng code trả về C.

Nếu LLM đọc code rồi viết test theo code, ta có dòng assert trong khung đỏ. Test này pass. Người xem thấy test xanh nên tưởng code đúng, trong khi bug bị giấu đi. Em gọi hiện tượng này là **hợp thức hoá bug**. Dòng assert này là ví dụ em minh hoạ.

---

## PHẦN 2. CƠ SỞ LÝ THUYẾT

### Trang 6. Coverage (50 giây)

Để biết test tốt hay không, thước đo phổ biến nhất là coverage. Line coverage là tỉ lệ dòng code mà test đã chạy qua, branch coverage là tỉ lệ nhánh `if/else` đã đi qua.

Nhưng coverage chưa đủ. Thử với ví dụ của em: test với 85 điểm thì pass, nhánh B được tính là đã phủ, còn bug ở mốc 80 vẫn nguyên.

Nghiên cứu cũng cho thấy điều này. Inozemtseva và Holmes khảo sát 31.000 bộ test trên 5 hệ thống Java: khi cố định số lượng test, coverage chỉ tương quan thấp đến vừa với hiệu quả của bộ test. Bài MutGen còn nêu ví dụ một bộ test đạt 100 % coverage nhưng chỉ đạt 4 % mutation score.

Tóm lại, coverage cho biết code đã được chạy qua, chứ không cho biết kết quả có được kiểm tra đúng hay không.

### Trang 7. Mutation testing (70 giây)

Vì vậy cần thước đo thứ hai là mutation testing. Ý tưởng là cố tình cài một lỗi nhỏ vào code. Bản sao bị sửa đó gọi là mutant. Ở đây, em đổi lớn hơn hoặc bằng 80 thành lớn hơn 80.

Rồi chạy bộ test trên cả hai bản. Test với 85 điểm pass trên cả code gốc lẫn mutant, tức là không phân biệt được hai bản. Ta nói mutant còn sống, bộ test chưa đủ chặt.

Test với đúng 80 điểm thì pass trên code gốc nhưng fail trên mutant. Ta nói mutant bị giết, bộ test bắt được loại lỗi này.

Mutation score là số mutant bị giết chia cho tổng số mutant.

Điểm quan trọng với đề tài của em: mỗi mutant còn sống cho biết chính xác bộ test đang bỏ sót điều gì, nên có thể đưa thẳng thông tin đó cho LLM. Về độ tin cậy, Just và cộng sự trên 357 lỗi thật cho thấy khả năng phát hiện mutant tương quan có ý nghĩa thống kê với khả năng phát hiện lỗi thật.

### Trang 8. Oracle problem (50 giây)

Khó khăn tiếp theo: khi một test fail, có hai khả năng.

Thứ nhất là test sai, ví dụ LLM tính nhầm giá trị mong đợi. Khi đó phải sửa test.

Thứ hai là code sai. Khi đó phải giữ nguyên test và báo cho người kiểm tra. Nếu sửa test cho khớp code thì bug được hợp thức hoá, đúng như em vừa nói.

Khó khăn này có tên là **oracle problem**, tức là khó biết kết quả nào mới đúng. Theo khảo sát của Barr và cộng sự, con người vẫn là nguồn xác nhận cuối cùng. Vì vậy, em dùng docstring làm căn cứ so sánh, chương trình chỉ gắn nhãn nghi có bug, và em không tuyên bố đã giải quyết xong bài toán này.

---

## PHẦN 3. NGHIÊN CỨU NỀN TẢNG

### Trang 9. Tổng quan tài liệu (50 giây)

Em đã tổng quan 37 tài liệu và thấy ba hướng chính.

Hướng thứ nhất dùng thuật toán tìm kiếm như EvoSuite, Pynguin. Hướng này có hệ thống, nhưng mỗi công cụ gắn với một ngôn ngữ. Hướng thứ hai hỏi LLM một lần: nhanh nhưng test không được kiểm chứng. Hướng thứ ba kết hợp LLM với phản hồi từ việc chạy thật, và đề tài của em thuộc hướng này.

Trong hướng thứ ba, em chọn MuTAP làm bài nền tảng vì ba lý do: bài dùng mutation testing làm phản hồi, quy trình được mô tả rõ nên đối chiếu được, và có số liệu trên cả lỗi nhân tạo lẫn lỗi thật của sinh viên.

### Trang 10. MuTAP (40 giây)

MuTAP là bài của Dakhel và cộng sự, đăng trên tạp chí Information and Software Technology năm 2024. Bài thử trên Codex và llama-2-chat, với hai bộ dữ liệu: HumanEval 164 bài toán Python và Refactory 1.710 bài nộp có lỗi thật của sinh viên.

Vấn đề bài đặt ra là test do LLM viết thường chỉ được đánh giá bằng coverage, trong khi coverage liên quan yếu đến khả năng phát hiện lỗi.

Ý tưởng chính rất gọn: đưa mutant còn sống vào prompt, kèm câu "test này không phát hiện được lỗi trong đoạn code sau", để LLM viết đúng test còn thiếu.

### Trang 11. Quy trình MuTAP (60 giây)

MuTAP có sáu bước.

Bước 1, LLM sinh test từ code. Bước 2, sửa lỗi cú pháp, yêu cầu LLM sửa tối đa 10 lần. Bước 3, sửa giá trị mong đợi: nếu giá trị LLM viết khác kết quả của code thì thay bằng kết quả của code. Thầy/cô chú ý bước này, em sẽ quay lại ngay sau đây.

Bước 4, dùng công cụ MutPy tạo mutant và tính điểm. Bước 5 là đóng góp chính: nếu chưa đạt 100 %, thêm một mutant còn sống vào prompt để LLM viết thêm test. Bước 4 và 5 lặp lại đến khi đạt 100 % hoặc hết mutant còn sống. Bước 6, rút gọn bộ test, chỉ giữ những test làm tăng điểm.

### Trang 12. Từ MuTAP đến luồng sinh test của đề tài (60 giây)

Trang này đặt quy trình của MuTAP ngay cạnh luồng của đề tài. Hàng trên là 6 bước MuTAP em vừa trình bày, hàng dưới là luồng của em, mỗi bước đặt thẳng cột với bước tương ứng. Nhãn ở giữa cho biết em giữ, đổi hay thêm.

Đi từ trái sang phải. Bước 1, LLM sinh test như MuTAP, nhưng em đưa thêm đặc tả và các bài học đã lưu từ lần chạy trước. Bước 2, khi file test bị lỗi, em gửi kèm thông báo lỗi thật để LLM sửa, MuTAP thì không gửi. Bước 3 là chỗ đổi quan trọng nhất: khi test fail, MuTAP sửa test cho khớp với code; em so với đặc tả, test sai thì sửa test, còn nghi code có bug thì giữ test và gắn nhãn.

Bước 4 là phần em thêm: gửi những dòng, nhánh chưa được phủ để LLM viết thêm test. Bước 5 em giữ nguyên ý tưởng của MuTAP: đưa mutant còn sống vào prompt. Các bước này lặp lại: mỗi vòng chạy test thật, đo lại, chưa đạt ngưỡng thì xử lý tiếp. Kết quả là bộ test và danh sách test nghi bug. Bước rút gọn bộ test của MuTAP em chưa làm.

Hai điểm khác nằm ngoài luồng: em chấm mutation trên mutant LLM chưa thấy, và chạy được cả Python lẫn JavaScript/TypeScript. Vì sao em đổi bước 3 và cách chấm, em xin trình bày ở trang 14, sau khi nói kết quả của bài báo.

### Trang 13. Kết quả trong bài báo (40 giây)

Đây là số liệu trong bài báo, em không chạy lại.

Trên HumanEval, MuTAP đạt mutation score 93,57 %, còn Pynguin là 65,94 %. Trên Refactory, MuTAP phát hiện 94,91 % lỗi thật của sinh viên, Pynguin là 67,54 %, tức là nhiều hơn 468 bài lỗi.

Tác giả kết luận rằng LLM có ích, nhưng cần thêm các bước xử lý sau thì test mới thật sự hiệu quả. Kết quả rất tốt, nhưng khi đọc kỹ, em thấy có hai điểm cần xem xét.

### Trang 14. Hai điểm cần xem xét (70 giây)

Điểm thứ nhất nằm ở bước 3: bước này mặc định code luôn đúng. Giả sử LLM viết đúng theo đặc tả, 80 điểm ra B. Khi chạy, code có bug trả về C, nên bước 3 sửa test thành C. Như vậy test đúng bị sửa thành test sai, và bộ test mất khả năng bắt chính bug đó.

Điểm thứ hai nằm ở cách chấm. Theo mô tả của bài, mutation score được tính lại trên chính danh sách mà từ đó lấy mutant đưa vào prompt, không có tập riêng mà LLM chưa thấy. Điều này giống như cho học sinh xem trước đề rồi chấm trên đúng đề đó, nên con số 93,57 % có thể cao hơn khả năng bắt lỗi mới.

Em nói rõ hai điều. Đây là nhận xét của em khi đọc bài, không phải hạn chế do tác giả tự nêu. Và kết quả trên Refactory không bị ảnh hưởng, vì lỗi thật của sinh viên không được đưa vào prompt. Em không nói kết quả của bài là sai.

---

## PHẦN 4. PHƯƠNG PHÁP

### Trang 15. Mục tiêu và câu hỏi nghiên cứu (40 giây)

Từ đó, mục tiêu của em là xây dựng agent theo ý tưởng của MuTAP, khắc phục hai điểm vừa nêu, và dùng được cho nhiều ngôn ngữ. Em đặt ra bốn câu hỏi.

Một: vòng lặp phản hồi có giúp test chạy được và đúng hơn so với sinh một lần không?
Hai: có phân biệt được test sai với code sai không?
Ba: phản hồi mutation có giúp bắt được lỗi mới, tức là mutant LLM chưa thấy, không?
Bốn: một vòng lặp có dùng được cho nhiều ngôn ngữ không?

Cột bên phải là cách đo từng câu. Cuối bài em sẽ trả lời theo số liệu, kể cả câu chưa kết luận được.

### Trang 16. Phương pháp rút ra (60 giây)

Đây là phần em rút ra từ bài báo, chia làm ba nhóm.

**Giữ:** ý tưởng dùng mutant còn sống làm phản hồi.

**Đổi** ba chỗ. Một, khi test fail, chương trình so với đặc tả chứ không mặc định code đúng: test sai thì sửa, nghi code sai thì giữ test và gắn nhãn. Hai, em chấm cả hai cách và kết luận theo những mutant LLM chưa thấy, gọi là tập held-out. Ba, khi test bị hỏng, em gửi kèm thông báo lỗi thật. Chính tác giả MuTAP cũng nêu việc không gửi thông báo lỗi là một hạn chế.

**Thêm** ba chỗ: phản hồi coverage trước bước mutation, bộ nhớ bài học lưu trong file JSON, và ngôn ngữ thứ hai.

Bước rút gọn bộ test của MuTAP thì em chưa làm.

---

## PHẦN 5. HỆ THỐNG VÀ DEMO

### Trang 17. Phương pháp sinh unit test (70 giây)

Phương pháp của em là: LLM viết test, rồi tự cải tiến nhờ phản hồi từ việc chạy test thật.

Thầy/cô đọc hàng trên từ trái sang phải. Đầu vào là code có đặc tả. Bước 1, LLM viết test theo đặc tả. Bước 2, chương trình chạy test thật. Bước 3, đo kết quả: pass hay fail, coverage và mutation. Nếu đạt ngưỡng thì ra bộ test, kèm nhãn nghi có bug nếu có.

Nếu chưa đạt thì sang bước 4: gửi phản hồi cho LLM rồi lặp lại. Mỗi vòng chỉ xử lý một vấn đề, theo đúng thứ tự trên hình. File test lỗi thì gửi thông báo lỗi thật. Có test fail thì so với đặc tả: test sai thì sửa, nghi code sai thì giữ test và gắn nhãn. Coverage thấp thì gửi dòng và nhánh chưa phủ. Mutation thấp thì gửi mutant còn sống. Em xử lý test fail trước vì coverage của một bộ test đang fail thì không đáng tin.

Hàng dưới là quan hệ với MuTAP. Em giữ ý tưởng đưa mutant còn sống vào prompt. Em đổi hai điểm: không mặc định code đúng khi test fail, và chấm trên mutant LLM chưa thấy. Em thêm phản hồi coverage, bộ nhớ bài học và chạy trên Python cùng JavaScript/TypeScript.

Vòng lặp này em tự viết bằng `for` và `if/else`, không dùng LangChain. Vòng lặp dừng khi đạt ngưỡng, khi hai lần liên tiếp không cải thiện, hoặc khi hết 8 vòng.

*Nếu được hỏi:*
- **Ngưỡng bao nhiêu?** Line 95 %, branch 90 %, mutation 80 %.
- **LLM có xóa được test cũ không?** Không. LLM chỉ trả về test mới hoặc test đã sửa, chương trình tự ghép vào file.
- **Ai đo điểm?** Công cụ thật đo, LLM không tự chấm mình.
- **Coverage chưa đạt mà không cải thiện thì sao?** Chương trình chuyển sang bước mutation, hình đã lược bỏ nhánh này cho dễ nhìn.

### Trang 18. LLM nhận phản hồi gì (50 giây)

Bảng này cho thấy mỗi tình huống đưa gì vào prompt. File test không chạy được thì gửi kèm thông báo lỗi thật. Có test fail thì yêu cầu LLM phân loại từng test và trả về JSON. Coverage thấp thì chỉ ra đúng dòng và nhánh chưa phủ. Còn mutant sống thì đưa mutant đó vào, yêu cầu test pass trên code đúng và fail trên mutant.

Quy tắc đầu tiên trong mọi prompt là viết assert theo đặc tả, không suy ra kết quả từ cách code cài đặt. Đây là cách em giảm hiện tượng hợp thức hoá bug.

Khung bên phải là một mutant thật đã đưa vào prompt, chỉ đổi nội dung thông báo lỗi. Em sẽ quay lại loại mutant này ở phần kết quả.

### Trang 19. Log thật (60 giây)

Đây là một lần chạy thật trên module `grading`. Vòng đầu tiên có hai test fail.

Test bên trái kiểm tra 80 điểm phải ra B. LLM so với docstring và trả lời rằng code sai, vì dùng lớn hơn 80 thay vì lớn hơn hoặc bằng 80. Chương trình giữ test và gắn nhãn nghi có bug.

Test bên phải do LLM tính nhầm giá trị mong đợi: viết 44,9 trong khi đúng là 48,1. Trường hợp này là test sai nên được sửa.

Sau vòng này, kết quả từ 18 pass, 2 fail thành 19 pass, 0 fail và 1 test mang nhãn. Nếu áp dụng bước 3 của MuTAP, bug ở mốc 80 đã bị che đi.

### Trang 20. Kiến trúc Adapter (50 giây)

Để chạy được nhiều ngôn ngữ, em dùng mẫu thiết kế Adapter. Vòng lặp không biết mình đang làm việc với ngôn ngữ nào. Mọi thao tác phụ thuộc ngôn ngữ như chạy test, đo coverage, chạy mutation đều nằm sau giao diện chung `LanguageAdapter`.

Python dùng pytest, coverage.py và các toán tử của mutmut. JavaScript/TypeScript dùng Jest, Istanbul và StrykerJS. Java mới được phác thảo trong tài liệu, em chưa hiện thực.

Khi tách kiến trúc này từ bản chỉ có Python, em so sánh hành vi trước và sau: 8 prompt giống từng ký tự, trạng thái từng mutant của 4 bộ test giống hệt, và agent với LLM giả lập cho cùng 7 hành động.

### Trang 21. Demo (3 đến 5 phút)

Bây giờ em xin demo.

*Thao tác: chuyển sang tab giao diện demo (`http://127.0.0.1:8000`), chạy theo bảng trên slide. Lời nói đầy đủ từng bước nằm trong `slides/KICH_BAN_DEMO.md`.*

1. Dán `ticket_price`, bấm chạy agent. Nói: "Coverage cao vẫn có test fail. LLM so với đặc tả và nghi code sai, trong khi bước 3 của MuTAP sẽ sửa test cho khớp code."
2. Mở tab Code test, chỉ đoạn tô đỏ. Nói: "Test được giữ để người kiểm tra xem lại."
3. REPLAY `calculator_agent_mutation`. Nói: "Đây là ý tưởng em giữ từ MuTAP: đưa mutant còn sống vào prompt để LLM viết thêm test."
4. REPLAY `shipping_agent_js`. Nói: "Cùng vòng lặp, giờ chạy trên TypeScript, và có thêm phản hồi coverage."
5. Quay lại slide, sang trang 22. Nói: "Còn một điểm đổi nữa là cách chấm, phải nhìn trên số liệu thực nghiệm, nên em xin chuyển sang phần kết quả."

**Nếu mạng hoặc API lỗi quá 30 giây:** chuyển sang chế độ REPLAY, chọn `user_module_app_20261031-233732` và nói: "Em phát lại một lần chạy đã ghi log, dữ liệu là của lần chạy thật."

---

## PHẦN 6. THỰC NGHIỆM VÀ KẾT QUẢ

### Trang 22. Thiết kế thực nghiệm (60 giây)

Em so sánh bốn cấu hình, mỗi cấu hình thêm một thành phần. A là sinh một lần. B thêm xử lý test fail và phản hồi coverage. C thêm phản hồi mutation. D thêm bộ nhớ.

Về cách chấm, em bỏ các mutant đã đưa vào prompt của C và D, rồi dùng chung tập còn lại để chấm cả bốn cấu hình. Đó là tập held-out. Một bug được tính là phát hiện khi có test fail hoặc mang nhãn trên code lỗi và pass trên bản đã sửa, nên nhãn đúng hay sai được chấm tự động.

Em cũng nói thật: lúc đầu chính em chấm trên tập có lẫn mutant đã đưa cho LLM. Một lượt review độc lập đã phát hiện lỗi này, và sau khi sửa thì kết luận thay đổi.

### Trang 23. Kết quả Python (60 giây)

Đây là số thật trên 5 module Python, 1 lượt chạy.

Thầy/cô nhìn hai cột in đậm. Từ A sang B, test fail còn lại giảm từ trung bình 1,2 xuống 0 mỗi module. Bug được gắn nhãn đúng tăng từ 0 trên 2 lên 2 trên 2, không có nhãn sai.

Em cần nói rõ: ở cấu hình A, test cũng đã fail ở cả hai bug, nhưng không được phân loại nên người dùng phải tự đoán nguyên nhân. Coverage đạt 99 % ngay từ lần sinh đầu, nên phản hồi coverage chưa thể hiện được tác dụng trên các module nhỏ này.

Đổi lại, số lần gọi LLM tăng từ 1 lên khoảng 2,4 đến 3,2 lần mỗi module. Đây là quan sát ban đầu, mẫu còn nhỏ nên chưa có ý nghĩa thống kê.

### Trang 24. Cách chấm làm đổi kết luận (50 giây)

Đây là phát hiện đáng chú ý nhất của em. Biểu đồ so sánh B, chưa có mutation, với C, đã có mutation.

Đường màu vàng là chấm như MuTAP, tính cả những mutant đã đưa cho LLM: điểm tăng từ 83,0 lên 86,0 %, tức là tăng 3 điểm, trông như phản hồi mutation có tác dụng.

Đường màu xanh chỉ tính những mutant LLM chưa thấy: điểm giữ nguyên 91,8 %, không tăng.

Thầy/cô có thể thắc mắc vì sao đường xanh cao hơn. Lý do là những mutant khó nhất còn sống nên được đưa vào prompt, và vì thế bị loại khỏi tập held-out. So sánh giữa các cấu hình vẫn công bằng vì dùng chung một tập.

### Trang 25. Vì sao chưa đủ để kết luận (60 giây)

Em không dừng ở đó mà đọc log để tìm nguyên nhân. Bảng này cho thấy vòng mutation chỉ thực sự sinh test ở 1 trong 5 module. Bốn module còn lại đã đạt ngưỡng 80 % nên agent dừng ngay, điểm không đổi là đương nhiên.

Module duy nhất có sinh test là `safe_parser`, dòng tô màu. Cả 5 mutant đưa vào prompt ở đây đều chỉ đổi nội dung thông báo lỗi. Tính trên tất cả mutant, điểm tăng từ 81,8 lên 97,0 %, còn trên tập held-out vẫn giữ 96,3 %.

Vì vậy em không nói MuTAP sai, và cũng không nói phản hồi mutation vô ích. Dữ liệu chỉ cho thấy cách chấm ảnh hưởng đến kết luận. Ngưỡng 80 % làm vòng mutation gần như chưa chạy, trong khi MuTAP lặp tới 100 %, nên cần thử với ngưỡng cao hơn.

### Trang 26. JavaScript/TypeScript (40 giây)

Với JavaScript/TypeScript, em mới có hai lần chạy thử, do model miễn phí giới hạn 50 request một ngày.

`shipping.ts` chạy đủ vòng lặp và bắt đúng bug biên ở `shippingFee(500)`. Phản hồi coverage đưa line và branch từ 92,9 lên 100 %, mutation đạt 90 %, 3 nhãn đều đúng.

`bank_account.js` có 8 nhãn đúng và 1 nhãn sai. Nhiều test còn đọc thuộc tính nội bộ `withdrawnToday`, tức là bám vào chi tiết cài đặt. Lần chạy này dừng giữa chừng vì hết hạn mức API.

Em nói thẳng: chưa có thực nghiệm A/B/C/D cho JavaScript, nên chưa so sánh được với Python.

### Trang 27. Trả lời bốn câu hỏi (50 giây)

Trở lại bốn câu hỏi.

Câu 1: **có**. Test fail còn lại giảm từ 1,2 xuống 0, đổi lại phải gọi LLM nhiều hơn.
Câu 2: **có, trên mẫu nhỏ**. Python gắn nhãn đúng 2 trên 2 bug, nhưng lần chạy thử JavaScript có 1 nhãn sai nên vẫn cần người kiểm tra.
Câu 3: **chưa kết luận được**, vì vòng mutation mới sinh test ở 1 trong 5 module.
Câu 4: **có, về mặt kỹ thuật**. Thêm JavaScript không phải sửa logic vòng lặp, còn so sánh định lượng giữa hai ngôn ngữ thì chưa có số liệu.

---

## PHẦN 7. KẾT LUẬN

### Trang 28. Hạn chế và hướng phát triển (40 giây)

Đề tài còn một số hạn chế. Thực nghiệm còn nhỏ: Python mới 1 lượt trong khi đề yêu cầu 3, JavaScript chưa có so sánh bốn cấu hình, chỉ dùng 1 model và 9 module tự viết. Ngưỡng 80 % làm vòng lặp dừng sớm. LLM vẫn có thể phân loại sai, và chương trình phụ thuộc vào việc code có đặc tả.

Hướng tiếp theo: chạy đủ 3 lượt cho mỗi ngôn ngữ với ngưỡng cao hơn, thử trên HumanEval để so sánh trực tiếp với số liệu của MuTAP, thử cách thay code trong prompt bằng đặc tả của Zhao và cộng sự, thêm Java và Go, và thêm bước rút gọn bộ test.

### Trang 29. Kết luận (40 giây)

Tóm lại, em đã xây dựng được một agent sinh, chạy, đo, sửa và bổ sung test cho Python và JavaScript/TypeScript, kế thừa ý tưởng của MuTAP.

Em có hai đóng góp so với MuTAP. Một là không mặc định code đúng, nên giữ lại được test phát hiện bug. Hai là chấm trên mutant LLM chưa thấy, và cho thấy cách chấm có thể làm đổi kết luận.

Với số liệu hiện có, lợi ích rõ nhất là xử lý test fail. Lợi ích của phản hồi mutation trên lỗi mới chưa được xác nhận, và con người vẫn là người xác nhận cuối cùng.

Em xin cảm ơn thầy/cô đã lắng nghe, và em xin nhận câu hỏi.

### Trang 30. Tài liệu tham khảo

Không đọc. Để trang này hoặc quay lại trang 27 trong lúc trả lời câu hỏi.

---

## Câu hỏi thầy/cô có thể hỏi

**1. Đề tài dựa trên bài nào, và khác gì bài đó?**
Em dựa trên MuTAP. Em giữ ý tưởng đưa mutant còn sống vào prompt. Em đổi cách xử lý test fail và cách chấm, thêm phản hồi coverage và đa ngôn ngữ. (Trang 16)

**2. Vì sao điểm held-out lại cao hơn điểm tính tất cả mutant?**
Vì những mutant khó nhất còn sống nên được đưa vào prompt, và do đó bị loại khỏi tập held-out. So sánh giữa các cấu hình vẫn công bằng vì dùng chung một tập. (Trang 24)

**3. Vậy em nói MuTAP sai à?**
Không ạ. Em chỉ cho thấy trên dữ liệu của em, cách chấm ảnh hưởng đến kết luận. Kết quả của MuTAP trên lỗi thật Refactory không bị ảnh hưởng bởi vấn đề này.

**4. Vì sao em chưa kết luận về phản hồi mutation?**
Vì vòng mutation chỉ sinh test ở 1 trong 5 module, và 5 mutant ở module đó đều chỉ đổi thông báo lỗi. Cần chạy thêm với ngưỡng cao hơn. (Trang 25)

**5. Vì sao không phân loại test fail hoàn toàn tự động mà không cần người?**
Đây là oracle problem. LLM có thể phân loại sai, ví dụ có 1 nhãn sai ở `bank_account`, nên nhãn chỉ là "nghi có bug" để người kiểm tra.

**6. Số liệu đã đủ chưa?**
Chưa ạ. Đề yêu cầu 3 lượt, Python mới có 1 lượt, JavaScript chưa có so sánh bốn cấu hình, do giới hạn 50 request một ngày của model miễn phí. Vì vậy em ghi rõ đây là quan sát ban đầu.

**7. "Bộ nhớ tự học" có phải là huấn luyện lại model không?**
Không ạ. Đây là học trong ngữ cảnh: bài học lưu trong file JSON rồi đưa vào prompt lần sau, trọng số của model không đổi. Với 1 lượt chạy, em chưa tách được tác dụng của bộ nhớ khỏi độ ngẫu nhiên của LLM.

**8. Vì sao không dùng LangChain?**
Đề tài yêu cầu tự viết để hiểu rõ vòng lặp. Một vòng `for` với `if/else` đủ cho bài toán này và dễ kiểm tra hơn.
