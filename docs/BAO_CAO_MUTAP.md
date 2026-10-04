# Báo cáo tìm hiểu bài nghiên cứu MuTAP

**Đề tài:** AI sinh unit test tự động
**Bài nghiên cứu chính:** *Effective Test Generation Using Pre-trained Large Language Models and Mutation Testing*
**Ngày báo cáo:** 04/10/2026

Báo cáo gồm 3 phần:

1. Bài nghiên cứu nói về cái gì.
2. Em đang nghiên cứu tới đâu.
3. Em áp dụng bài vào đề tài như thế nào.

---

## Phần 1. Bài nghiên cứu nói về cái gì

### 1.1. Thông tin bài báo

| Mục | Nội dung |
|---|---|
| Tên bài | Effective Test Generation Using Pre-trained Large Language Models and Mutation Testing |
| Tên phương pháp | MuTAP |
| Tác giả | Arghavan Moradi Dakhel, Amin Nikanjam, Vahid Majdinasab, Foutse Khomh, Michel C. Desmarais |
| Nơi công bố | Tạp chí *Information and Software Technology*, 2024 — DOI: [10.1016/j.infsof.2024.107468](https://doi.org/10.1016/j.infsof.2024.107468) |
| Bản đọc miễn phí | [arXiv:2308.16557](https://arxiv.org/abs/2308.16557) |

**Tóm tắt một câu:** bài cho AI viết unit test, sau đó tìm những lỗi mà bộ test còn bỏ sót và đưa đúng những lỗi đó lại
cho AI để nó viết thêm test.

### 1.2. Vấn đề bài giải quyết

- AI (mô hình ngôn ngữ lớn — LLM) viết unit test rất nhanh. Các nghiên cứu trước đây chủ yếu đánh giá test do AI viết
  bằng **coverage**, tức là tỉ lệ phần code mà test đã chạy qua.
- Tác giả chỉ ra rằng coverage chỉ liên quan **yếu** đến khả năng phát hiện bug. Test chạy qua một dòng code nhưng có thể
  không hề kiểm tra kết quả của dòng đó.
- Test do AI viết còn hay sai cú pháp, sai giá trị mong đợi và bỏ qua các trường hợp biên.

**Mục tiêu của bài:** làm cho test do AI viết phát hiện được nhiều lỗi hơn, bằng cách dùng **mutation testing** làm
phản hồi cho AI.

### 1.3. Khái niệm cần biết

| Khái niệm | Giải thích |
|---|---|
| Unit test | Đoạn kiểm tra tự động cho một hàm: đưa vào một input rồi so kết quả với giá trị mong đợi |
| Coverage | Tỉ lệ phần code đã được test chạy qua |
| Mutant | Một bản sao của code bị cố ý sửa sai một chút, ví dụ đổi dấu hoặc đổi phép toán |
| Mutant bị "giết" | Có ít nhất một test báo lỗi khi chạy trên bản sai, tức là bộ test phát hiện được lỗi đó |
| Mutant còn sống | Mọi test vẫn qua trên bản sai, tức là bộ test đã bỏ sót loại lỗi này |
| Mutation score (MS) | Số mutant bị giết chia cho tổng số mutant. Điểm càng cao thì bộ test bắt được càng nhiều lỗi |
| Zero-shot / few-shot | Hai cách hỏi AI: không kèm ví dụ (zero-shot) hoặc kèm vài ví dụ mẫu (few-shot) |

**Ví dụ minh hoạ** (em tự đặt ra, không lấy từ bài): một hàm xếp loại quy định "từ 80 điểm trở lên là loại B". Một
mutant sửa điều kiện thành "trên 80 điểm là loại B".

- Nếu bộ test chỉ thử với 85 điểm thì cả code gốc lẫn mutant đều trả về B. Mutant còn sống, dù coverage có thể đã
  đạt 100 %.
- Nếu thêm một test với đúng 80 điểm thì code gốc trả về B còn mutant trả về C. Mutant bị giết. Test mới này chính là
  test kiểm tra giá trị biên.

### 1.4. Phương pháp MuTAP

**Ý tưởng chính:** mutant còn sống cho AI biết chính xác bộ test đang bỏ sót lỗi nào. Vì vậy MuTAP đưa mutant đó vào câu
hỏi (prompt) để AI viết thêm test bắt đúng lỗi đó.

Quy trình gồm 6 bước:

1. **Sinh test ban đầu:** đưa code cần test cho AI, hỏi theo kiểu zero-shot hoặc few-shot.
2. **Sửa cú pháp:** kiểm tra test bằng bộ phân tích cú pháp của Python. Nếu test có lỗi thì yêu cầu AI sửa, tối đa
   10 lần. Nếu vẫn còn lỗi thì chỉ giữ phần test nằm trước dòng lỗi.
3. **Sửa giá trị mong đợi:** chạy code thật với input của từng test. Nếu giá trị mong đợi mà AI viết khác với kết quả
   của code thì thay bằng kết quả của code. Bước này **giả định code luôn đúng**.
4. **Mutation testing:** dùng công cụ MutPy để tạo mutant, chạy bộ test trên từng mutant rồi tính mutation score.
5. **Bổ sung prompt:** nếu mutation score chưa đạt 100 %, thêm vào prompt bộ test hiện tại, câu "test này không phát
   hiện được lỗi trong đoạn code sau" và **một** mutant còn sống, rồi yêu cầu AI viết thêm test.
6. **Rút gọn bộ test:** chỉ giữ những test làm tăng mutation score và bỏ các test thừa (dùng thuật toán tham lam).

Bước 4 và bước 5 lặp lại cho đến khi mutation score đạt 100 % hoặc đã dùng hết các mutant còn sống. Sơ đồ quy trình:

> Sinh test → Sửa cú pháp → Sửa giá trị mong đợi → Đo mutation → **Đã bắt hết mutant?**
> — Chưa: thêm 1 mutant còn sống vào prompt, AI viết thêm test, rồi quay lại kiểm tra.
> — Rồi: rút gọn bộ test và kết thúc.

### 1.5. Thực nghiệm và kết quả

**Cách thử nghiệm:**

- **Mô hình AI:** Codex (code-davinci-002) và llama-2-chat.
- **Dữ liệu:** HumanEval (164 bài toán Python, lỗi được tạo bằng mutant) và Refactory (1.710 bài nộp có lỗi thật của
  sinh viên).
- **So sánh với:** Pynguin (công cụ sinh test không dùng AI) và cách hỏi AI zero-shot/few-shot không có vòng lặp
  mutation.

**Kết quả chính** (MuTAP dùng llama-2-chat few-shot, cấu hình cho kết quả tốt nhất trong bài):

| Tiêu chí | MuTAP | Pynguin |
|---|---|---|
| HumanEval: mutation score | 93,57 % | 65,94 % |
| HumanEval: số mutant bị giết (trên tổng 1.260) | 1.179 | 649 |
| HumanEval: số bài đạt mutation score 100 % | 114 bài (69,93 %) | 46 bài (28,22 %) |
| Refactory: tỉ lệ phát hiện lỗi thật | 94,91 % | 67,54 % |

- Trên Refactory, MuTAP phát hiện nhiều hơn Pynguin 468 bài lỗi (28 %).
- Có 79 bài lỗi (17 %) mà cả Pynguin lẫn AI không có vòng lặp đều bỏ sót; chỉ MuTAP phát hiện được.

**Kết luận của tác giả:** AI có ích cho việc sinh test, nhưng cần thêm các bước xử lý sau (sửa cú pháp, sửa giá trị mong
đợi, phản hồi bằng mutation) thì test mới thật sự hiệu quả.

### 1.6. Hạn chế của bài

**Tác giả tự nêu:**

- Bước sửa cú pháp chỉ yêu cầu AI sửa lại, không gửi kèm thông báo lỗi.
- Cách rút gọn bộ test bằng thuật toán tham lam có thể chưa tối ưu.
- Bài chỉ sinh các câu kiểm tra (assert) dạng đơn giản.
- Mutant là lỗi nhân tạo, nên tác giả dùng thêm bộ dữ liệu Refactory để kiểm tra trên lỗi thật.
- Phần cài đặt hiện tại chỉ dành cho Python.
- Các mô hình AI thay đổi liên tục nên khó lặp lại y hệt kết quả.

**Em nhận xét thêm:** bước 3 giả định code luôn đúng. Nếu code thật sự có bug và AI đã viết test đúng, bước này vẫn sửa
test cho khớp với bug. Khi đó test sẽ "hợp thức hoá" bug thay vì phát hiện nó. Trong kiểm thử phần mềm, khó khăn này được
gọi là **oracle problem**: rất khó biết kết quả nào mới là kết quả đúng.

---

## Phần 2. Em đang nghiên cứu tới đâu

| Việc | Trạng thái |
|---|---|
| Tìm tài liệu liên quan (37 tài liệu về kiểm thử, mutation testing, AI sinh test) | Xong |
| Chọn MuTAP làm bài nghiên cứu chính | Xong |
| Đọc và tóm tắt MuTAP: vấn đề, phương pháp, kết quả, hạn chế | Xong (phần 1 ở trên) |
| Xây dựng hệ thống áp dụng ý tưởng của MuTAP cho Python và JavaScript | Xong, chạy được từ đầu đến cuối |
| Thử nghiệm lần 1 với 5 đoạn code Python | Xong |
| Thử nghiệm thêm 2 lần cho Python và 3 lần cho JavaScript | Chưa làm |
| Đọc kỹ lại phần đánh giá của bài để so sánh với kết quả của em | Đang làm |

**Điểm em cần đọc kỹ thêm trong bài:** mutation score được tính trên chính các mutant đã đưa cho AI hay trên một tập
mutant riêng. Nếu là cùng một tập thì điểm có thể cao hơn thực tế, vì AI đã được cho xem trước chính những lỗi đó.

---

## Phần 3. Em áp dụng vào đề tài như thế nào

### 3.1. Những gì em học theo bài

- Không tin ngay test do AI viết: phải **chạy thật và đo thật**.
- Không dừng ở coverage: dùng **mutant còn sống** làm phản hồi để AI viết thêm test.
- Làm theo **vòng lặp**: AI viết test, hệ thống kiểm tra, AI sửa hoặc bổ sung, rồi lặp lại.

### 3.2. Những gì em làm khác hoặc làm thêm

| Nội dung | MuTAP | Đề tài của em |
|---|---|---|
| Dùng mutant còn sống làm phản hồi cho AI | Có | Học theo bài |
| Khi test báo lỗi trên code | Luôn sửa test theo code | AI so với mô tả của hàm: nếu test sai thì sửa test; nếu nghi code sai thì giữ test và đánh dấu "nghi có bug" để người kiểm tra |
| Sửa test không chạy được | Không gửi thông báo lỗi | Gửi kèm thông báo lỗi thật cho AI |
| Kiểm tra phần code chưa được test chạy qua | Không có | Có, làm trước bước mutation |
| Ghi nhớ kinh nghiệm cho lần sau | Không có | Có |
| Cách chấm điểm mutation | (cần đọc kỹ thêm) | Chấm thêm trên những mutant AI chưa từng thấy |
| Ngôn ngữ | Python | Python và JavaScript |

Quy trình của em: AI viết test → hệ thống chạy test → xử lý theo thứ tự ưu tiên:

1. **Test báo lỗi:** nếu test sai thì AI sửa; nếu nghi code sai thì giữ test và đánh dấu "nghi có bug".
2. **Còn code chưa được test:** chỉ cho AI phần còn thiếu để viết thêm test.
3. **Còn mutant sống:** đưa mutant đó cho AI để viết thêm test bắt nó (theo MuTAP).

Hệ thống lặp lại cho đến khi không còn gì cần sửa, rồi trả về bộ test cuối cùng kèm danh sách các test "nghi có bug".

**Ví dụ vì sao điểm khác ở bước "test báo lỗi" lại quan trọng:** mô tả của hàm nói "80 điểm là loại B" nhưng code lại
trả về loại C. MuTAP sẽ sửa test thành "80 điểm là loại C", tức là chấp nhận bug. Cách của em giữ test đúng theo mô tả
và báo "nghi có bug" để người kiểm tra xem lại.

### 3.3. Kết quả ban đầu (lần thử 1, 5 đoạn code Python có cài sẵn 2 bug)

| Tiêu chí | AI viết test 1 lần | AI có vòng lặp tự sửa |
|---|---|---|
| Số test còn báo lỗi chưa rõ nguyên nhân | Trung bình 1,2 test mỗi đoạn code | 0 |
| Số bug được đánh dấu đúng | 0/2 | 2/2, không đánh dấu nhầm |
| Tỉ lệ bắt được mutant mà AI chưa từng thấy | 89,1 % | 91,8 % |

**Nhận xét trung thực:**

- Lợi ích rõ nhất của vòng lặp là xử lý test báo lỗi: vòng lặp phân biệt được test sai với bug thật và đánh dấu đúng
  cả 2 bug.
- Khác với bài MuTAP: ở lần thử này, bước "đưa mutant cho AI" **chưa** làm tăng tỉ lệ bắt những mutant AI chưa từng
  thấy (91,8 % trước và sau bước này).
- Mới thử 1 lần với ít đoạn code nên **chưa đủ để kết luận**.

### 3.4. Việc tiếp theo

1. Thử nghiệm thêm 2 lần cho Python và 3 lần cho JavaScript.
2. So sánh kết quả với bài MuTAP và giải thích những chỗ khác nhau.
3. Viết báo cáo cuối kỳ và chuẩn bị slide bảo vệ.

**Em xin ý kiến thầy:** em chọn MuTAP làm bài nghiên cứu chính và áp dụng như trên có phù hợp không?

---

## Tài liệu tham khảo

1. A. M. Dakhel, A. Nikanjam, V. Majdinasab, F. Khomh, M. C. Desmarais. *Effective Test Generation Using Pre-trained Large
   Language Models and Mutation Testing.* Information and Software Technology, 2024.
   https://doi.org/10.1016/j.infsof.2024.107468 — bản arXiv: https://arxiv.org/abs/2308.16557
2. L. Inozemtseva, R. Holmes. *Coverage Is Not Strongly Correlated with Test Suite Effectiveness.* ICSE 2014.
   https://doi.org/10.1145/2568225.2568271
3. E. T. Barr, M. Harman, P. McMinn, M. Shahbaz, S. Yoo. *The Oracle Problem in Software Testing: A Survey.* IEEE TSE,
   2015. https://doi.org/10.1109/TSE.2014.2372785
