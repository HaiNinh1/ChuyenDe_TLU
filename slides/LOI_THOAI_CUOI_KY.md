# Script đọc khi trình bày cuối kỳ

Đi kèm slide: `slides/bao_cao_cuoi_ky.html` (29 trang: 27 trang trình bày, 2 trang phụ lục).

- **Thời lượng dự kiến:** khoảng 20 phút nói, chưa kể demo. Thời gian ghi ở từng slide chỉ là ước lượng; nên đọc thử một lần có bấm giờ.
- **[Bấm]** nghĩa là nhấn phím mũi tên phải để hiện phần tiếp theo trên cùng slide. Slide không ghi [Bấm] thì hiện đủ ngay.
- **Trước khi vào phòng:** điền tên, MSSV, giảng viên ở slide 1 (mở file HTML bằng trình soạn thảo, tìm dòng "Sinh viên").

---

## PHẦN MỞ ĐẦU

### Slide 1. Bìa (30 giây)

Em xin chào thầy/cô. Đề tài của em là **LLM Agent tự sinh unit test đa ngôn ngữ, với vòng lặp tự cải tiến dựa trên phản hồi coverage và mutation testing**.

Thầy/cô nhìn hai dòng code trên màn hình. Đặc tả yêu cầu lớn hơn hoặc bằng 80, nhưng code lại viết lớn hơn 80. Chỉ thiếu đúng một dấu bằng. Đây là một bug có trong tập dữ liệu của em, và em sẽ dùng nó làm ví dụ xuyên suốt bài.

Bài của em gồm bốn phần: bài toán, bài nghiên cứu nền tảng, phương pháp em rút ra, và kết quả.

### Slide 2. Câu hỏi mở đầu (30 giây)

Viết unit test tốn nhiều thời gian nên hay bị bỏ qua. Hiện nay AI, cụ thể là các mô hình ngôn ngữ lớn LLM, có thể viết test rất nhanh.

Nhưng câu hỏi là: test đó có đáng tin không?

Đề tài của em trả lời câu hỏi này bằng cách không tin ngay. Chương trình cho LLM viết test, rồi tự chạy, tự đo chất lượng, yêu cầu LLM sửa hoặc viết thêm, và lặp lại nhiều vòng.

---

## PHẦN 1. BÀI TOÁN

### Slide 3. Một bug chỉ do thiếu một ký tự (30 giây)

Ví dụ cụ thể: hàm `letter_grade` đổi điểm số sang điểm chữ.

Đặc tả nói từ 80 đến dưới 90 là loại B. Nhưng vì code thiếu dấu bằng, đúng 80 điểm lại trả về C.

Câu hỏi đặt ra là: nếu cho AI viết test cho hàm này, chuyện gì sẽ xảy ra?

### Slide 4. AI chép luôn lỗi vào test (40 giây)

Trường hợp nguy hiểm nhất là AI đọc code rồi viết test theo đúng code: 80 điểm thì phải ra C.

Test này chạy qua, tức là pass. Mọi người nhìn thấy test xanh nên tưởng code đúng, trong khi bug bị giấu đi. Em gọi hiện tượng này là **hợp thức hoá bug**.

Nghiên cứu của Zhao và cộng sự ở hội nghị ISSTA 2026 cũng ghi nhận rằng code có bug có thể dẫn dắt sai LLM như vậy.

Dòng test trên màn hình là ví dụ minh hoạ của em.

### Slide 5. Coverage cao chưa chắc bắt được lỗi (40 giây)

Vậy đo chất lượng test bằng cách nào? Thước đo phổ biến nhất là coverage, tức là tỉ lệ dòng và nhánh của code mà test đã chạy qua.

Thử với 85 điểm: test đi qua nhánh B và pass. Coverage ghi nhận nhánh đó đã được phủ, nhưng bug ở mốc 80 vẫn còn nguyên.

Inozemtseva và Holmes ở ICSE 2014 đã khảo sát 31.000 bộ test trên 5 hệ thống Java. Khi cố định số lượng test, coverage chỉ tương quan thấp đến vừa với hiệu quả của bộ test. Vì vậy cần thêm một thước đo thứ hai.

### Slide 6. Mutation testing (1 phút)

Thước đo thứ hai là mutation testing. Ý tưởng là cố tình cài một lỗi nhỏ vào code. Bản code bị sửa đó gọi là mutant. Ở đây, em đổi lớn hơn hoặc bằng thành lớn hơn.

**[Bấm]** Test với 85 điểm pass trên cả code gốc lẫn mutant. Bộ test không phân biệt được hai bản, nên ta nói mutant còn sống: bộ test chưa đủ chặt.

**[Bấm]** Test với đúng 80 điểm thì pass trên code gốc nhưng fail trên mutant. Ta nói mutant bị giết: bộ test bắt được loại lỗi này.

**[Bấm]** Mutation score là số mutant bị giết chia cho tổng số mutant.

Điểm quan trọng là một mutant còn sống cho biết chính xác bộ test đang bỏ sót điều gì. Đề tài của em khai thác đúng thông tin này. Ngoài ra, Just và cộng sự ở FSE 2014 cho thấy khả năng phát hiện mutant có tương quan với khả năng phát hiện lỗi thật.

### Slide 7. Test sai hay code sai? (40 giây)

Khó khăn tiếp theo: khi một test fail, có hai khả năng.

Thứ nhất, test viết sai, ví dụ AI tính nhầm giá trị mong đợi. Khi đó phải sửa test.

Thứ hai, code có bug. Khi đó phải giữ nguyên test và báo cho người kiểm tra. Nếu sửa test cho khớp code thì bug được hợp thức hoá.

Trong kiểm thử, khó khăn này gọi là **oracle problem**, theo khảo sát của Barr và cộng sự năm 2015. Em không tuyên bố giải quyết xong bài toán này. Chương trình chỉ gắn nhãn nghi có bug, và con người vẫn là người xác nhận cuối cùng.

### Slide 8. Bốn câu hỏi nghiên cứu (30 giây)

Từ đó em đặt ra bốn câu hỏi.

Một: vòng lặp phản hồi có giúp test tốt hơn so với sinh một lần không?
Hai: có phân biệt được test sai với code sai không?
Ba: phản hồi mutation có giúp bắt được lỗi mới, tức là những mutant mà LLM chưa thấy, không?
Bốn: một vòng lặp có dùng được cho nhiều ngôn ngữ không?

Cuối bài em sẽ trả lời từng câu theo số liệu, kể cả câu chưa kết luận được.

---

## PHẦN 2. NGHIÊN CỨU NỀN TẢNG

### Slide 9. Ba hướng tiếp cận (40 giây)

Em đã tổng quan 37 tài liệu và thấy ba hướng chính.

Hướng thứ nhất dùng thuật toán tìm kiếm như EvoSuite, Pynguin. Hướng này có hệ thống, nhưng mỗi công cụ gắn với một ngôn ngữ.

Hướng thứ hai cho LLM sinh test một lần: test dễ đọc nhưng không được kiểm chứng và hay lỗi.

Hướng thứ ba kết hợp LLM với phản hồi từ công cụ đo thật. Đề tài của em thuộc hướng này. Trong đó, em chọn **MuTAP** làm bài nền tảng vì bài dùng mutation làm phản hồi, có quy trình rõ ràng và có số liệu để đối chiếu.

### Slide 10. MuTAP (30 giây)

MuTAP là bài của Dakhel và cộng sự, đăng trên tạp chí Information and Software Technology năm 2024.

Bài xuất phát từ vấn đề: test do LLM viết hay sai và bỏ sót trường hợp biên, còn coverage thì không cho thấy khả năng phát hiện lỗi.

Ý tưởng chính rất gọn: đưa mutant còn sống vào prompt, để LLM viết đúng test còn thiếu.

### Slide 11. Quy trình của MuTAP (1 phút)

MuTAP gồm sáu bước.

Bước 1, LLM sinh test từ code.
Bước 2, sửa lỗi cú pháp, yêu cầu LLM sửa tối đa 10 lần.
Bước 3, sửa giá trị mong đợi: nếu giá trị LLM viết khác kết quả của code thì thay bằng kết quả của code. Thầy/cô chú ý bước này, em sẽ quay lại ngay sau đây.
Bước 4, dùng công cụ MutPy tạo mutant và tính điểm.
Bước 5, đóng góp chính của bài: nếu chưa đạt 100 %, thêm một mutant còn sống vào prompt để LLM viết thêm test. Bước 4 và 5 lặp lại.
Bước 6, rút gọn bộ test.

### Slide 12. Kết quả trong bài báo (30 giây)

Đây là số liệu trong bài báo, em không chạy lại.

Trên bộ HumanEval, MuTAP đạt mutation score 93,57 %, còn Pynguin là 65,94 %.
Trên bộ Refactory gồm lỗi thật của sinh viên, MuTAP phát hiện 94,91 %, Pynguin 67,54 %.

Như vậy, phản hồi bằng mutation trong bài cho kết quả rất tốt. Nhưng khi đọc kỹ, em thấy có hai điểm cần xem xét.

### Slide 13. Điểm yếu 1 (40 giây)

Điểm thứ nhất nằm ở bước 3: bước này mặc định code luôn đúng.

Giả sử LLM viết đúng theo đặc tả: 80 điểm ra B.

**[Bấm]** Khi chạy, code trả về C, nên bước 3 sửa test thành C.

**[Bấm]** Test đúng bị sửa thành test sai. Bộ test mất khả năng bắt chính bug đó.

Đây là nhận xét của em khi đọc bài, không phải hạn chế do tác giả tự nêu.

### Slide 14. Điểm yếu 2 (40 giây)

Điểm thứ hai nằm ở cách chấm. Theo mô tả của bài, mutation score được tính trên chính danh sách mutant dùng để lấy mutant đưa vào prompt.

Điều này giống như cho học sinh xem trước đề rồi chấm trên đúng đề đó. Vì vậy, con số 93,57 % có thể cao hơn khả năng bắt lỗi mới.

Em cũng nói rõ: kết quả trên Refactory không bị ảnh hưởng, vì lỗi thật của sinh viên không được đưa vào prompt.

---

## PHẦN 3. PHƯƠNG PHÁP

### Slide 15. Phương pháp em rút ra (1 phút)

Từ bài báo, em rút ra phương pháp theo ba nhóm.

**Giữ:** ý tưởng dùng mutant còn sống làm phản hồi cho LLM.

**Đổi** ba chỗ. Một, khi test fail, chương trình so với đặc tả chứ không mặc định code đúng. Hai, ngoài cách chấm của MuTAP, em chấm thêm trên những mutant LLM chưa thấy, gọi là tập held-out, và kết luận dựa trên tập này. Ba, khi test bị hỏng, em gửi kèm thông báo lỗi thật cho LLM.

**Thêm** hai chỗ: phản hồi coverage trước bước mutation, và khả năng chạy trên nhiều ngôn ngữ, hiện là Python và JavaScript/TypeScript.

Một phần em chưa làm là bước rút gọn bộ test của MuTAP.

### Slide 16. Vòng lặp tự cải tiến (1 phút)

Hệ thống của em là một vòng lặp gồm bốn việc: LLM viết test, chạy test thật, đo chất lượng, rồi tạo phản hồi cụ thể để đưa vào prompt của vòng sau. Em tự viết vòng lặp này bằng `for` và `if/else`, không dùng LangChain hay framework agent.

Mỗi vòng, chương trình xử lý vấn đề ưu tiên nhất:

**[Bấm]** Trước hết là file test lỗi cú pháp hoặc import.
**[Bấm]** Tiếp theo là test fail: LLM phân loại test sai hay code sai.
**[Bấm]** Rồi đến dòng, nhánh chưa được phủ.
**[Bấm]** Cuối cùng là mutant còn sống.

Em đặt thứ tự như vậy vì coverage của một bộ test đang fail thì không đáng tin. LLM chỉ trả về test mới hoặc test đã sửa, chương trình tự ghép vào file nên LLM không xoá được test cũ. Vòng lặp dừng khi đạt ngưỡng, khi hai lần liên tiếp không cải thiện, hoặc khi hết 8 vòng.

### Slide 17. Log thật (50 giây)

Đây là một lần chạy thật trên module `grading`. Vòng đầu tiên có hai test fail.

Test bên trái kiểm tra 80 điểm phải ra B. LLM so với docstring và kết luận code sai, vì code dùng lớn hơn 80 thay vì lớn hơn hoặc bằng 80. Chương trình giữ test và gắn nhãn nghi có bug.

Test bên phải do LLM tính nhầm giá trị mong đợi: viết 44,9 trong khi đúng phải là 48,1. Trường hợp này là test sai nên được sửa.

Sau vòng này, kết quả từ 18 pass, 2 fail thành 19 pass, 1 test mang nhãn. Nếu áp dụng bước 3 của MuTAP, bug ở mốc 80 đã bị che đi.

### Slide 18. Một vòng lặp, nhiều ngôn ngữ (40 giây)

Để chạy được nhiều ngôn ngữ, em dùng mẫu thiết kế Adapter. Vòng lặp không biết mình đang làm việc với ngôn ngữ nào. Mọi thao tác phụ thuộc ngôn ngữ, như chạy test, đo coverage, chạy mutation, nằm sau một giao diện chung là `LanguageAdapter`.

Python dùng pytest, coverage.py và mutmut. JavaScript/TypeScript dùng Jest, Istanbul và StrykerJS. Java mới được phác thảo trong tài liệu, em chưa hiện thực.

Khi tách kiến trúc này, em chụp lại hành vi phần Python và so sánh sau mỗi bước: 8 prompt giống từng ký tự, 160 mutant giữ nguyên trạng thái.

---

## PHẦN 4. KẾT QUẢ

### Slide 19. Thiết kế thực nghiệm (50 giây)

Em so sánh bốn cấu hình, mỗi cấu hình thêm đúng một thành phần. A là sinh một lần. B thêm phản hồi lỗi và coverage. C thêm phản hồi mutation. D thêm bộ nhớ.

Điểm mutation được chấm trên những mutant LLM chưa thấy. Lúc đầu chính em cũng chấm trên tập có lẫn mutant đã đưa cho LLM. Một lượt review độc lập đã phát hiện lỗi này, và sau khi sửa thì kết luận thay đổi.

Bug được tính là phát hiện khi có test fail trên code lỗi và pass trên bản đã sửa, nên nhãn đúng hay sai được chấm tự động.

### Slide 20. Kết quả Python (50 giây)

Đây là số thật trên 5 module Python, 1 lượt chạy.

Từ A sang B, số test fail còn lại giảm từ trung bình 1,2 xuống 0 mỗi module. Số bug được gắn nhãn đúng tăng từ 0 trên 2 lên 2 trên 2, và không có nhãn sai.

Em cần nói rõ: ở cấu hình A, test cũng đã fail ở cả hai bug, nhưng không được phân loại nên người dùng phải tự đoán nguyên nhân. Coverage đã đạt 99 % ngay từ đầu, nên phản hồi coverage chưa thể hiện được tác dụng trên các module này.

Đổi lại, số lần gọi LLM tăng từ 1 lên khoảng 2,4 đến 3,2 lần mỗi module. Đây là quan sát ban đầu, mẫu còn nhỏ nên chưa có ý nghĩa thống kê.

### Slide 21. Cách chấm làm đổi kết luận (50 giây)

Đây là phát hiện đáng chú ý nhất của em. Biểu đồ so sánh B, chưa có mutation, với C, đã có mutation.

Nếu chấm như MuTAP, tính cả những mutant đã đưa cho LLM, điểm tăng từ 83,0 lên 86,0 %, tức là tăng 3 điểm.

**[Bấm]** Nhưng chỉ tính những mutant LLM chưa thấy thì điểm giữ nguyên 91,8 %, không tăng.

Điểm held-out cao hơn vì các mutant khó nhất đã bị loại khỏi tập này. So sánh giữa các cấu hình vẫn công bằng vì dùng chung một tập.

### Slide 22. Vì sao chưa đủ để kết luận (1 phút)

Em xem log để tìm nguyên nhân và thấy: vòng mutation chỉ thực sự sinh test ở 1 trong 5 module. Bốn module còn lại đã đạt ngưỡng 80 % nên agent dừng ngay.

**[Bấm]** Ở module duy nhất có sinh test là `safe_parser`, cả 5 mutant đưa vào prompt đều chỉ đổi nội dung thông báo lỗi. Tính trên tất cả mutant, điểm module này tăng từ 81,8 lên 97,0 %, còn trên tập held-out vẫn giữ nguyên 96,3 %.

**[Bấm]** Vì vậy em không nói MuTAP sai, và cũng không nói phản hồi mutation vô ích. Dữ liệu của em chỉ cho thấy cách chấm ảnh hưởng đến kết luận, và cần thử thêm với ngưỡng cao hơn.

### Slide 23. JavaScript/TypeScript (40 giây)

Với JavaScript/TypeScript, em mới có hai lần chạy thử, do model miễn phí giới hạn 50 request một ngày.

`shipping.ts` bắt đúng bug biên ở `shippingFee(500)`. Phản hồi coverage đưa line và branch từ 92,9 lên 100 %, mutation đạt 90 %, 3 nhãn đều đúng.

`bank_account.js` có 8 nhãn đúng và 1 nhãn sai. Nhiều test còn bám vào thuộc tính nội bộ `withdrawnToday`. Lần chạy này dừng giữa chừng vì hết hạn mức API.

Em nói thẳng: chưa có thực nghiệm A/B/C/D cho JavaScript, nên chưa so sánh được với Python.

### Slide 24. Trả lời bốn câu hỏi (50 giây)

Trở lại bốn câu hỏi.

Câu 1: **có**. Test fail còn lại giảm từ 1,2 xuống 0.
Câu 2: **có, trên mẫu nhỏ**. Python gắn nhãn đúng 2 trên 2 bug, nhưng lần chạy thử JavaScript có 1 nhãn sai nên vẫn cần người kiểm tra.
Câu 3: **chưa kết luận được**, vì vòng mutation mới sinh test ở 1 trong 5 module.
Câu 4: **có, về mặt kỹ thuật**. Thêm JavaScript không phải sửa logic vòng lặp, còn so sánh định lượng giữa hai ngôn ngữ thì chưa có số liệu.

### Slide 25. Demo (khoảng 3 đến 5 phút)

Bây giờ em xin demo.

*Thao tác: chuyển sang tab Streamlit.*

1. Chọn JavaScript/TypeScript, module `shipping.ts`, bật mutation, bấm chạy agent.
   Nói: "Cùng một vòng lặp, giờ chạy trên TypeScript."
2. Khi có test fail ở mốc 500.
   Nói: "LLM phân loại là nghi code có bug, nên agent giữ test và gắn `test.failing`, không sửa cho khớp code."
3. Mở tab Code test, chỉ vào đoạn tô đỏ.
   Nói: "Đây là test nghi có bug, người kiểm tra sẽ xem lại."
4. Đổi sang Python, module `grading.py`.
   Nói: "Cùng vòng lặp, công cụ khác."
5. Mở tab Kết quả thực nghiệm.

**Nếu mạng hoặc API lỗi quá 30 giây:** chuyển sang chế độ REPLAY và nói: "Em phát lại một lần chạy đã ghi log, dữ liệu là của lần chạy thật."

---

## PHẦN KẾT

### Slide 26. Hạn chế và hướng phát triển (50 giây)

Đề tài còn một số hạn chế. Thực nghiệm còn nhỏ: Python mới 1 lượt, JavaScript chưa có so sánh bốn cấu hình, chỉ dùng 1 model và 9 module tự viết. Ngưỡng mutation 80 % làm vòng lặp dừng sớm, trong khi MuTAP lặp tới 100 %. Và LLM vẫn có thể phân loại sai.

Hướng tiếp theo: chạy đủ 3 lượt cho mỗi ngôn ngữ với ngưỡng cao hơn, thử trên HumanEval để so sánh trực tiếp với số liệu của MuTAP, và thêm Java, Go.

### Slide 27. Kết luận (40 giây)

Tóm lại, em đã xây dựng được một agent sinh, chạy, đo, sửa và bổ sung test cho Python và JavaScript/TypeScript, kế thừa ý tưởng của MuTAP.

Em có hai đóng góp so với MuTAP. Một là không mặc định code đúng, nên giữ lại được test phát hiện bug. Hai là chấm trên mutant LLM chưa thấy, và cho thấy cách chấm có thể làm đổi kết luận.

Với số liệu hiện có, lợi ích rõ nhất là xử lý test fail. Lợi ích của phản hồi mutation trên lỗi mới chưa được xác nhận.

Em xin cảm ơn thầy/cô đã lắng nghe, và em xin nhận câu hỏi.

### Slide 28 và 29. Phụ lục

Không đọc. Chỉ mở khi thầy/cô hỏi số liệu chi tiết (slide 28) hoặc nguồn tài liệu (slide 29).

---

## Câu hỏi thầy/cô có thể hỏi

**1. Đề tài dựa trên bài nào, và khác gì bài đó?**
Em dựa trên MuTAP. Em giữ ý tưởng đưa mutant còn sống vào prompt. Em đổi cách xử lý test fail và cách chấm, thêm phản hồi coverage và đa ngôn ngữ.

**2. Vì sao điểm held-out lại cao hơn điểm tính tất cả mutant?**
Vì những mutant khó nhất còn sống nên được đưa vào prompt, và do đó bị loại khỏi tập held-out. So sánh giữa các cấu hình vẫn công bằng vì dùng chung một tập.

**3. Vậy em nói MuTAP sai à?**
Không ạ. Em chỉ cho thấy trên dữ liệu của em, cách chấm ảnh hưởng đến kết luận. Kết quả của MuTAP trên lỗi thật Refactory không bị ảnh hưởng bởi vấn đề này.

**4. Vì sao em chưa kết luận về phản hồi mutation?**
Vì vòng mutation chỉ sinh test ở 1 trong 5 module, và 5 mutant ở module đó đều chỉ đổi thông báo lỗi. Cần chạy thêm với ngưỡng cao hơn.

**5. Vì sao không phân loại test fail hoàn toàn tự động mà không cần người?**
Đây là oracle problem. LLM có thể phân loại sai, ví dụ có 1 nhãn sai ở `bank_account`, nên nhãn chỉ là "nghi có bug" để người kiểm tra.

**6. Số liệu đã đủ chưa?**
Chưa ạ. Đề yêu cầu 3 lượt, Python mới có 1 lượt, JavaScript chưa có so sánh bốn cấu hình, do giới hạn 50 request một ngày của model miễn phí. Vì vậy em ghi rõ đây là quan sát ban đầu.

**7. "Bộ nhớ tự học" có phải là huấn luyện lại model không?**
Không ạ. Đây là học trong ngữ cảnh: bài học lưu trong file JSON rồi đưa vào prompt lần sau, trọng số của model không đổi. Với 1 lượt chạy, em chưa tách được tác dụng của bộ nhớ khỏi độ ngẫu nhiên của LLM.

**8. Vì sao không dùng LangChain?**
Đề tài yêu cầu tự viết để hiểu rõ vòng lặp. Một vòng `for` với `if/else` đủ cho bài toán này và dễ kiểm tra hơn.
