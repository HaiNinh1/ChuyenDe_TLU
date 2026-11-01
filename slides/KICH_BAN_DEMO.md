# Kịch bản demo: vừa chạy vừa giải thích theo nghiên cứu

Thời lượng chiếu khoảng 3 phút 45. Mạch trình bày: nhắc lại MuTAP, chỉ ra vấn đề, rồi dùng sản phẩm cho thấy cách giải quyết.

Mỗi bước có hai phần: **Nói** là phần nói khi chiếu, **Giải thích đầy đủ** là phần dùng khi thầy hỏi sâu hoặc khi còn thời gian. Thuật ngữ nằm ở cuối file.

| Bước | Màn hình | So với MuTAP | Câu hỏi nghiên cứu | Thời gian |
|---|---|---|---|---|
| 1 | Nhắc lại MuTAP | | | 1 phút |
| 2 | Chạy thật `ticket_price` | **Đổi:** test fail thì so với đặc tả | CH1, CH2 | 1 phút 45 |
| 3 | REPLAY `calculator_agent_mutation` | **Giữ:** mutant còn sống làm phản hồi | CH3 | 30 giây |
| 4 | REPLAY `shipping_agent_js` | **Thêm:** coverage, ngôn ngữ thứ hai | CH4 | 30 giây |
| 5 | Sang slide 21, không chiếu trong demo | **Đổi:** chấm trên tập held-out | CH3 | Nói ở slide 22–24 |

## Chuẩn bị trước khi vào phòng

1. Nhấn đúp `run_demo.bat`, đợi trình duyệt mở `http://localhost:8501`.
2. Ở thanh bên, chọn **Chế độ: Chạy mới → Mã nguồn: Dán code**. Kéo **Số vòng tối đa** lên **8** cho khớp slide.
3. Copy sẵn đoạn code ở bước 2.

---

## Bước 1. Nhắc lại MuTAP (1 phút, chưa thao tác)

**Nói:**

> Thưa thầy, đề tài của em dựa trên bài MuTAP của Dakhel và cộng sự, năm 2024. Vấn đề của bài là test do LLM viết thường chỉ được đánh giá bằng coverage, trong khi coverage cao chưa chắc đã bắt được lỗi.
>
> Ý tưởng chính của MuTAP là đưa mutant còn sống vào prompt, tức là nói với LLM rằng bộ test chưa phát hiện được lỗi này, để LLM viết đúng test còn thiếu.
>
> Khi đọc kỹ, em thấy hai điểm cần xem xét. Một là bước 3 sửa giá trị mong đợi theo kết quả của code, tức là mặc định code đúng. Nếu code có bug, test đúng sẽ bị sửa thành test sai. Hai là điểm số được chấm trên chính danh sách mutant đã lấy để đưa vào prompt, nên có thể cao hơn khả năng bắt lỗi mới. Đây là nhận xét của em khi đọc bài, em không nói kết quả của bài là sai.
>
> Vì vậy, em giữ ý tưởng dùng mutant làm phản hồi, đổi hai điểm vừa nêu, và thêm phản hồi coverage cùng ngôn ngữ thứ hai. Hệ thống của em là một vòng lặp: LLM viết test, chạy test thật, đo kết quả, rồi tạo phản hồi cho vòng sau. Mỗi vòng chỉ xử lý vấn đề ưu tiên nhất: file test hỏng, rồi test fail, rồi coverage, cuối cùng là mutant còn sống. Dòng in đậm trên mỗi thẻ cho biết vòng đó đang xử lý vấn đề gì.

**Giải thích đầy đủ:**

- **Sáu bước của MuTAP:** (1) LLM sinh test; (2) sửa lỗi cú pháp, tối đa 10 lần; (3) sửa giá trị mong đợi theo kết quả của code; (4) tạo mutant bằng MutPy và tính điểm; (5) đưa mutant còn sống vào prompt, lặp lại bước 4–5 đến khi đạt 100 % hoặc hết mutant sống; (6) rút gọn bộ test.
- **Kết quả trong bài (em không chạy lại):** HumanEval: MuTAP 93,57 %, Pynguin 65,94 %. Refactory: MuTAP phát hiện 94,91 % lỗi thật của sinh viên, Pynguin 67,54 %.
- **Vì sao nói bước 3 mặc định code đúng:** Giả sử đặc tả ghi 80 điểm là B, LLM viết đúng là B, nhưng code có bug trả C. Bước 3 sẽ sửa test thành C, nên test mất khả năng bắt chính bug đó.
- **Vì sao cách chấm đáng xem xét:** Giống cho học sinh xem trước đề rồi chấm đúng đề đó. Kết quả trên Refactory không bị ảnh hưởng, vì lỗi thật không được đưa vào prompt.
- **Ai làm việc gì trong vòng lặp:** LLM viết, sửa và phân loại test. Công cụ thật chạy test và đo điểm. Code của em chọn việc tiếp theo bằng `for` và `if/else`, không dùng LangChain. Vì vậy LLM không tự chấm điểm mình.
- **Vì sao xử lý test fail trước coverage:** Coverage của một bộ test đang fail thì không đáng tin.

---

## Bước 2. Chạy thật: test sai hay code sai? (1 phút 45)

**Mục đích:** cho thấy điểm đổi thứ nhất so với MuTAP. Đây là phần chính của demo.

**Thao tác 1:** Dán đoạn code sau vào ô **"Dán code"** ở thanh bên trái, rồi **bấm ra ngoài ô**. Chưa bấm chạy. Mở tab **📄 Mã nguồn module** để code hiện to hơn.

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

**Nói (chỉ dòng 7–8 và dòng 16):**

> Đây là đoạn code em tự viết cho buổi demo. Đặc tả ghi từ 60 tuổi trở lên giá 70000. Thầy có thấy lỗi trong code không?

**Thao tác 2:** Bấm **▶️ Chạy agent**, rồi mở tab **🔄 Tiến trình**. Ba lần chạy gần nhất mất 21, 34 và 51 giây. Vừa chờ vừa nói:

> Đầu tiên, LLM đọc code và đặc tả để sinh bộ test, giống như MuTAP. Sau đó agent chạy test thật bằng pytest và đo coverage.

**Thao tác 3:** Khi thẻ **Vòng 0** hiện ra, chỉ vào ô coverage và dòng **🧪 Phân loại & sửa test fail**.

> Coverage ở đây là [đọc số], nhưng vẫn có test fail. Nếu chỉ nhìn coverage, em không biết có lỗi này.
>
> Đến đây có hai khả năng: LLM viết sai test, hoặc code sai. MuTAP mặc định code đúng và sẽ sửa test thành 100000, như vậy bug bị giấu đi. Agent của em yêu cầu LLM so test với đặc tả. Dòng có biểu tượng con bọ là kết luận của LLM: nghi code sai, kèm lý do.

**Thao tác 4:** Chỉ vào thẻ **Vòng 1** và dòng **⏹️ Dừng**.

> Agent giữ test và gắn nhãn, nên không còn test fail nhưng lỗi vẫn được báo. Mutation score đã đạt ngưỡng 80 % nên agent dừng, vòng này không cần viết thêm test.

**Thao tác 5:** Mở tab **🧾 Code test**, chỉ phần **tô đỏ**.

> Test này vẫn khẳng định `ticket_price(60)` phải là 70000, đúng theo đặc tả. Em chỉ gắn nhãn nghi có bug để người kiểm tra xem lại, vì LLM vẫn có thể phân loại sai. Trường hợp LLM viết sai test thì agent sửa test, như log em đã trình bày ở trang 18.

**Giải thích đầy đủ:**

| Thời điểm | Chuyện gì xảy ra | Vì sao |
|---|---|---|
| Trước vòng 0 | **Gọi LLM lần 1:** sinh bộ test | Prompt yêu cầu viết assert theo đặc tả |
| Vòng 0 | pytest chạy: 9 pass, 1 fail; coverage 100 % | Test `ticket_price(60) == 70000` fail vì code trả 100000 |
| Vòng 0 | Ô Mutation hiện "—" | Còn test fail nên chưa tới bước mutation |
| Vòng 0 | **Gọi LLM lần 2:** phân loại, kết quả SUSPECTED_BUG | Đặc tả ghi rõ, code vi phạm |
| Vòng 0 | Chương trình gắn `xfail`, không gọi thêm LLM | Không có test sai nên không cần sửa |
| Vòng 1 | pytest chạy: 9 pass, 0 fail, 1 nhãn | Test có nhãn được tính là dự kiến fail |
| Vòng 1 | Mutation: 11/13 mutant bị giết = 84,6 % | Coverage đã đạt nên chuyển sang mutation |
| Vòng 1 | ⏹️ Dừng | 84,6 % ≥ ngưỡng 80 % |

Đây là số của lần chạy 31/10. Số test mỗi lần có thể khác (lần chạy 1/11 lúc 10:46 có 10 pass thay vì 9), nên hãy đọc số trên màn hình.

- **Hai mutant còn sống:** một mutant đổi nội dung thông báo lỗi, một mutant đổi `age <= 60` thành `age < 60`. Mutant thứ hai chính là cách sửa bug, nên không thể giết nó bằng test đúng đặc tả.
- **Sao LLM biết code sai:** LLM nhận mã nguồn, đặc tả, test đang fail và thông báo lỗi. Prompt yêu cầu chỉ chọn SUSPECTED_BUG khi đặc tả nói rõ và code vi phạm (`testgen/prompts.py:87`).
- **Nếu LLM cho là test sai:** agent nhờ LLM sửa đúng test đó. Sửa quá 2 lần vẫn không được thì xóa test (`testgen/agent.py:239`).

**Nếu kết quả khác dự kiến:**
- **LLM không bắt được lỗi hoặc phân loại sai:** "Đây là hạn chế em đã nêu: LLM không phải lúc nào cũng đúng, nên nhãn chỉ là nghi ngờ. Em phát lại lần chạy đã ghi log để thầy xem trường hợp bắt được."
- **API lỗi hoặc chờ quá 30 giây:** chọn **REPLAY từ log → `user_module_app_20261031-233732`** rồi bấm **Phát lại**. Nói: "Em phát lại một lần chạy đã ghi log, không gọi LLM."

---

## Bước 3. REPLAY `calculator_agent_mutation`: phần giữ lại từ MuTAP (30 giây)

**Mục đích:** ở bước 2 điểm đã đạt ngưỡng nên agent dừng, chưa thấy được vòng sinh test từ mutant. Log này cho thấy vòng đó.

**Thao tác:** Chọn **REPLAY từ log → `[python] calculator_agent_mutation_20260926-185430`**, bấm **▶️ Phát lại**. Mở mục **2 mutant còn sống**.

**Nói:**

> Lần chạy vừa rồi đạt ngưỡng nên agent dừng ngay. Đây là log một lần chạy em đặt ngưỡng 100 %, dùng model cũ. Coverage đã 100 % nhưng mutation chỉ 90,9 %, tức là còn 2 mutant mà test chưa phát hiện được. Agent đưa hai mutant này vào prompt, đây là ý tưởng của MuTAP. LLM viết thêm 2 test và điểm lên 100 %. Nhưng LLM đã thấy hai mutant này, nên em chấm riêng trên mutant chưa thấy, em sẽ nói ở phần kết quả.

**Giải thích đầy đủ (mở tab 🧾 Code test, tick diff nếu thầy muốn xem test mới):**

| Vòng | Test pass | Coverage | Mutation | Việc agent làm |
|---|---|---|---|---|
| 0 | 5 | 100 % | 20/22 = 90,9 % | 🧬 Đưa 2 mutant còn sống cho LLM |
| 1 | 7 | 100 % | 22/22 = 100 % | ⏹️ Đạt ngưỡng, dừng |

- **Hai mutant:** dòng 40 đổi `value < low` thành `value <= low`; dòng 42 đổi `value > high` thành `value >= high`.
- **Vì sao khó giết:** khi `value` bằng đúng `low`, code gốc trả `value`, mutant trả `low`, hai giá trị bằng nhau. Chỉ phân biệt được khi xét có cùng một đối tượng không, nên LLM viết `result is value`.
- **Test đó có tốt không:** chưa hẳn. Đặc tả không quy định điều này, nên test đang bám vào cách cài đặt. Đây là mặt trái khi chạy theo điểm 100 %.
- **Prompt có cấm không:** prompt hiện tại có quy tắc không kiểm tra chi tiết cài đặt (`testgen/prompts.py:191`). Quy tắc này được commit lúc 18:59, sau log chạy lúc 18:54, nên log có thể chưa áp dụng quy tắc này. Em chưa đo tác dụng của quy tắc.
- **Mỗi prompt đưa bao nhiêu mutant:** tối đa 6 mutant còn sống. MuTAP đưa từng mutant một.

---

## Bước 4. REPLAY `shipping_agent_js`: phần em thêm (30 giây)

**Mục đích:** cho thấy phản hồi coverage và một vòng lặp dùng cho hai ngôn ngữ.

**Thao tác:** Chọn **REPLAY từ log → `[javascript] shipping_agent_js_20260926-210042`**, bấm **▶️ Phát lại**.

**Nói:**

> Cùng vòng lặp này, giờ chạy trên TypeScript. Vòng 1 là phần em thêm so với MuTAP: coverage 92,9 % chưa đạt ngưỡng, agent chỉ cho LLM đúng dòng và nhánh chưa phủ, nên vòng sau đạt 100 %.

**Giải thích đầy đủ (mở tab 🧾 Code test, chỉ phần tô đỏ nếu thầy muốn xem):**

| Vòng | Kết quả đo | Việc agent làm |
|---|---|---|
| 0 | 6 pass, 3 fail, coverage 92,9 % | 🧪 LLM phân loại: 3 test nghi code sai |
| 1 | 6 pass, 0 fail, 3 nhãn, coverage 92,9 % | 📈 Gửi 1 dòng và 1 nhánh chưa phủ |
| 2 | 10 pass, 0 fail, 3 nhãn, coverage 100 %, mutation 18/20 = 90 % | ⏹️ Đạt ngưỡng, dừng |

- **Bug trong module:** đặc tả ghi từ 500 được miễn phí, code viết `total > 500`, nên `shippingFee(500)` trả 15 thay vì 0. Ba nhãn cùng xuất phát từ một bug này, không phải ba bug.
- **Khác gì Python:** vòng lặp giữ nguyên, chỉ đổi adapter sang Jest, Istanbul, StrykerJS. Nhãn là `test.failing`, tương đương `xfail` bên pytest.
- **Thêm ngôn ngữ phải làm gì:** viết một adapter mới, không sửa logic vòng lặp. Tài liệu ước lượng Java 5–6 ngày (`docs/THEM_NGON_NGU_MOI.md`), nhưng chưa hiện thực.
- **Sao biết refactor không làm hỏng Python:** so trước và sau: 8 prompt giống từng ký tự, trạng thái từng mutant của 4 bộ test giống hệt, agent với LLM giả lập cho cùng 7 hành động.
- **So với Python thế nào:** chưa so được. JavaScript mới có 2 lần chạy thử, chưa có thực nghiệm A/B/C/D.

---

## Bước 5. Cách chấm held-out: nói ở slide 22–24

**Mục đích:** điểm đổi thứ hai không thấy được trong một lần chạy, chỉ thấy khi chấm thực nghiệm. Slide đã có bảng và biểu đồ nên không cần chiếu trong demo.

**Câu kết demo, rồi chuyển sang slide trang 21:**

> Tóm lại, demo vừa rồi cho thấy phần em giữ, đổi và thêm so với MuTAP. Còn một điểm đổi nữa là cách chấm, phải nhìn trên số liệu thực nghiệm, nên em xin chuyển sang phần kết quả.

**Giải thích đầy đủ (slide 23, hoặc tab 🔬 Kết quả thực nghiệm nếu thầy muốn xem bảng thật):**

> Em tách bước sinh test và bước chấm. Cột `mutation_all` chấm cả những mutant đã đưa cho LLM: từ B sang C tăng từ 83,0 lên 86,0 %, trông như phản hồi mutation có tác dụng. Cột `mutation_score` chỉ chấm những mutant LLM chưa thấy, gọi là tập held-out: giữ nguyên 91,8 %. Như vậy, cách chấm có thể làm đổi kết luận.
>
> Nhưng em chưa kết luận phản hồi mutation vô ích: đây mới là 1 lượt trên 5 module Python, và vòng mutation chỉ sinh test ở 1 trong 5 module, vì các module còn lại đã đạt ngưỡng 80 %.

| Cấu hình | Thành phần | Held-out | Tất cả mutant | Test fail còn lại | Gọi LLM |
|---|---|---|---|---|---|
| **A** | Sinh một lần | 89,06 | 80,66 | 1,2 | 1,0 |
| **B** | + xử lý test fail, coverage | 91,78 | 82,98 | 0 | 2,4 |
| **C** | + mutation | 91,78 | 86,02 | 0 | 2,6 |
| **D** | + bộ nhớ | 91,78 | 88,08 | 0 | 3,2 |

- **Tập held-out lấy thế nào:** bỏ các mutant đã đưa vào prompt của C và D, rồi dùng chung phần còn lại để chấm cả 4 cấu hình.
- **Sao held-out cao hơn:** những mutant khó nhất còn sống nên được đưa vào prompt, vì thế bị loại khỏi tập held-out. So sánh giữa các cấu hình vẫn công bằng vì dùng chung một tập.

---

## Nếu thầy chỉ cho rất ít thời gian

Làm bước 1 và 2, rồi nói:

> Lần chạy này đạt ngưỡng nên chưa đi vào vòng mutation. Em có log riêng cho vòng mutation và cho TypeScript, thầy muốn xem thì em mở ngay ạ.

---

## Những điều không nên nói

- **"MuTAP sai":** hai điểm trên chỉ là nhận xét của em khi đọc bài.
- **"Agent chắc chắn phát hiện được bug":** số mẫu còn nhỏ, và lần chạy thử `bank_account.js` có 1 nhãn sai trên tổng 9 nhãn.
- **"Phản hồi mutation giúp bắt lỗi mới":** chưa có số liệu đủ để kết luận.
- **So sánh số giữa hai ngôn ngữ:** chưa có thực nghiệm A/B/C/D cho JavaScript, tab Kết quả cũng chỉ có Python.
- **Nói có log thật cho nhánh sửa file test hỏng:** các log hiện có không có vòng 🔧 nào. Nhánh này mới được kiểm tra bằng test của công cụ với LLM giả lập (`tests/test_agent.py`).

## Lỗi thao tác cần tránh

- **Sau khi kéo thanh trượt hoặc tick ô ở tab Code test, các thẻ từng vòng ở tab Tiến trình sẽ biến mất.** Vì vậy, hãy nói xong tab Tiến trình rồi mới sang tab khác. Muốn xem lại thì bấm **Phát lại**.
- **Không đóng cửa sổ đen** của `run_demo.bat` trong lúc demo.
- **Không để lộ `.env`** trên màn chiếu.

---

## Thuật ngữ: nếu thầy hỏi

### Đo chất lượng test

| Thuật ngữ | Trả lời ngắn | Ví dụ |
|---|---|---|
| **Unit test** | Đoạn code tự động gọi một hàm và kiểm tra kết quả | `assert ticket_price(60) == 70000` |
| **Pass / Fail** | Kết quả đúng như mong đợi là pass, sai là fail | Code trả 100000 nên test trên fail |
| **Coverage** | Tỷ lệ phần code đã được test chạy tới. Chỉ cho biết code đã chạy, không cho biết kết quả có được kiểm tra đúng hay không | `ticket_price` đạt 100 % mà vẫn có bug |
| **Line coverage** | Tỷ lệ dòng code đã chạy | 95 trên 100 dòng là 95 % |
| **Branch coverage** | Tỷ lệ nhánh rẽ đã đi qua, như cả `if` đúng và `if` sai | Chỉ thử `age = 30` thì chưa đi qua nhánh `age < 6` |
| **Mutation testing** | Cố tình tạo các lỗi nhỏ trong code, rồi xem test có phát hiện được không. Dùng để đo khả năng bắt lỗi của bộ test | Đổi `<` thành `<=`, chạy lại toàn bộ test |
| **Mutant** | Một bản sao của code bị đổi một chỗ nhỏ | `if age <= 60` thành `if age < 60` |
| **Mutant bị giết** | Có test fail trên mutant, tức là test đã phát hiện thay đổi | |
| **Mutant còn sống** | Tất cả test vẫn pass trên mutant, tức là test chưa phát hiện được | 2 mutant đầu tiên của `calculator` |
| **Mutation score** | Số mutant bị giết / tổng số mutant | `calculator`: 20/22 = 90,9 % |
| **Mutant tương đương** | Mutant có hành vi giống hệt code gốc, nên không test nào giết được. Vì vậy 100 % không phải lúc nào cũng đạt được | |
| **Held-out** | Tập mutant LLM chưa từng thấy trong prompt, dùng để đo khả năng bắt lỗi mới | Như đề thi chưa bị lộ |
| **Ngưỡng** | Mức điểm mà đạt thì agent không cải thiện thêm | Line 95 %, branch 90 %, mutation 80 % |

**Coverage khác mutation thế nào?**
> Coverage trả lời "code đã được chạy tới chưa", còn mutation trả lời "nếu code có lỗi nhỏ thì test có phát hiện được không". Vì vậy một bộ test có thể đạt 100 % coverage mà vẫn bỏ sót lỗi.

**Mutation score 100 % có nghĩa là hết bug không?**
> Không ạ. Điểm này chỉ tính trên những mutant đã tạo. Test vẫn có thể bỏ sót lỗi khác, và code vẫn có thể sai so với đặc tả. Như `ticket_price`, điểm đạt 84,6 % mà lỗi vẫn nằm trong code.

### Xác định đúng sai

| Thuật ngữ | Trả lời ngắn |
|---|---|
| **Đặc tả** | Mô tả hàm phải làm gì, nằm trong docstring (Python) hoặc JSDoc (JS/TS). Là căn cứ để xác định đúng sai |
| **Oracle problem** | Khó biết kết quả nào mới đúng: test fail là do test sai hay code sai. Đề tài giảm vấn đề này bằng cách so với đặc tả, không giải quyết xong hoàn toàn |
| **Hợp thức hóa bug** | Sửa test cho khớp với code đang sai, làm bug bị giấu đi |
| **TEST_WRONG** | LLM kết luận test viết sai, agent sẽ sửa test |
| **SUSPECTED_BUG** | LLM nghi code sai so với đặc tả, agent giữ test và gắn nhãn. Chỉ là nghi ngờ, cần người kiểm tra |
| **`xfail`, `test.failing`** | Đánh dấu test dự kiến fail, lần lượt của pytest và Jest. Test vẫn nằm trong file, bộ test không còn đỏ, lỗi vẫn được báo |

### LLM và agent

| Thuật ngữ | Trả lời ngắn |
|---|---|
| **LLM** | Large Language Model, mô hình ngôn ngữ lớn. Trong đề tài dùng để viết, sửa và phân loại test |
| **Prompt** | Nội dung gửi cho LLM, nằm trong `testgen/prompts.py` |
| **Agent** | Chương trình tự lặp lại các bước: gọi LLM, chạy test, đo kết quả, chọn việc tiếp theo. Em tự viết, không dùng framework |
| **Vòng lặp phản hồi** | Kết quả đo được của vòng này trở thành thông tin gửi cho LLM ở vòng sau |
| **Vòng** | Một lần chạy và đo, kèm một việc agent làm sau đó |
| **Baseline (cấu hình A)** | Hỏi LLM một lần, không có vòng lặp, dùng làm mốc so sánh |
| **Bộ nhớ tự học** | Bài học từ các lần trước, lưu trong file JSON và đưa vào prompt lần sau. Tắt khi demo |
| **LLM giả lập (mock)** | LLM giả dùng để kiểm thử công cụ không tốn API. Không dùng làm kết quả |

### Công cụ và kiến trúc

| Thuật ngữ | Trả lời ngắn |
|---|---|
| **Adapter** | Mẫu thiết kế để vòng lặp không cần biết ngôn ngữ. Mỗi ngôn ngữ có một adapter gọi công cụ riêng |
| **pytest, Jest** | Công cụ chạy test của Python và JS/TS |
| **coverage.py, Istanbul** | Công cụ đo coverage của Python và JS/TS |
| **mutmut, StrykerJS** | Công cụ tạo mutant của Python và JS/TS. Với Python, em dùng toán tử của mutmut và tự viết phần chạy, vì mutmut 3.x không chạy trên Windows |
| **REPLAY** | Phát lại một lần chạy đã lưu trong log, không gọi LLM |
| **Log** | File JSON ghi lại từng vòng của một lần chạy, nằm trong `logs/` |

### Nghiên cứu

| Thuật ngữ | Trả lời ngắn |
|---|---|
| **MuTAP** | Bài nền tảng của Dakhel và cộng sự, 2024: đưa mutant còn sống vào prompt để LLM viết test còn thiếu |
| **MutPy** | Công cụ tạo mutant mà MuTAP dùng |
| **Pynguin** | Công cụ sinh test Python bằng thuật toán tìm kiếm, MuTAP dùng để so sánh |
| **HumanEval** | Bộ 164 bài toán Python, MuTAP dùng để đo mutation score |
| **Refactory** | Bộ 1.710 bài nộp có lỗi thật của sinh viên, MuTAP dùng để đo khả năng phát hiện lỗi |
