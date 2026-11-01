# Giải thích mọi thứ trong demo

File này giúp em hiểu để tự giải thích. Thao tác và lời nói theo từng bước nằm trong `slides/KICH_BAN_DEMO.md`.

**Nên học theo thứ tự:** Phần 1 → Phần 2 → Phần 3. Phần 4 dùng để tra khi quên một ô trên màn hình. Phần 5 dùng để luyện trả lời.

---

## Phần 1. Hiểu toàn bộ sản phẩm trong 1 phút

**Sản phẩm làm gì?** Em đưa vào một đoạn code có đặc tả. Agent tự viết unit test, chạy thử, tự cải thiện bộ test qua nhiều vòng, và báo chỗ nghi code có bug.

| | Nội dung |
|---|---|
| **Đầu vào** | Code Python hoặc JavaScript/TypeScript, có docstring hoặc JSDoc mô tả hành vi đúng |
| **Xử lý** | LLM viết test → chương trình chạy thật và đo → tạo phản hồi → LLM viết hoặc sửa tiếp |
| **Đầu ra** | File test, các nhãn nghi có bug, điểm coverage và mutation, log của từng vòng |

**Vì sao cần vòng lặp?** LLM viết test rất nhanh, nhưng test có thể không chạy được, bỏ sót trường hợp, hoặc viết sai. Vòng lặp cho LLM biết kết quả chạy thật thay vì tin ngay câu trả lời đầu tiên.

**Câu nói gọn:**
> Thay vì hỏi LLM một lần rồi tin luôn, agent của em chạy test thật, đo kết quả rồi gửi phản hồi cụ thể để LLM cải thiện. Khi test fail, agent không mặc định code đúng mà so với đặc tả.

---

## Phần 2. Các khái niệm cần hiểu

Các ví dụ dưới đây dùng chung hàm trong demo:

```python
def ticket_price(age):
    """Từ 18 đến dưới 60 tuổi giá 100000, từ 60 tuổi giá 70000 (...)."""
    ...
    if age <= 60:        # lỗi: đặc tả yêu cầu đúng 60 tuổi phải giá 70000
        return 100000
    return 70000
```

### Unit test
Một đoạn code nhỏ tự động gọi hàm và kiểm tra kết quả.
```python
def test_60_tuoi():
    assert ticket_price(60) == 70000
```
Kết quả đúng thì test **pass**, sai thì test **fail**.

### Đặc tả (docstring, JSDoc)
Phần mô tả hàm **phải** làm gì. Agent dùng đặc tả làm căn cứ để xác định đúng sai. Nếu code không có đặc tả rõ ràng, agent mất căn cứ. Đây là một hạn chế của đề tài.

### Oracle problem
Oracle là thứ cho biết kết quả nào mới đúng. Khi test fail, có hai khả năng:

| Khả năng | Ví dụ | Việc cần làm |
|---|---|---|
| **Test sai** | LLM tính nhầm, viết 44,9 trong khi đúng là 48,1 | Sửa test |
| **Code sai** | Đặc tả ghi 70000, code trả 100000 | Giữ test, báo cho người kiểm tra |

Nếu luôn sửa test theo code, bug sẽ được hợp thức hóa. Đề tài **giảm** vấn đề này, không giải quyết xong hoàn toàn, vì LLM vẫn có thể phân loại sai.

### Coverage
Tỷ lệ phần code đã được test chạy tới. **Line** tính theo dòng, **branch** tính theo nhánh `if`.

Coverage chỉ cho biết code đã được chạy, chưa cho biết test có kiểm tra đúng hay không. Trong lần chạy 31/10, `ticket_price` đạt coverage 100 % mà vẫn có bug.

### Mutant và mutation score
**Mutant** là bản sao của code bị cố tình đổi một chỗ nhỏ, ví dụ `<` thành `<=`. Chạy lại test trên bản đó:
- Có test fail: mutant **bị giết**, test đã phát hiện thay đổi.
- Tất cả test pass: mutant **còn sống**, test chưa phát hiện được.

**Mutation score** = số mutant bị giết / tổng số mutant. Ví dụ `calculator` ở vòng 0 giết được 20/22 mutant, nên điểm là 90,9 %.

### Held-out
Tập mutant **LLM chưa từng thấy trong prompt**. Giống như khi cho học sinh xem trước đề rồi chấm đúng đề đó, điểm cao chưa chắc học sinh đã giỏi. Muốn đo khả năng bắt lỗi mới thì phải chấm trên đề chưa lộ.

### SUSPECTED_BUG, `xfail`, `test.failing`
Là nhãn "test này đúng theo đặc tả, nhưng nghi code sai".
- Python dùng `@pytest.mark.xfail`, JS/TS dùng `test.failing`. Cả hai đều có nghĩa là test **dự kiến fail**.
- Vì vậy bộ test không còn đỏ, nhưng lỗi vẫn được báo và test vẫn nằm trong file.
- Đây chỉ là **nghi ngờ**, người kiểm tra phải xem lại.

### Adapter
Mẫu thiết kế giúp vòng lặp không cần biết đang làm việc với ngôn ngữ nào. Giống ổ cắm chuyển đổi: vòng lặp chỉ gọi `run_tests` hay `run_mutation`, còn mỗi adapter tự gọi công cụ của ngôn ngữ đó.

| | Python | JavaScript/TypeScript |
|---|---|---|
| Chạy test | pytest | Jest |
| Đo coverage | coverage.py | Istanbul |
| Mutation | toán tử của mutmut + runner em tự viết | StrykerJS |
| Nhãn nghi bug | `xfail` | `test.failing` |

### MuTAP (bài nền tảng)
Dakhel và cộng sự, 2024. Ý tưởng chính là đưa mutant còn sống vào prompt để LLM viết đúng test còn thiếu.

| Em làm gì so với MuTAP | Nội dung | Thấy ở đâu trong demo |
|---|---|---|
| **Giữ** | Mutant còn sống làm phản hồi | Bước 3 |
| **Đổi** | Không mặc định code đúng, so với đặc tả | Bước 2 |
| **Đổi** | Chấm trên tập held-out | Slide 22–24 |
| **Đổi** | Gửi thông báo lỗi thật khi file test hỏng | Chỉ nói khi được hỏi, chưa có log thật |
| **Thêm** | Phản hồi coverage, ngôn ngữ thứ hai | Bước 4 |
| **Thêm** | Bộ nhớ bài học | Tắt khi demo |
| **Chưa làm** | Rút gọn bộ test như bước 6 của MuTAP | |

---

## Phần 3. Luồng chạy từ khi bấm nút đến khi có kết quả

### Ai làm việc gì?
Đây là ý quan trọng nhất khi giải thích luồng.

| Việc | Ai làm |
|---|---|
| Viết test, sửa test, phân loại test fail | **LLM** |
| Chạy test, đo coverage, tạo và chạy mutant | **Công cụ thật** (pytest, Jest, Stryker...) |
| Chọn việc tiếp theo, ghép test vào file, gắn nhãn, dừng vòng lặp | **Code của em** (`for` và `if/else`) |

LLM không tự chấm điểm mình. Mọi con số trên màn hình đều do công cụ đo. LLM chỉ trả về test mới hoặc test đã sửa, chương trình tự ghép vào file, nên LLM không xóa được test cũ hay gỡ nhãn.

### Sơ đồ một lần chạy

```text
Bước đầu: LLM đọc code + đặc tả, sinh bộ test
   │
   ▼
Mỗi vòng: chạy test thật và đo coverage
   │
   ├─ 1. File test không chạy được?  → 🔧 gửi lỗi thật, LLM sửa cả file
   ├─ 2. Có test fail?               → 🧪 LLM phân loại từng test
   │        ├─ test sai → LLM sửa test đó (quá 2 lần thì xóa test)
   │        └─ nghi code sai → giữ test, gắn nhãn
   ├─ 3. Coverage chưa đạt?          → 📈 gửi dòng/nhánh chưa phủ, LLM viết thêm
   ├─ 4. Mutation chưa đạt?          → 🧬 gửi mutant còn sống, LLM viết thêm
   └─ Đạt hết hoặc không cải thiện   → ⏹️ dừng, lưu kết quả
   │
   └─ Quay lại đầu vòng, chạy và đo lại
```

Mỗi vòng **chỉ xử lý một vấn đề**, ưu tiên từ trên xuống. Lý do: coverage của một bộ test đang fail thì không đáng tin, nên phải xử lý test fail trước.

**Agent dừng khi:** đạt ngưỡng; hai lần liên tiếp không cải thiện; hết số vòng tối đa; hoặc gọi LLM bị lỗi (khi đó giữ bộ test tốt nhất hiện có).

Code tương ứng: `testgen/agent.py:147` là vòng lặp, `testgen/agent.py:169` là thứ tự ưu tiên.

### Đi qua một lần chạy thật: `ticket_price`, ngày 31/10

| Thời điểm | Chuyện gì xảy ra | Vì sao |
|---|---|---|
| Trước vòng 0 | **Gọi LLM lần 1:** sinh bộ test | Yêu cầu viết assert theo đặc tả |
| Vòng 0 | pytest chạy: 9 pass, 1 fail; coverage 100 % | Test `ticket_price(60) == 70000` fail vì code trả 100000 |
| Vòng 0 | Ô Mutation hiện "—" | Còn test fail nên chưa tới bước mutation |
| Vòng 0 | **Gọi LLM lần 2:** phân loại, kết quả SUSPECTED_BUG | Đặc tả ghi rõ, code vi phạm |
| Vòng 0 | Chương trình gắn `xfail`, không gọi thêm LLM | Không có test sai nên không cần sửa |
| Vòng 1 | pytest chạy: 9 pass, 0 fail, 1 nhãn | Test có nhãn được tính là dự kiến fail |
| Vòng 1 | Mutation: 11/13 mutant bị giết = 84,6 % | Coverage đã đạt nên chuyển sang mutation |
| Vòng 1 | ⏹️ Dừng | 84,6 % ≥ ngưỡng 80 %, không viết thêm test |

Tổng cộng 2 lần gọi LLM, 21 giây. Việc chạy test và mutation không tốn lượt gọi LLM.

---

## Phần 4. Mọi thứ trên màn hình

### Thanh bên: chế độ Chạy mới

| Mục | Nghĩa |
|---|---|
| **Chế độ** | Chạy mới gọi LLM thật. REPLAY phát lại log đã lưu, không gọi LLM |
| **Mã nguồn** | Module mẫu trong `targets/`, hoặc Dán code |
| **Ngôn ngữ** | Chọn được; khi dán code thì tự nhận diện |
| **Tên module** | Tên dùng để lưu file code dán vào |
| **Khung xanh 🔧** | Công cụ đang dùng cho ngôn ngữ đó |
| **Mutation testing** | Bật hoặc tắt bước mutation |
| **Bộ nhớ tự học** | Dùng bài học từ các lần trước. Demo để **tắt** |
| **Số vòng tối đa** | Giới hạn số vòng. Mặc định 6 trên giao diện, nên kéo lên 8 cho khớp slide |
| **Ngưỡng line, branch, mutation** | Mặc định 95, 90, 80 %. Đạt ngưỡng thì không cải thiện thêm |
| **Số mutant tối đa** | Giới hạn số mutant để chạy không quá lâu |
| **Nhà cung cấp, Model** | LLM đang dùng, đọc từ `.env` |

### Thanh bên: chế độ REPLAY

| Mục | Nghĩa |
|---|---|
| **Chọn log** | Lần chạy đã lưu, phần đầu ghi ngôn ngữ, ví dụ `[python]` |
| **Tốc độ phát lại** | Số giây giữa hai vòng |

### Tab 🔄 Tiến trình: thẻ từng vòng

| Ô | Nghĩa |
|---|---|
| **Vòng** | Số thứ tự, bắt đầu từ 0 |
| **Pass / Fail** | Số test pass và số test fail hoặc lỗi. Test có nhãn không tính vào đây |
| **Line cov., Branch cov.** | Coverage đo ở vòng đó |
| **Mutation** | Mutation score. Hiện "—" nếu vòng đó chưa chạy mutation |
| **Dòng in đậm** | Việc agent làm ở vòng đó, kèm lý do |
| **Khung vàng** | Số test có nhãn SUSPECTED_BUG |
| **🐞 ... SUSPECTED_BUG** | LLM nghi code sai, kèm lý do |
| **✏️ ... TEST_WRONG** | LLM cho là test sai |
| **Mục "mutant còn sống"** | Đoạn code đã bị đổi mà test chưa phát hiện |
| **📝 LESSON** | Bài học LLM rút ra khi sửa lỗi |

**Cách đọc dòng in đậm:** Số liệu trên thẻ là kết quả đo **đầu vòng**, dòng in đậm là việc agent làm **sau khi** có kết quả đó. Hiệu quả của việc này sẽ thấy ở thẻ vòng tiếp theo.

### Tab 🔄 Tiến trình: khung tổng kết cuối trang

| Ô | Nghĩa |
|---|---|
| **Kết thúc** | Lý do dừng |
| **Line, Branch, Mutation** | Kết quả cuối cùng |
| **Số vòng** | Số vòng có cải tiến; vòng cuối chỉ đo rồi dừng nên không tính |
| **Gọi LLM** | Tổng số lần gọi LLM |
| **Thời gian** | Tổng thời gian chạy |
| **Khung đỏ 🐞** | Danh sách test nghi có bug, cần người kiểm tra |
| **Dòng chữ nhỏ** | Công cụ, model, tên file log |

### Các tab còn lại

| Tab | Xem gì | Chú ý |
|---|---|---|
| **📊 Biểu đồ** | Coverage và mutation qua các vòng; bảng số liệu | Đường mutation chỉ có ở vòng đã chạy mutation |
| **🧾 Code test** | Code test ở từng vòng; phần tô đỏ là test có nhãn | Có **diff** để xem thay đổi; kéo thanh trượt hoặc tick ô sẽ làm thẻ ở tab Tiến trình biến mất |
| **🔬 Kết quả thực nghiệm** | Bảng và biểu đồ A/B/C/D | Hiện chỉ có Python, 1 lượt |
| **📄 Mã nguồn module** | Code đem ra kiểm thử | Dùng để chỉ dòng có bug |

### Bảng trong tab Kết quả thực nghiệm

**Bốn cấu hình, mỗi cấu hình thêm một thành phần:**

| Cấu hình | Thành phần | `mutation_score` (held-out) | `mutation_all` | `tests_failing` | `llm_calls` | `bug_flagged_rate` |
|---|---|---|---|---|---|---|
| **A** | Sinh một lần | 89,06 | 80,66 | 1,2 | 1,0 | 0 % |
| **B** | + xử lý test fail, coverage | 91,78 | 82,98 | 0 | 2,4 | 100 % |
| **C** | + mutation | 91,78 | 86,02 | 0 | 2,6 | 100 % |
| **D** | + bộ nhớ | 91,78 | 88,08 | 0 | 3,2 | 100 % |

**Nghĩa các cột hay được hỏi:**

| Cột | Nghĩa |
|---|---|
| `language`, `config` | Ngôn ngữ, cấu hình |
| `n_runs`, `n_modules` | Số lượt chạy, số module |
| `line_coverage`, `branch_coverage` | Coverage trung bình |
| `mutation_score` | **Điểm chỉ trên mutant LLM chưa thấy (held-out)** |
| `mutation_all` | Điểm trên tất cả mutant, gồm cả mutant đã đưa cho LLM |
| `iterations`, `llm_calls`, `seconds` | Số vòng, số lần gọi LLM, thời gian (trung bình mỗi module) |
| `tests_total`, `tests_failing` | Số test, số test còn fail (trung bình mỗi module) |
| `suspected_tp`, `suspected_fp` | Số nhãn đúng, số nhãn sai |
| `bug_detection_rate` | Tỷ lệ bug có test bắt được |
| `bug_flagged_rate` | Tỷ lệ bug được gắn nhãn đúng |

**Ba ý đọc từ bảng:**
1. **A sang B:** test fail giảm từ 1,2 xuống 0, bug được gắn nhãn đúng tăng từ 0 lên 100 %. Ở A, test cũng đã fail ở bug (`bug_detection_rate` 100 %), nhưng chưa được phân loại nên người dùng phải tự đoán. Đổi lại, số lần gọi LLM tăng.
2. **B sang C:** `mutation_all` tăng từ 82,98 lên 86,02, nhưng held-out giữ nguyên 91,78. Đây là chỗ cách chấm làm đổi kết luận.
3. **Giới hạn:** chỉ 1 lượt, 5 module tự viết, 2 bug cài sẵn, vòng mutation chỉ sinh test ở 1/5 module. Vì vậy đây mới là quan sát ban đầu.

---

## Phần 5. Giải thích từng bước demo và câu hỏi thầy có thể hỏi

### Bước 1: Nhắc lại MuTAP
**Cần làm rõ:** Vấn đề của MuTAP là gì, hai điểm em thấy cần xem xét, và em giữ, đổi, thêm gì.

- **Hỏi: "Sao em nói MuTAP mặc định code đúng?"** → Bước 3 của bài thay giá trị mong đợi khác với kết quả của code bằng kết quả của code. Nếu code có bug, test đúng sẽ bị sửa thành test sai.
- **Hỏi: "Vậy MuTAP sai à?"** → Không ạ. Đây là nhận xét của em. Kết quả trên lỗi thật của sinh viên không bị ảnh hưởng bởi cách chấm, vì lỗi đó không được đưa vào prompt.

### Bước 2: Chạy `ticket_price`
**Cần làm rõ:** Coverage cao vẫn có bug, và agent không sửa test theo code.

- **Hỏi: "Sao LLM biết code sai?"** → LLM nhận mã nguồn, đặc tả, test đang fail và thông báo lỗi, rồi phải phân loại từng test. Prompt yêu cầu chỉ chọn SUSPECTED_BUG khi đặc tả nói rõ và code vi phạm (`testgen/prompts.py:87`).
- **Hỏi: "LLM phân loại sai thì sao?"** → Có thể xảy ra, lần chạy thử `bank_account.js` có 1 nhãn sai trên 9 nhãn. Vì vậy em chỉ gắn nhãn nghi ngờ, và trong thực nghiệm em chấm nhãn tự động bằng bản code đã sửa.
- **Hỏi: "Nhãn sai có hại gì?"** → Một test sai có thể được giữ lại và báo nhầm là code có bug, nên người kiểm tra mất công xem lại.
- **Hỏi: "Sao mutant `age < 60` còn sống?"** → Đổi `<=` thành `<` chính là cách sửa bug. Trên mutant này, test `ticket_price(60)` đúng ra phải pass, nên không thể giết nó bằng test đúng đặc tả.
- **Hỏi: "Sao đạt 84,6 % đã dừng?"** → Vì ngưỡng là 80 %. Ngưỡng này làm vòng mutation ít khi chạy, em đã ghi là hạn chế và cần thử ngưỡng cao hơn.
- **Hỏi: "Kết quả có giống mỗi lần chạy không?"** → Không, LLM có tính ngẫu nhiên. Vì vậy thực nghiệm cần chạy nhiều lượt, mà hiện mới có 1 lượt.

### Bước 3: REPLAY `calculator_agent_mutation`
**Cần làm rõ:** Có coverage 100 % mà mutation vẫn chưa đủ, và đây là cách phản hồi mutation hoạt động.

Log này: 20/22 mutant bị giết (90,9 %) → LLM viết thêm 2 test → 22/22 (100 %). Tốn 2 lần gọi LLM. Mỗi prompt đưa tối đa 6 mutant còn sống.

- **Hỏi: "Sao hai mutant này khó giết?"** → Khi `value` bằng đúng `low`, code gốc trả `value`, mutant trả `low`, hai giá trị bằng nhau. Chỉ phân biệt được khi xét có cùng một đối tượng không, nên LLM viết `result is value`.
- **Hỏi: "Test như vậy có tốt không?"** → Không hẳn, vì đặc tả không quy định điều đó, nên test đang bám vào cách cài đặt. Đây là mặt trái khi chạy theo điểm 100 %.
- **Hỏi: "Prompt của em có cấm viết kiểu này không?"** → Prompt hiện tại có quy tắc không kiểm tra chi tiết cài đặt, và coi mutant kiểu này là tương đương (`testgen/prompts.py:191`). Quy tắc này được commit lúc 18:59, sau log chạy lúc 18:54, nên log này có thể chưa áp dụng quy tắc. Em chưa đo lại xem quy tắc có hiệu quả không.
- **Hỏi: "Sao không chạy thật?"** → Lần chạy thật ở bước 2 thường đạt ngưỡng 80 % nên không sinh test từ mutant. Log này đặt ngưỡng 100 % để thấy rõ cơ chế. Đây là log thật, nhưng dùng model cũ.

### Bước 4: REPLAY `shipping_agent_js`
**Cần làm rõ:** Phản hồi coverage hoạt động thế nào, và vòng lặp không đổi khi đổi ngôn ngữ.

| Vòng | Kết quả đo | Việc agent làm |
|---|---|---|
| 0 | 6 pass, 3 fail, coverage 92,9 % | 🧪 LLM phân loại: 3 test nghi code sai |
| 1 | 6 pass, 0 fail, 3 nhãn, coverage 92,9 % | 📈 Gửi 1 dòng và 1 nhánh chưa phủ |
| 2 | 10 pass, 0 fail, 3 nhãn, coverage 100 %, mutation 90 % | ⏹️ Đạt ngưỡng, dừng |

3 nhãn này cùng xuất phát từ một bug ở mốc 500, nên không phải 3 bug.

- **Hỏi: "Thêm ngôn ngữ phải sửa gì?"** → Viết một adapter mới, không sửa logic vòng lặp. Em đã có tài liệu ước lượng cho Java là 5–6 ngày (`docs/THEM_NGON_NGU_MOI.md`), nhưng chưa hiện thực.
- **Hỏi: "Sao biết refactor không làm hỏng phần Python?"** → Em so sánh trước và sau: 8 prompt giống từng ký tự, trạng thái từng mutant của 4 bộ test giống hệt, và agent với LLM giả lập cho cùng 7 hành động.
- **Hỏi: "JavaScript có tốt bằng Python không?"** → Chưa so sánh được, vì mới có 2 lần chạy thử, chưa có thực nghiệm A/B/C/D.

### Bước 5: Cách chấm held-out (nói ở slide 22–24, không chiếu trong demo)
**Cần làm rõ:** Cách chấm có thể làm đổi kết luận, nhưng dữ liệu còn ít nên chưa kết luận được về phản hồi mutation.

- **Hỏi: "Tập held-out lấy thế nào?"** → Bỏ các mutant đã đưa vào prompt của C và D, rồi dùng chung phần còn lại để chấm cả 4 cấu hình.
- **Hỏi: "Sao held-out cao hơn mutation_all?"** → Những mutant khó nhất còn sống nên được đưa vào prompt, vì thế bị loại khỏi tập held-out. So sánh giữa các cấu hình vẫn công bằng vì dùng chung một tập.
- **Hỏi: "Vậy phản hồi mutation vô ích à?"** → Chưa thể kết luận. Vòng mutation chỉ sinh test ở 1 trong 5 module, vì 4 module còn lại đã đạt ngưỡng 80 %. Cần thử ngưỡng cao hơn và chạy thêm lượt.
- **Hỏi: "Sao coverage các cấu hình bằng nhau?"** → Vì lần sinh đầu đã đạt 99 % trên các module nhỏ này, nên phản hồi coverage chưa thể hiện tác dụng trong bảng này.
- **Hỏi: "Sao mới 1 lượt?"** → Do model miễn phí giới hạn 50 lượt gọi mỗi ngày. Em ghi rõ đây là hạn chế, và đề yêu cầu 3 lượt nên vẫn còn phải chạy tiếp.

---

## Phần 6. Bốn câu tóm tắt cần thuộc

1. **Sản phẩm:** "Agent viết test, chạy thật, đo kết quả, rồi dùng phản hồi đó để cải thiện qua nhiều vòng."
2. **Coverage và mutation:** "Coverage cho biết code đã được chạy tới chưa, mutation kiểm tra test có phát hiện được lỗi nhỏ không."
3. **So với MuTAP:** "Em giữ ý tưởng dùng mutant làm phản hồi, không mặc định code đúng, chấm trên mutant LLM chưa thấy, và thêm phản hồi coverage cùng ngôn ngữ thứ hai."
4. **Hạn chế:** "Số liệu còn ít, LLM vẫn có thể phân loại sai, và cần có đặc tả rõ ràng."

Nếu gặp câu chưa biết, hãy nói thật: "Phần này em chưa đo, nên em chưa kết luận được." Đừng đoán số liệu.
