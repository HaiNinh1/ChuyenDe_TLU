# Tài liệu đọc khi thuyết trình — Buổi giới thiệu đề tài

Đi kèm bộ slide 10 trang: https://claude.ai/artifact/TWrhnLMKch4dJswM6z7UxQ

Tài liệu gồm 4 phần:

1. **Hiểu đề tài trong 5 phút.** Đọc trước ở nhà để tự hiểu mình đang làm gì.
2. **Một ví dụ xuyên suốt.** Theo một bug cụ thể đi qua toàn bộ hệ thống.
3. **Lời nói theo từng slide.** Đọc hoặc nói theo khi trình bày.
4. **Từ khoá và câu hỏi thầy có thể hỏi.**

---

## PHẦN 1 — Hiểu đề tài trong 5 phút

### Đề tài nói gì, bằng một câu

> Em làm một chương trình dùng AI (LLM, như ChatGPT) để **tự viết test** cho code. Chương trình không tin ngay
> test do AI viết mà **chạy thử, đo xem test tốt đến đâu, rồi bắt AI sửa**, lặp lại nhiều lần cho đến khi bộ test đủ tốt.

### Test là gì?

Lập trình viên viết một hàm, ví dụ hàm **xếp loại điểm**: nhận vào điểm số, trả về chữ A, B, C…
Viết **test** cho hàm đó nghĩa là viết thêm một đoạn nhỏ để tự động kiểm tra:

> "Gọi hàm với điểm 85 thì **phải** ra chữ B. Nếu không ra B thì báo lỗi."

Mỗi test có 3 phần: **dữ liệu vào** (85), **lời gọi hàm**, và **kết quả mong đợi** (B).
Viết test bằng tay tốn nhiều thời gian nên người ta muốn máy **tự sinh test**.

### Tại sao không để AI viết test là xong?

AI viết test rất nhanh, nhưng hay mắc 3 lỗi:

| Lỗi | Hiểu đơn giản |
|---|---|
| Test **không chạy được** | Giống bài làm bị lỗi chính tả nặng đến mức máy không đọc được |
| Test **chưa đầy đủ** | Chỉ kiểm tra điểm 85, quên kiểm tra các điểm "sát ranh giới" như 80 hay 90 |
| Test **"hợp thức hoá" bug** | Nguy hiểm nhất, xem giải thích bên dưới |

**"Hợp thức hoá" bug** nghĩa là gì? Giả sử hàm có bug: điểm 80 lẽ ra là B nhưng hàm lại trả về C.
AI đọc code rồi viết test "80 thì phải ra C". Test này **chạy qua (pass)**, nên mọi người tưởng code đúng, và
bug bị giấu đi. Tức là AI đã **chép lại cái sai** của code vào test.
Hiện tượng này đã có nghiên cứu đặt tên là **misguidance effect**, nghĩa là code sai "dẫn dắt sai" AI.

### Em giải quyết thế nào? (ý tưởng chính)

Thay vì tin AI ngay, chương trình của em làm như **một giáo viên chấm bài rồi bắt làm lại**:

```
 1. AI viết bộ test
 2. Chương trình CHẠY bộ test và ĐO chất lượng
 3. Chương trình chỉ ra chỗ còn yếu (phản hồi)
 4. AI dựa vào phản hồi để sửa / viết thêm
 → quay lại bước 2, lặp đến khi đủ tốt hoặc không cải thiện được nữa
```

Chương trình **đo chất lượng test** bằng 2 cách. Đây là 2 khái niệm lý thuyết chính của đề tài.

**(1) Độ phủ mã (coverage): test đã "đi qua" những chỗ nào của code?**
Hình dung: bảo vệ đi tuần một toà nhà. Coverage là tỉ lệ số phòng bảo vệ đã đi qua. Phòng nào chưa đi qua thì
chắc chắn chưa được kiểm tra.
Nhưng **đi qua chưa chắc đã kiểm tra kỹ**: bảo vệ có thể đi ngang phòng mà không nhìn vào. Nên coverage cao vẫn
chưa đủ để nói test tốt.

**(2) Kiểm thử đột biến (mutation testing): test có đủ "tinh mắt" để phát hiện lỗi không?**
Hình dung: muốn biết camera an ninh có tốt không, ta **cho người giả đột nhập** xem camera có phát hiện ra không.
Mutation testing làm tương tự: **cố tình cài một lỗi nhỏ** vào code (ví dụ đổi "lớn hơn hoặc bằng" thành
"lớn hơn"), rồi chạy bộ test:

- Test phát hiện ra (có test báo lỗi) thì lỗi giả đó **"bị giết"**. Tốt.
- Test không phát hiện (mọi test vẫn pass) thì lỗi giả **"sống sót"**. Nghĩa là bộ test còn lỗ hổng đúng ở chỗ đó.

Tỉ lệ lỗi giả bị phát hiện gọi là **mutation score**. Các lỗi giả còn sống sót được gửi cho AI để nó viết thêm
test ở đúng chỗ đó.

**(3) Bài toán oracle: khi test báo lỗi, ai sai, test hay code?**
"Oracle" nghĩa là **đáp án**, tức là cái để biết kết quả đúng là gì. Khi một test báo lỗi, có 2 khả năng:

- **Test sai**, tức AI viết nhầm kết quả mong đợi. Khi đó sửa test.
- **Code sai**, tức code thật có bug. Khi đó **phải giữ test lại** và báo cho người xem, không được sửa test cho pass.

Đồ án cho AI **đối chiếu với mô tả của hàm** (tài liệu ghi hàm phải làm gì) để phân loại. Con người là người
xác nhận cuối cùng. Đây chính là cách chống lại lỗi "hợp thức hoá bug" ở trên.

**(4) LLM agent: AI biết tự làm nhiều bước**
"Agent" là AI không chỉ trả lời một lần, mà **làm, xem kết quả, rồi làm tiếp**, giống sinh viên làm bài tập lập
trình: viết code, chạy thử, đọc lỗi, sửa lại. Có một "bộ nhớ" ghi lại bài học (ví dụ "lần trước viết sai kiểu này")
để lần sau đưa vào câu hỏi gửi AI.
Lưu ý: AI **không được huấn luyện lại**, nó chỉ được "nhắc bài" trong câu hỏi. Cách này gọi là **học trong ngữ cảnh**.

### Còn "đa ngôn ngữ" là gì?

Mỗi ngôn ngữ lập trình có bộ công cụ chạy test và đo riêng: Python dùng một bộ, JavaScript dùng bộ khác.
Em thiết kế sao cho **vòng lặp ở trên dùng chung**, còn phần "chạy test, đo" của mỗi ngôn ngữ nằm ở một khối riêng,
giống như **ổ cắm chuyển đổi (adapter)**: cùng một phích cắm (vòng lặp), mỗi nước (ngôn ngữ) một đầu chuyển.
Trong lập trình, cách thiết kế này gọi là **mẫu thiết kế Adapter**. Hiện đã làm được cho **Python** và
**JavaScript/TypeScript**. Java và Go là hướng phát triển.

### Làm sao biết cách này có hiệu quả?

Em tự viết mấy chương trình mẫu và **cố tình cài sẵn 4 bug đã biết** (bug được ghi riêng, AI không được xem).
Em cũng giữ một bản **đã sửa bug**. Một bug được tính là "phát hiện được" khi có test **báo lỗi trên bản có bug**
nhưng **chạy đúng trên bản đã sửa**.

Để biết mỗi phần đóng góp bao nhiêu, em so sánh 4 cách chạy (4 cấu hình), từ đơn giản đến đầy đủ:

| Cấu hình | Làm gì |
|---|---|
| A | AI viết test **một lần**, không kiểm tra lại |
| B | A + vòng lặp có phản hồi **coverage** (và sửa test lỗi) |
| C | B + phản hồi **mutation** |
| D | C + **bộ nhớ** kinh nghiệm |

---

## PHẦN 2 — Một ví dụ xuyên suốt (nên đọc kỹ)

Hàm **xếp loại điểm**. Mô tả của hàm ghi: *"80 đến dưới 90 điểm là B"*.
Nhưng code bị cài bug: nó dùng điều kiện "lớn hơn 80" thay vì "lớn hơn hoặc bằng 80". Vì vậy **đúng 80 điểm lại bị
xếp C**.

1. **AI viết test lần đầu.** AI viết test cho 95 (A), 85 (B), 70 (C)… Có thể có một test "80 thì ra B".
2. **Chạy và đo.** Test "80 ra B" **báo lỗi** vì code trả về C. Coverage đã cao, gần như mọi dòng đều được chạy.
3. **Bài toán oracle.** Test báo lỗi, vậy test sai hay code sai? AI đối chiếu với mô tả ("80 đến dưới 90 là B")
   và kết luận: **code sai**. Chương trình **giữ nguyên test** và gắn nhãn *"nghi có bug"* để người xem xác nhận.
   Nếu không có bước này, cách làm ngây thơ sẽ sửa test thành "80 ra C" cho pass, tức là che mất bug.
4. **Mutation.** Chương trình cài lỗi giả, ví dụ đổi "lớn hơn hoặc bằng 90" thành "lớn hơn 90". Nếu không có test
   nào thử đúng 90 điểm thì lỗi giả này sống sót. Chương trình báo cho AI, AI viết thêm test "90 thì ra A".
5. **Chấm.** Test "80 ra B" báo lỗi trên bản có bug và chạy đúng trên bản đã sửa, nên **bug được phát hiện**.

Ví dụ này cũng cho thấy vì sao **coverage không đủ**: test 85 điểm đã "đi qua" nhánh B, coverage cao,
nhưng vẫn không lộ ra bug ở đúng 80 điểm.

---

## PHẦN 3 — Lời nói theo từng slide (~10 phút, mỗi slide ~1 phút)

> Mẹo: không cần đọc thuộc. Mỗi slide nhớ **một câu chốt** (in đậm ở đầu), còn lại nói theo ý.

### Slide 1 — Bìa
**Câu chốt:** Em làm AI tự viết test, và tự sửa test dựa trên việc đo chất lượng.

"Em chào thầy. Em xin giới thiệu đề tài: xây dựng một LLM Agent, tức là một chương trình dùng mô hình ngôn ngữ
lớn như ChatGPT, để tự sinh unit test cho nhiều ngôn ngữ lập trình. Điểm chính là chương trình có vòng lặp tự cải
tiến: nó chạy thử test, đo chất lượng bằng coverage và mutation testing, rồi dùng kết quả đo để bắt AI sửa lại.
Em sẽ trình bày vấn đề, cơ sở lý thuyết, hướng giải quyết và hiện trạng."

### Slide 2 — Kiểm thử đơn vị và sinh test tự động
**Câu chốt:** Sinh test tự động đã có từ lâu. LLM là thế hệ mới nhất nhưng chưa đảm bảo test đúng.

"Unit test là đoạn code kiểm tra một hàm hay một lớp nhỏ. Mỗi test có dữ liệu vào, lời gọi hàm và kết quả mong
đợi. Viết tay tốn công nên đã có nhiều thế hệ công cụ tự sinh test.
Thế hệ đầu, khoảng 2007, là sinh ngẫu nhiên, ví dụ Randoop. Thế hệ hai là dùng thuật toán tìm kiếm, tiến hoá, như
EvoSuite cho Java và Pynguin cho Python, để đạt độ phủ cao. Nhưng các công cụ này lấy chính kết quả hiện tại của
code làm kết quả mong đợi, nên nếu code sai thì test cũng sai theo. Ngoài ra mỗi công cụ chỉ dùng cho một ngôn ngữ.
Từ 2023 có hướng dùng LLM: AI đọc được code và mô tả nên viết test giống người viết. Nhưng không có gì đảm bảo test
AI viết là đúng."

### Slide 3 — Vấn đề
**Câu chốt:** AI có thể chép lại cái sai của code vào test, làm bug bị che đi.

"Test do AI viết có ba vấn đề. Một, có thể không chạy được. Hai, có thể chưa đầy đủ, ví dụ quên thử các giá trị
sát ranh giới. Ba, nguy hiểm nhất, là hợp thức hoá bug. Ví dụ hàm xếp loại có bug làm 80 điểm ra C thay vì B.
AI nhìn code rồi viết test '80 ra C'. Test pass và bug bị giấu đi. Hiện tượng này đã được nghiên cứu, gọi là
misguidance effect.
Từ đó em đặt câu hỏi: làm sao để AI tự kiểm tra và cải thiện bộ test của nó, và cách làm dùng được cho nhiều
ngôn ngữ. Để trả lời, em dựa trên bốn khái niệm lý thuyết ở các slide sau."

### Slide 4 — Bài toán oracle
**Câu chốt:** Khi test báo lỗi, phải biết lỗi ở test hay ở code. Nếu lỗi ở code thì phải giữ test lại.

"Khái niệm thứ nhất là test oracle, tức là cái cho biết kết quả đúng là gì, cũng là nguồn của kết quả mong đợi.
Oracle problem là bài toán kinh điển: với phần mềm thật, rất khó tự động biết thế nào là đúng. Bài khảo sát của
Barr và cộng sự năm 2015 kết luận con người vẫn là nguồn đáp án cuối cùng.
Trong đồ án, bài toán này xuất hiện mỗi khi test báo lỗi. Nếu test sai thì sửa test. Nếu code sai thì phải giữ
test và báo nghi có bug, vì sửa test cho pass chính là che bug. Em cho AI đối chiếu với mô tả của hàm để phân
loại, còn con người xác nhận."

### Slide 5 — Độ phủ mã
**Câu chốt:** Coverage cho biết chỗ nào chưa được test, nhưng coverage cao chưa chắc test tốt.

"Khái niệm thứ hai là độ phủ mã. Line coverage là tỉ lệ dòng code được chạy khi chạy test. Branch coverage là
tỉ lệ nhánh rẽ được đi qua. Ví dụ điều kiện 'điểm lớn hơn hoặc bằng 50' có hai nhánh là đậu và trượt. Nếu chỉ thử
với 70 điểm thì mới đi một nhánh, tức branch coverage 50%.
Hạn chế là coverage chỉ nói code đã được chạy, không nói kết quả có được kiểm tra. Nghiên cứu của Inozemtseva và
Holmes năm 2014 trên 31 nghìn bộ test cho thấy coverage chỉ tương quan thấp đến vừa với khả năng phát hiện lỗi.
Vì vậy em dùng coverage để tìm vùng chưa được test, chứ không coi đó là thước đo chất lượng duy nhất."

### Slide 6 — Kiểm thử đột biến
**Câu chốt:** Cố tình cài lỗi giả để xem bộ test có phát hiện được không.

"Khái niệm thứ ba là kiểm thử đột biến. Ta cố tình sửa nhỏ code, ví dụ đổi 'lớn hơn hoặc bằng' thành 'lớn hơn',
tạo ra một mutant. Sau đó chạy bộ test. Nếu có test báo lỗi thì mutant bị giết, tức bộ test phát hiện được lỗi
này. Nếu mọi test vẫn pass thì mutant sống sót, tức bộ test còn lỗ hổng đúng ở chỗ đó. Mutation score là tỉ lệ
mutant bị giết.
Tại sao lỗi giả lại nói được gì về lỗi thật? Có hai giả thuyết từ bài gốc năm 1978 của DeMillo. Một là lập trình
viên giỏi thường chỉ sai lệch nhỏ. Hai là hiệu ứng ghép cặp: test bắt được lỗi đơn giản thì cũng bắt được phần lớn
lỗi phức tạp. Nghiên cứu của Just và cộng sự năm 2014 cho thấy phát hiện mutant tương quan với phát hiện lỗi thật.
Trong đồ án, các mutant sống sót là gợi ý rất cụ thể để AI biết cần viết thêm test gì."

### Slide 7 — LLM agent và học từ phản hồi
**Câu chốt:** Agent là AI làm việc theo vòng: hành động, nhận kết quả thật, rồi quyết định bước tiếp.

"Khái niệm thứ tư là LLM agent. Agent gồm AI, công cụ, và một vòng lặp. AI quyết định làm gì, công cụ thực hiện và
trả kết quả thật, AI dựa vào đó làm bước tiếp. Một số công trình nền tảng: ReAct xen kẽ suy nghĩ và hành động.
Self-Refine cho AI tự nhận xét rồi sửa. Self-Debug cho AI chạy code, đọc lỗi rồi sửa. Reflexion ghi bài học vào
bộ nhớ để dùng lần sau.
'Học' ở đây là học trong ngữ cảnh: mô hình không được huấn luyện lại, chỉ được nhắc kinh nghiệm trong câu hỏi.
Khác biệt của đồ án là phản hồi đến từ công cụ đo thật, gồm kết quả chạy test, coverage và mutation, chứ không phải
AI tự chấm mình, nên khách quan hơn."

### Slide 8 — Hướng giải quyết: vòng lặp tự cải tiến
**Câu chốt:** Ghép 4 khái niệm lại thành một vòng lặp: sinh, đo, phản hồi, cải tiến.

"Ghép bốn khái niệm trên lại, em có vòng lặp bốn bước. Một, AI đọc code và mô tả, viết bộ test. Hai, chạy test và
đo coverage, mutation. Ba, rút ra phản hồi: test nào lỗi, chỗ nào chưa phủ, mutant nào sống sót. Bốn, AI sửa hoặc
viết thêm. Rồi quay lại bước hai, đến khi đạt ngưỡng hoặc không cải thiện nữa.
Bốn loại phản hồi ứng với bốn phần lý thuyết. Test không chạy được thì AI tự sửa, theo ý tưởng Self-Debug. Chỗ
chưa phủ thì viết thêm test. Mutant sống sót thì viết test chặt hơn. Test báo lỗi thì phân loại theo bài toán
oracle, và nếu nghi code có bug thì giữ test lại. Bài học mỗi lần được ghi vào bộ nhớ, giống Reflexion."

### Slide 9 — Mục tiêu và phạm vi
**Câu chốt:** 3 mục tiêu: vòng lặp tự cải tiến, xử lý oracle, đánh giá bằng thực nghiệm. Làm cho 2 ngôn ngữ.

"Đồ án có ba mục tiêu. Một, xây dựng agent sinh test có vòng lặp tự cải tiến. Hai, giải quyết một phần bài toán
oracle: phân biệt test sai và code sai dựa trên mô tả. Ba, đánh giá bằng thực nghiệm: so sánh bốn cấu hình, từ AI
viết một lần đến có đủ coverage, mutation và bộ nhớ, để biết mỗi phần đóng góp bao nhiêu và tốn thêm bao nhiêu lần
gọi AI.
Về phạm vi, vì mỗi ngôn ngữ có công cụ riêng, em tách vòng lặp chung khỏi phần riêng của từng ngôn ngữ theo mẫu
thiết kế Adapter. Hiện làm cho Python và JavaScript/TypeScript. Dữ liệu thử là các chương trình mẫu có cài sẵn bug
đã biết, để chấm khách quan. Java và Go là hướng phát triển."

### Slide 10 — Hiện trạng, kế hoạch, xin ý kiến
**Câu chốt:** Đã có bản chạy thử và kết quả ban đầu. Cần chạy thực nghiệm đầy đủ. Em xin thầy góp ý.

"Hiện em đã tìm hiểu cơ sở lý thuyết qua 37 tài liệu, đã có bản chạy thử cho Python và JavaScript/TypeScript, và
đã chạy thực nghiệm ban đầu trên Python. Kết quả ban đầu cho thấy vòng lặp giúp loại bỏ test sai và giữ lại test
phát hiện bug. Nhưng mới chạy một lượt trên ít chương trình nên em chưa kết luận.
Tiếp theo em sẽ chạy thực nghiệm đầy đủ, nhiều lượt, cho cả hai ngôn ngữ, so sánh với công cụ có sẵn và viết báo
cáo. Em mong thầy góp ý ba điểm: phạm vi hai ngôn ngữ có phù hợp không, dữ liệu thử đã đủ chưa, và tiêu chí đánh
giá đã hợp lý chưa. Em xin cảm ơn thầy."

---

## PHẦN 4 — Từ khoá và câu hỏi thầy có thể hỏi

### Bảng từ khoá (nói tiếng Việt thế nào)

| Thuật ngữ | Nghĩa ngắn gọn |
|---|---|
| Unit test | Test kiểm tra một hàm/lớp nhỏ |
| Assert | Câu lệnh "kết quả phải bằng…" trong test |
| Pass / Fail | Test chạy đúng / test báo lỗi |
| LLM | Mô hình ngôn ngữ lớn (ChatGPT, Claude…) |
| Agent | AI làm nhiều bước: hành động, xem kết quả, làm tiếp |
| Prompt | Câu hỏi / yêu cầu gửi cho AI |
| Coverage (line / branch) | Tỉ lệ dòng / nhánh code được chạy khi chạy test |
| Mutant | Bản code bị cố tình sửa nhỏ để tạo lỗi giả |
| Mutant bị giết / sống sót | Test phát hiện / không phát hiện được lỗi giả |
| Mutation score | Tỉ lệ mutant bị giết |
| Test oracle | "Đáp án", tức cái cho biết kết quả đúng là gì |
| Oracle problem | Bài toán khó biết đáp án đúng khi kiểm thử |
| Misguidance effect | Code sai dẫn dắt AI viết test sai theo |
| Học trong ngữ cảnh | AI không học lại, chỉ được nhắc kinh nghiệm trong prompt |
| Adapter | Mẫu thiết kế "đầu chuyển": phần chung dùng lại, phần riêng thay theo ngôn ngữ |

### Câu hỏi thầy có thể hỏi và gợi ý trả lời

**1. Đề tài khác gì so với việc hỏi ChatGPT "viết test cho hàm này"?**
Hỏi ChatGPT là cấu hình A, tức viết một lần và không kiểm tra. Đồ án thêm vòng lặp: chạy thử, đo coverage và
mutation, phân loại test lỗi, rồi bắt AI sửa. Phản hồi đến từ việc chạy thật chứ không phải AI tự đánh giá.

**2. Tại sao cần mutation khi đã có coverage?**
Coverage chỉ cho biết code đã được chạy, không cho biết kết quả có được kiểm tra. Test 85 điểm đi qua nhánh B nhưng
không phát hiện được bug ở đúng 80 điểm. Mutation kiểm tra test có phát hiện được lỗi hay không.

**3. Làm sao biết AI phân loại "test sai hay code sai" là đúng?**
Không chắc chắn 100%, vì đây là bài toán oracle chưa có lời giải tổng quát. Vì vậy AI chỉ đề xuất, test nghi bug
được giữ lại và gắn nhãn để người xác nhận. Khi đánh giá, em chấm khách quan bằng bản code đã sửa bug mà AI không
được xem.

**4. Agent có "học" thật không, có huấn luyện lại mô hình không?**
Không huấn luyện lại. Đây là học trong ngữ cảnh: bài học được ghi vào một file bộ nhớ và đưa vào prompt lần sau,
giống Reflexion.

**5. Tại sao làm 2 ngôn ngữ mà không đi sâu một ngôn ngữ?**
Để kiểm chứng rằng vòng lặp thật sự tách được khỏi ngôn ngữ, đúng như mẫu Adapter hứa hẹn. Nếu chỉ làm một ngôn ngữ
thì không chứng minh được điều đó. Đây cũng là điểm em muốn xin ý kiến thầy.

**6. Kết quả hiện tại thế nào?** (chỉ nói nếu thầy hỏi, và nói rõ là mới 1 lượt)
Trên Python, 5 chương trình, chạy 1 lượt: cách viết một lần (A) còn trung bình khoảng 1 test lỗi mỗi chương trình và
không gắn nhãn được bug nào. Có vòng lặp (B, C, D) thì không còn test lỗi, và cả 2 bug Python đều được gắn nhãn nghi
bug đúng. Coverage đã rất cao ngay từ lần đầu (khoảng 99%). Phản hồi mutation chưa cho thấy cải thiện rõ trên các lỗi
giả mới. Đổi lại, số lần gọi AI tăng từ 1 lên khoảng 2 đến 3 lần. Phần JavaScript mới chạy thử, chưa có số liệu đầy
đủ. Em chưa kết luận vì mới có một lượt.

**7. Vì sao không dùng LangChain hay framework agent có sẵn?**
Vòng lặp không phức tạp nên em tự viết để hiểu rõ và kiểm soát từng bước. Bài "Building Effective Agents" của
Anthropic cũng khuyên nên dùng các mẫu đơn giản thay vì framework phức tạp.

**8. Hạn chế của đề tài?**
Mới làm 2 ngôn ngữ, và thực nghiệm còn nhỏ, trên chương trình mẫu tự viết. AI vẫn có thể phân loại sai. Công cụ đo
của mỗi ngôn ngữ khác nhau nên so sánh giữa hai ngôn ngữ chỉ mang tính tương đối. Dùng AI thì tốn nhiều lần gọi
hơn so với viết một lần.
