# Báo cáo cuối kỳ (bản nháp)

**Đề tài:** LLM Agent tự sinh unit test đa ngôn ngữ với vòng lặp tự cải tiến dựa trên phản hồi coverage và mutation testing
**Bài nghiên cứu nền tảng:** MuTAP — Dakhel và cộng sự, *Information and Software Technology*, 2024
**Sinh viên:** ……………… · **MSSV:** ……………… · **GVHD:** ………………

> Trạng thái bản nháp: các chương 1–4 và kết quả Python lượt 1 đã có đủ nội dung. Những chỗ ghi **[CHỜ SỐ LIỆU]** chỉ
> được điền sau khi chạy thực nghiệm thật (`python evaluate.py --languages javascript --runs 1`, rồi
> `python evaluate.py --runs 3`). Không điền tay số nào.

---

## Chương 1. Mở đầu

### 1.1. Vấn đề
Viết unit test tốn thời gian nên hay bị bỏ qua. LLM viết test rất nhanh nhưng test có thể:
- không chạy được (sai import, sai cú pháp);
- bỏ sót nhánh hoặc trường hợp biên;
- **sai** — nguy hiểm nhất là test được viết theo code đang sai, làm bug bị "hợp thức hoá".

### 1.2. Câu hỏi nghiên cứu
- **CH1.** Vòng lặp phản hồi thực thi (chạy test, đo coverage) có giúp LLM tạo bộ test chạy được và đúng hơn so với
  sinh một lần không?
- **CH2.** Có phân biệt được "test sai" với "code sai" (oracle problem) khi test fail không?
- **CH3.** Phản hồi mutation testing (theo MuTAP) có giúp bộ test bắt được lỗi **mới**, tức là mutant LLM chưa thấy không?
- **CH4.** Có thể dùng **cùng một vòng lặp** cho nhiều ngôn ngữ mà không viết lại không?

### 1.3. Phạm vi
- 2 ngôn ngữ: Python (5 module) và JavaScript/TypeScript (4 module), có 4 bug cài sẵn (ghi trong `BUGS.md`).
- 1 model LLM miễn phí qua OpenRouter (`nvidia/nemotron-3-super-120b-a12b:free`, giới hạn 50 request/ngày).
- Không dùng LangChain hay framework agent; vòng lặp tự viết.

---

## Chương 2. Cơ sở lý thuyết

| Khái niệm | Ý nghĩa ngắn |
|---|---|
| Unit test, assert | Kiểm tra tự động một hàm: đưa input, so kết quả với giá trị mong đợi |
| Line / branch coverage | Tỉ lệ dòng / nhánh được test chạy qua |
| Coverage chưa đủ | Inozemtseva & Holmes (ICSE 2014): coverage chỉ liên quan yếu đến khả năng phát hiện lỗi |
| Mutant, mutation score | Bản code bị sửa nhẹ một chỗ; điểm = số mutant bị giết / tổng số mutant |
| Oracle problem | Khó biết kết quả nào mới đúng (Barr và cộng sự, IEEE TSE 2015) |
| LLM agent | Chương trình gọi LLM nhiều lần, mỗi lần dựa trên kết quả của lần trước |
| In-context learning | LLM "học" từ ví dụ trong prompt; trọng số không đổi |

Tổng quan 37 tài liệu: `docs/TAI_LIEU_THAM_KHAO.md`.

---

## Chương 3. Bài nghiên cứu nền tảng: MuTAP

Tóm tắt đầy đủ: `docs/BAO_CAO_MUTAP.md`. Các ý chính:

- **Ý tưởng:** mutant còn sống cho LLM biết chính xác bộ test đang bỏ sót lỗi nào → đưa mutant đó vào prompt.
- **Quy trình 6 bước:** sinh test → sửa cú pháp → sửa giá trị mong đợi theo kết quả của code → đo mutation (MutPy) →
  thêm 1 mutant sống vào prompt, lặp → rút gọn bộ test.
- **Kết quả trong bài** (llama-2-chat few-shot): mutation score 93,57 % trên HumanEval (Pynguin 65,94 %); phát hiện
  94,91 % lỗi thật trên Refactory (Pynguin 67,54 %).
- **Hai điểm yếu đồ án nhắm tới:**
  1. Bước sửa giá trị mong đợi giả định code đúng → nếu code có bug, test bị sửa cho khớp bug (oracle problem).
  2. Mutation score được chấm trên chính các mutant đã đưa vào prompt → có thể cao hơn khả năng bắt lỗi mới.

| | MuTAP | Đồ án |
|---|---|---|
| Mutant còn sống làm phản hồi | Có | Kế thừa |
| Test fail trên code | Sửa test cho khớp code | So với đặc tả: test sai → sửa; nghi code sai → giữ test, gắn nhãn `SUSPECTED_BUG` |
| Sửa test hỏng | Không gửi thông báo lỗi | Gửi thông báo lỗi thật |
| Phản hồi coverage | Không | Có, trước bước mutation |
| Chấm mutation | Trên mutant đã đưa vào prompt | Chấm cả hai cách; kết luận dựa trên tập held-out |
| Ngôn ngữ | Python | Python + JavaScript/TypeScript |

---

## Chương 4. Thiết kế và cài đặt hệ thống

### 4.1. Vòng lặp tự cải tiến (`testgen/agent.py`)
1. LLM sinh bộ test ban đầu.
2. Chạy test, đo coverage qua adapter.
3. File lỗi cú pháp/import → LLM sửa cả file (kèm thông báo lỗi).
4. Test fail → LLM phân loại: `TEST_WRONG` thì sửa test; `SUSPECTED_BUG` thì giữ test, gắn `xfail` (Python) hoặc
   `test.failing` (Jest).
5. Coverage dưới ngưỡng → gửi dòng/nhánh chưa phủ.
6. Mutation score dưới ngưỡng → gửi mutant còn sống (ý tưởng của MuTAP).
7. Dừng khi đạt ngưỡng, 2 lần liên tiếp không cải thiện, hoặc hết số vòng.

LLM chỉ trả về test mới hoặc test đã sửa; chương trình tự ghép vào file (Python dùng `ast`, JS dùng bộ quét ngoặc) nên
LLM không xoá được test cũ.

### 4.2. Kiến trúc Adapter (`adapters/`)
Vòng lặp không biết ngôn ngữ; mọi thao tác phụ thuộc ngôn ngữ (chạy test, đo coverage, mutation, ghép test, gắn nhãn)
nằm trong lớp con của `LanguageAdapter`:

| | Python | JavaScript/TypeScript |
|---|---|---|
| Chạy test | pytest | Jest 30 + babel-jest |
| Coverage | coverage.py | Istanbul |
| Mutation | toán tử mutmut 2.5.1 + runner tự viết | StrykerJS 10 |

Refactor từ bản chỉ-Python được kiểm chứng bằng ảnh chụp hành vi (`scripts/snapshot_python.py`): prompt giống từng ký
tự, kết quả chạy test/mutation/agent-mock giống hệt.

### 4.3. Bộ nhớ "tự học" (`testgen/memory.py`)
File JSON lưu bài học sửa lỗi (chỉ lưu khi vòng sau xác nhận) và mẫu test tốt, chia theo ngôn ngữ. Đây là
in-context learning, không huấn luyện lại model.

### 4.4. Giao diện demo
Streamlit (`app.py`): chọn ngôn ngữ/module hoặc dán code, chạy agent trực tiếp hoặc phát lại (REPLAY) từ log.

---

## Chương 5. Thực nghiệm

### 5.1. Thiết lập
- 4 cấu hình: **A** sinh một lần · **B** + phản hồi coverage · **C** B + mutation · **D** C + bộ nhớ.
- A và B lấy từ ảnh chụp trung gian của lần chạy C (ghép cặp) để so sánh công bằng.
- **Phát hiện bug:** có test fail trên code lỗi **và** pass trên bản đã sửa (`evaluation/fixed_targets/`).
- **Mutation held-out:** bỏ các mutant đã đưa vào prompt của C/D, dùng chung tập đó để chấm cả 4 cấu hình.
- Bước SINH tách bước CHẤM (`python evaluate.py --measure-only` chấm lại từ log, không tốn API).

### 5.2. Kết quả Python (lượt 1, 5 module)

| Cấu hình | Line / branch | Mutation held-out | Mutation tất cả | Test fail còn lại | Bug gắn nhãn đúng | Gọi LLM |
|---|---|---|---|---|---|---|
| A | 99,0 / 98,4 % | 89,1 % | 80,7 % | 1,2 / module | 0 / 2 | 1,0 |
| B | 99,0 / 98,4 % | 91,8 % | 83,0 % | 0 | 2 / 2 | 2,4 |
| C | 99,0 / 98,4 % | 91,8 % | 86,0 % | 0 | 2 / 2 | 2,6 |
| D | 99,0 / 98,4 % | 91,8 % | 88,1 % | 0 | 2 / 2 | 3,2 |

Nguồn: `results/results.csv`, `results/runs.csv`. Kết quả **Python lượt 2–3: [CHỜ SỐ LIỆU]**.

### 5.3. Kết quả JavaScript/TypeScript
**[CHỜ SỐ LIỆU]** — chưa có lượt A/B/C/D nào. Hiện chỉ có 2 lần chạy thử agent thật:
- `shipping.ts`: 100/100 % coverage, mutation 90 %, 3 nhãn nghi bug đúng, 0 sai (bắt đúng bug `shippingFee(500)`).
- `bank_account.js`: 96,6/95 % coverage, 8 nhãn đúng, 1 sai; dừng giữa chừng vì hết hạn mức API.

### 5.4. Trả lời câu hỏi nghiên cứu (theo số liệu hiện có)
- **CH1:** Có. Test fail còn lại giảm từ 1,2/module (A) xuống 0 (B–D). Coverage đã bão hoà ngay lần sinh đầu (~99 %)
  nên phản hồi coverage chưa thể hiện được tác dụng trên các module nhỏ này.
- **CH2:** Có, trên tập nhỏ: gắn nhãn đúng 2/2 bug Python, 0 nhãn sai. Baseline A không gắn nhãn được bug nào.
- **CH3:** Chưa thấy. Chấm như MuTAP (tính cả mutant đã đưa vào prompt) thì B → C tăng 83,0 → 86,0 %; chấm held-out
  thì giữ nguyên 91,8 %. Kết quả này khác kết luận của MuTAP; cách chấm là một nguyên nhân có thể.
- **CH4:** Có về mặt kỹ thuật: thêm JS không sửa logic của vòng lặp. So sánh định lượng giữa hai ngôn ngữ
  **[CHỜ SỐ LIỆU]**.

---

## Chương 6. Hạn chế và hướng phát triển

**Hạn chế**
- Thực nghiệm nhỏ: Python 1 lượt (đề yêu cầu 3), JS chưa có lượt A/B/C/D; 1 model; 9 module tự viết. Chưa có ý nghĩa
  thống kê.
- Công cụ đo khác nhau giữa hai ngôn ngữ nên so sánh chéo chỉ tương đối.
- LLM có thể phân loại sai; test tối ưu theo mutation có thể bám chi tiết cài đặt (ví dụ đọc `withdrawnToday`).
- Phụ thuộc docstring/JSDoc làm đặc tả. Chạy code người dùng dán vào không phải sandbox bảo mật.

**Hướng phát triển**
- Chạy đủ thực nghiệm; thử trên HumanEval để so sánh trực tiếp với số liệu của MuTAP.
- Thêm Java (JUnit 5 + JaCoCo + PIT, đã phác thảo trong `docs/THEM_NGON_NGU_MOI.md`), Go.
- Thêm bước rút gọn bộ test như MuTAP.

---

## Chương 7. Kết luận
Đồ án xây dựng được agent sinh → chạy → đo → sửa/bổ sung cho Python và JavaScript/TypeScript, kế thừa ý tưởng phản
hồi mutation của MuTAP. Đóng góp chính so với MuTAP là không mặc định code đúng (giữ lại test phát hiện bug) và chấm
mutation trên mutant LLM chưa thấy. Với số liệu hiện có, lợi ích rõ nhất là xử lý test fail; lợi ích của phản hồi
mutation trên lỗi mới chưa được xác nhận.

---

## Tài liệu tham khảo
1. A. M. Dakhel, A. Nikanjam, V. Majdinasab, F. Khomh, M. C. Desmarais. *Effective Test Generation Using Pre-trained Large
   Language Models and Mutation Testing.* Information and Software Technology, 2024. https://doi.org/10.1016/j.infsof.2024.107468
2. L. Inozemtseva, R. Holmes. *Coverage Is Not Strongly Correlated with Test Suite Effectiveness.* ICSE 2014.
   https://doi.org/10.1145/2568225.2568271
3. E. T. Barr, M. Harman, P. McMinn, M. Shahbaz, S. Yoo. *The Oracle Problem in Software Testing: A Survey.* IEEE TSE, 2015.
   https://doi.org/10.1109/TSE.2014.2372785
4. Các tài liệu còn lại: `docs/TAI_LIEU_THAM_KHAO.md`.
