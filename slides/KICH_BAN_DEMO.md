# Kịch bản demo: vừa chạy vừa giải thích theo nghiên cứu

Thời lượng khoảng 5 phút. Mạch trình bày: nhắc lại MuTAP, chỉ ra vấn đề, rồi dùng sản phẩm cho thấy cách giải quyết.

| Bước | Màn hình | So với MuTAP | Câu hỏi nghiên cứu | Thời gian |
|---|---|---|---|---|
| 1 | Nhắc lại MuTAP | | | 1 phút |
| 2 | Chạy thật `ticket_price` | **Đổi:** test fail thì so với đặc tả | CH1, CH2 | 1 phút 45 |
| 3 | REPLAY `calculator_agent_mutation` | **Giữ:** mutant còn sống làm phản hồi | CH3 | 45 giây |
| 4 | REPLAY `shipping_agent_js` | **Thêm:** coverage, ngôn ngữ thứ hai | CH4 | 45 giây |
| 5 | Tab Kết quả thực nghiệm | **Đổi:** chấm trên tập held-out | CH3 | 45 giây |

## Chuẩn bị trước khi vào phòng

1. Nhấn đúp `run_demo.bat`, đợi trình duyệt mở `http://localhost:8501`.
2. Mở `DEMO_CHECKLIST.md` và copy sẵn đoạn code `ticket_price`.
3. Ở thanh bên, chọn **Chạy mới → Dán code**. Kéo **Số vòng tối đa** lên **8** cho khớp slide.

---

## Bước 1. Nhắc lại MuTAP (1 phút, chưa thao tác)

> Thưa thầy, đề tài của em dựa trên bài MuTAP của Dakhel và cộng sự, năm 2024. Vấn đề của bài là test do LLM viết thường chỉ được đánh giá bằng coverage, trong khi coverage cao chưa chắc đã bắt được lỗi.
>
> Ý tưởng chính của MuTAP là đưa mutant còn sống vào prompt, tức là nói với LLM rằng bộ test chưa phát hiện được lỗi này, để LLM viết đúng test còn thiếu.
>
> Khi đọc kỹ, em thấy hai điểm cần xem xét. Một là bước 3 sửa giá trị mong đợi theo kết quả của code, tức là mặc định code đúng. Nếu code có bug, test đúng sẽ bị sửa thành test sai. Hai là điểm số được chấm trên chính danh sách mutant đã lấy để đưa vào prompt, nên có thể cao hơn khả năng bắt lỗi mới. Đây là nhận xét của em khi đọc bài, em không nói kết quả của bài là sai.
>
> Vì vậy, em giữ ý tưởng dùng mutant làm phản hồi, đổi hai điểm vừa nêu, và thêm phản hồi coverage cùng ngôn ngữ thứ hai. Hệ thống của em là một vòng lặp: LLM viết test, chạy test thật, đo kết quả, rồi tạo phản hồi cho vòng sau. Mỗi vòng chỉ xử lý vấn đề ưu tiên nhất: file test hỏng, rồi test fail, rồi coverage, cuối cùng là mutant còn sống. Dòng in đậm trên mỗi thẻ cho biết vòng đó đang xử lý vấn đề gì.

---

## Bước 2. Chạy thật: test sai hay code sai? (1 phút 45)

**Mục đích:** cho thấy điểm đổi thứ nhất so với MuTAP.

**Thao tác 1:** Dán code vào ô, **bấm ra ngoài ô**, nhưng chưa bấm chạy.

> Đây là đoạn code em tự viết cho buổi demo. Đặc tả ghi từ 60 tuổi trở lên giá 70000. Thầy có thấy lỗi trong code không?

**Thao tác 2:** Bấm **▶️ Chạy agent**. Lần chạy ngày 31/10 mất 21 giây, nên vừa chờ vừa nói:

> Đầu tiên, LLM đọc code và đặc tả để sinh bộ test, giống như MuTAP. Sau đó agent chạy test thật bằng pytest và đo coverage.

**Thao tác 3:** Khi thẻ **Vòng 0** hiện ra, chỉ vào ô coverage và dòng **🧪 Phân loại & sửa test fail**.

> Coverage ở đây là [đọc số], nhưng vẫn có test fail. Nếu chỉ nhìn coverage, em không biết có lỗi này.
>
> Đến đây có hai khả năng: LLM viết sai test, hoặc code sai. MuTAP mặc định code đúng và sẽ sửa test thành 100000, như vậy bug bị giấu đi. Agent của em yêu cầu LLM so test với đặc tả. Dòng có biểu tượng con bọ là kết luận của LLM: nghi code sai, kèm lý do.

**Thao tác 4:** Chỉ vào thẻ **Vòng 1** và dòng **⏹️ Dừng**.

> Agent giữ test và gắn nhãn, nên không còn test fail nhưng lỗi vẫn được báo. Mutation score đã đạt ngưỡng 80 % nên agent dừng, vòng này không cần viết thêm test.

**Thao tác 5:** Mở tab **🧾 Code test**, chỉ phần **tô đỏ**.

> Test này vẫn khẳng định `ticket_price(60)` phải là 70000, đúng theo đặc tả. Em chỉ gắn nhãn nghi có bug để người kiểm tra xem lại, vì LLM vẫn có thể phân loại sai. Trường hợp LLM viết sai test thì agent sửa test, như log em đã trình bày ở trang 18.

**Số liệu lần chạy 31/10 để đối chiếu:** vòng 0 có 9 pass, 1 fail, coverage 100 %. Vòng 1 có 9 pass, 0 fail, 1 nhãn, mutation 84,6 %. Kết quả mỗi lần có thể khác, nên hãy đọc số trên màn hình.

**Nếu kết quả khác dự kiến:**
- **LLM không bắt được lỗi hoặc phân loại sai:** "Đây là hạn chế em đã nêu: LLM không phải lúc nào cũng đúng, nên nhãn chỉ là nghi ngờ. Em phát lại lần chạy đã ghi log để thầy xem trường hợp bắt được."
- **API lỗi hoặc chờ quá 30 giây:** chọn **REPLAY từ log → `user_module_app_20261031-233732`** rồi bấm **Phát lại**. Nói: "Em phát lại một lần chạy đã ghi log, không gọi LLM."

---

## Bước 3. REPLAY `calculator_agent_mutation`: phần giữ lại từ MuTAP (45 giây)

**Mục đích:** lần chạy thật ở bước 2 đã đạt ngưỡng nên không sinh test từ mutant, vì vậy em dùng log có vòng này.

**Thao tác:** Chọn **REPLAY từ log → `[python] calculator_agent_mutation_20260926-185430`**, bấm **Phát lại**. Mở mục **2 mutant còn sống**.

> Đây là ý tưởng em giữ từ MuTAP. Bộ test đã đạt 100 % coverage nhưng mutation score chỉ 90,9 %. Hai mutant này đổi `<` thành `<=` mà test không phát hiện được. Agent đưa chúng vào prompt, LLM viết thêm 2 test, và điểm lên 100 %.

**Thao tác:** Mở tab **🧾 Code test**, tick **Chỉ xem thay đổi so với vòng trước (diff)**.

> Đây là hai test mới. Em cần nói rõ: lần chạy này em đặt ngưỡng 100 % và dùng model cũ. Hai test này kiểm tra `result is value`, tức là khá bám vào cách cài đặt. Và vì LLM đã thấy hai mutant này, giết được chúng chưa chứng minh bộ test bắt được lỗi mới. Điều này dẫn tới cách chấm của em ở bước cuối.

---

## Bước 4. REPLAY `shipping_agent_js`: phần em thêm (45 giây)

**Mục đích:** cho thấy phản hồi coverage và một vòng lặp dùng cho hai ngôn ngữ.

**Thao tác:** Chọn **REPLAY từ log → `[javascript] shipping_agent_js_20260926-210042`**, bấm **Phát lại**.

> Vẫn vòng lặp đó, nhưng giờ chạy trên TypeScript bằng Jest, Istanbul và StrykerJS. Mọi việc phụ thuộc ngôn ngữ nằm sau một adapter, nên thêm JavaScript không phải sửa logic vòng lặp.
>
> Vòng 0 giống bước trước: 3 test fail, LLM nghi code sai vì đặc tả ghi từ 500 được miễn phí nhưng code viết `total > 500`. Vòng 1 là phần em thêm so với MuTAP: coverage 92,9 % chưa đạt ngưỡng, agent chỉ cho LLM đúng 1 dòng và 1 nhánh chưa phủ. Đến vòng 2, coverage đạt 100 % và mutation đạt 90 %.

**Thao tác:** Mở tab **🧾 Code test**, chỉ phần **tô đỏ**.

> Bên TypeScript, nhãn là `test.failing`, tương đương `xfail` bên pytest.

---

## Bước 5. Tab Kết quả thực nghiệm: cách chấm (45 giây)

**Mục đích:** cho thấy điểm đổi thứ hai. Điểm này không thấy được trong một lần chạy, chỉ thấy khi chấm thực nghiệm.

**Thao tác:** Mở tab **🔬 Kết quả thực nghiệm**, chỉ dòng B và C ở hai cột `mutation_all` và `mutation_score`.

> Em tách bước sinh test và bước chấm. Cột `mutation_all` chấm cả những mutant đã đưa cho LLM: từ B sang C tăng từ 83,0 lên 86,0 %, trông như phản hồi mutation có tác dụng. Cột `mutation_score` chỉ chấm những mutant LLM chưa thấy, gọi là tập held-out: giữ nguyên 91,8 %.
>
> Như vậy, cách chấm có thể làm đổi kết luận. Nhưng em chưa kết luận phản hồi mutation vô ích: đây mới là 1 lượt trên 5 module Python, và vòng mutation chỉ sinh test ở 1 trong 5 module, vì các module còn lại đã đạt ngưỡng 80 %.

**Câu kết, rồi chuyển sang slide trang 21:**

> Tóm lại, em giữ ý tưởng của MuTAP, không mặc định code đúng, chấm trên mutant LLM chưa thấy, và dùng một vòng lặp cho hai ngôn ngữ. Em xin chuyển sang phần số liệu chi tiết.

---

## Nếu thời gian rất ngắn (khoảng 3 phút)

Rút bước 1 còn câu cuối và bỏ bước 4. Khi đó, nói một câu ở bước 5: "Sản phẩm cũng chạy trên TypeScript, thầy có thể xem log `shipping_agent_js`."

## Những điều không nên nói

- **"MuTAP sai":** hai điểm trên chỉ là nhận xét của em khi đọc bài. Kết quả của bài trên lỗi thật của sinh viên (Refactory) không bị ảnh hưởng bởi cách chấm.
- **"Agent chắc chắn phát hiện được bug":** số mẫu còn nhỏ, và lần chạy thử `bank_account.js` có 1 nhãn sai trên tổng 9 nhãn.
- **"Phản hồi mutation giúp bắt lỗi mới":** chưa có số liệu đủ để kết luận.
- **So sánh số giữa hai ngôn ngữ:** chưa có thực nghiệm A/B/C/D cho JavaScript, tab Kết quả cũng chỉ có Python.
- **Nói có log thật cho nhánh sửa file test hỏng:** 19 log hiện có không có vòng 🔧 nào. Nhánh này mới được kiểm tra bằng test của công cụ với LLM giả lập (`tests/test_agent.py`).

## Thầy có thể hỏi

1. **Sao biết LLM phân loại đúng?** → Trong một lần chạy thì không chắc chắn, nên chỉ gắn nhãn nghi ngờ. Trong thực nghiệm, em chấm tự động: nhãn đúng khi test fail hoặc mang nhãn trên code lỗi và pass trên bản đã sửa.
2. **Nếu không có đặc tả thì sao?** → Agent mất căn cứ để so sánh, đây là một hạn chế của đề tài.
3. **Sao ở bước 2 mutant `age < 60` vẫn còn sống?** → Vì đổi `<=` thành `<` chính là cách sửa bug. Trên mutant này, test `ticket_price(60)` đúng ra phải pass, nên không thể giết nó bằng test đúng đặc tả.
4. **Sao bước 3, 4 không chạy thật?** → Mỗi lần chạy tốn lượt gọi API, và `shipping.ts` từng mất 169 giây. Nhưng chúng là log của lần chạy thật, không phải kết quả giả lập; giao diện cũng ghi rõ đang phát lại.
5. **Khác gì so với MuTAP về số lần lặp?** → MuTAP lặp đến khi đạt 100 % hoặc hết mutant sống. Em dừng ở ngưỡng 80 %, nên vòng mutation ít khi chạy. Bước tiếp theo là thử ngưỡng cao hơn. Bước rút gọn bộ test của MuTAP em chưa làm.

## Lỗi thao tác cần tránh

- **Sau khi kéo thanh trượt hoặc tick ô ở tab Code test, các thẻ từng vòng ở tab Tiến trình sẽ biến mất.** Vì vậy, hãy nói xong tab Tiến trình rồi mới sang tab khác. Muốn xem lại thì bấm **Phát lại**.
- **Không đóng cửa sổ đen** của `run_demo.bat` trong lúc demo.
- **Không để lộ `.env`** trên màn chiếu.
