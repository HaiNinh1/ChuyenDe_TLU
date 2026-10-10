# Lời thoại thuyết trình (12–15 phút) + câu hỏi vấn đáp

> Mẹo: nói chậm, mỗi slide ~1 phút. Slide 4 (kiến trúc Adapter), 9 (refactor an toàn), 11–12 (kết quả) và 13 (demo)
> là quan trọng nhất.

---

## Slide 0 — Tiêu đề (20 giây)
"Em xin chào thầy cô. Đề tài của em là **LLM agent tự sinh unit test đa ngôn ngữ**, có **vòng lặp tự cải tiến** dựa
trên hai loại phản hồi là **coverage** và **mutation testing**. Hiện em đã hiện thực cho **Python** và
**JavaScript/TypeScript**."

## Slide 1 — Vấn đề (1 phút)
"Viết unit test tốn thời gian nên hay bị bỏ qua. LLM viết test rất nhanh, nhưng test có thể không chạy được, có thể bỏ
sót nhánh, và nguy hiểm nhất là **hợp thức hoá bug** — code trả về C cho điểm 80, LLM nhìn code rồi viết `== "C"`, test
pass, bug bị che đi. Câu hỏi của em: làm sao để LLM tự kiểm tra và cải thiện bộ test, và làm được cho nhiều ngôn ngữ
mà không phải viết lại từ đầu?"

## Slide 2 — Hướng tiếp cận hiện có (1 phút)
"Có ba hướng. Công cụ tìm kiếm – tiến hoá như EvoSuite, Pynguin: coverage cao nhưng assert chỉ 'chụp' hành vi hiện tại,
và **mỗi công cụ chỉ cho một ngôn ngữ**. Hỏi LLM một lần: dễ đọc nhưng không kiểm chứng. Hướng thứ ba như CoverUp,
MuTAP kết hợp LLM với phản hồi thực thi. Em đi theo hướng thứ ba, tự cài đặt đơn giản, và tách phần phụ thuộc ngôn ngữ
ra thành các adapter."

## Slide 2.1 — Bài nền tảng MuTAP (1 phút 30)
"Đề tài của em dựa trên bài **MuTAP** của nhóm Dakhel, đăng trên tạp chí Information and Software Technology năm 2024.
Ý tưởng chính: mutant còn sống cho AI biết chính xác bộ test đang bỏ sót lỗi nào, nên đưa mutant đó vào prompt để AI viết
thêm test bắt đúng lỗi đó. Quy trình 6 bước: sinh test, sửa cú pháp, sửa giá trị mong đợi theo kết quả chạy code, đo
mutation bằng MutPy, chưa đạt 100 % thì thêm một mutant sống vào prompt rồi lặp, cuối cùng rút gọn bộ test. Kết quả trong
bài: mutation score 93,57 % so với 65,94 % của Pynguin; trên lỗi thật của sinh viên phát hiện 94,91 % so với 67,54 %.
Đây là số của bài, em không chạy lại."

## Slide 2.2 — Kế thừa và cải tiến (1 phút 30)
"Em kế thừa ý tưởng chính: dùng mutant còn sống làm phản hồi. Nhưng khi đọc kỹ em thấy hai điểm yếu. Thứ nhất, bước 3
**giả định code luôn đúng**: nếu code có bug thì test bị sửa cho khớp bug — ví dụ đặc tả nói 80 điểm là B, code trả C,
MuTAP sẽ sửa test thành C. Đây là oracle problem. Em xử lý bằng cách cho AI so test với đặc tả: test sai thì sửa, nghi
code sai thì giữ test và gắn nhãn nghi bug. Thứ hai, MuTAP chấm mutation score trên **chính các mutant đã đưa cho AI xem**
— giống cho xem trước đề rồi chấm trên đúng đề đó. Em chấm thêm trên tập mutant AI chưa từng thấy. Ngoài ra em gửi kèm
thông báo lỗi khi sửa test, thêm bước coverage, và làm cho cả JavaScript."

## Slide 3 — Mục tiêu & phạm vi (40 giây)
"Mục tiêu: agent sinh test, chạy, đo, rồi dùng kết quả đo để tự sửa và bổ sung; xử lý oracle problem; **một vòng lặp
dùng cho nhiều ngôn ngữ**; so sánh 4 cấu hình. Phạm vi: Python 5 module, JavaScript/TypeScript 4 module, tổng cộng 4 bug
cài sẵn, không dùng framework agent."

## Slide 4 — Kiến trúc Adapter (1 phút 30)
"Đây là thay đổi chính so với bản đầu. Agent — vẫn chỉ là vòng for và if/else — **không biết** mình đang làm việc với
ngôn ngữ nào. Nó chỉ gọi các phương thức của một giao diện chung `LanguageAdapter`: chạy test, đo coverage, chạy mutation,
ghép test mới, gắn nhãn nghi bug. Mỗi ngôn ngữ là một lớp con: Python dùng pytest, coverage.py, mutmut; JavaScript và
TypeScript dùng Jest, Istanbul, StrykerJS. Registry chọn adapter theo đuôi file. Prompt cũng tách làm hai: khung chung —
quy trình, yêu cầu phân loại, chống oracle problem — và phần gợi ý riêng như tên framework, cách viết import, cách assert
ngoại lệ. Thêm Java chỉ cần viết thêm một lớp và một dòng đăng ký."

## Slide 5 — Vòng lặp (1 phút)
"Thứ tự ưu tiên: sửa file hỏng, xử lý test fail, tăng coverage, rồi mutation. Điểm quan trọng nhất là bước 4: khi test
fail, agent **không** tự sửa test cho pass mà hỏi LLM: test sai hay code có bug so với đặc tả? Nếu nghi bug, test được
**giữ nguyên** và gắn nhãn — `xfail` bên pytest, `test.failing` bên Jest — bộ test vẫn xanh nhưng bằng chứng còn đó cho
người review. LLM chỉ trả về test mới hoặc đã sửa, chương trình tự ghép — Python dùng `ast`, JS dùng một bộ quét ngoặc
em tự viết — nên LLM không thể xoá test cũ."

## Slide 6 — Coverage (40 giây)
"Line coverage đo phần trăm dòng được chạy, branch coverage đo phần trăm nhánh. Agent gửi cho LLM chính xác chỗ chưa
phủ. Mỗi công cụ có định dạng khác nhau — coverage.py cho cặp 'từ dòng tới dòng', Istanbul cho từng nhánh của if, switch,
toán tử `&&` — nên mỗi adapter tự mô tả bằng lời cho LLM."

## Slide 7 — Mutation (1 phút)
"Coverage 100% chưa chắc test tốt. Mutation testing sửa nhẹ code — đổi `>= 90` thành `> 90` — rồi chạy lại bộ test; phải
có test đúng biên 90 mới giết được mutant. Python dùng toán tử của mutmut 2.5.1 với runner tự viết vì mutmut 3 không chạy
trên Windows; JS dùng StrykerJS. Nếu máy chưa cài công cụ mutation, adapter báo 'không khả dụng' và agent vẫn chạy phần
coverage, không bị dừng."

## Slide 8 — Bộ nhớ (40 giây)
"Bộ nhớ là file JSON lưu bài học sửa lỗi và mẫu test tốt, chỉ lưu khi đã xác nhận có tác dụng. Khi có nhiều ngôn ngữ em
**chia bộ nhớ theo ngôn ngữ**, vì bài học 'dùng `pytest.approx`' đưa vào prompt Jest chỉ gây nhiễu. Dữ liệu cũ của Python
được tự chuyển sang định dạng mới, không mất. Đây là học trong ngữ cảnh — trọng số mô hình không đổi."

## Slide 9 — Refactor an toàn (1 phút 30)
"Yêu cầu số một khi refactor là không làm hỏng phần Python đã chạy tốt. Trước khi sửa, em chụp lại hành vi của hệ thống:
mã băm của 8 prompt, kết quả chạy lại các bộ test đã lưu, trạng thái của từng mutant trong 160 mutant, và một lần chạy
agent với LLM giả lập theo kịch bản. Sau mỗi bước refactor em chạy lại và so sánh: tất cả **giống hệt** — prompt giống từng
ký tự, nên LLM nhận đúng nội dung như cũ. Chấm lại thực nghiệm cũ ra file kết quả giống từng byte. Riêng lần chạy với LLM
thật thì không thể giống hệt vì LLM ngẫu nhiên, nhưng cùng chuỗi hành động và cùng mức coverage, mutation."

## Slide 10 — Thiết lập thực nghiệm (1 phút)
"Bốn cấu hình A, B, C, D giữ nguyên. Hai bug JS được chọn cùng loại với hai bug Python — một lỗi biên, một lỗi trạng
thái — để so sánh giữa hai ngôn ngữ công bằng hơn. Mọi bộ test được chấm lại bằng cùng thước đo qua adapter; mutation
chấm trên các mutant LLM chưa từng thấy; bug được tính là phát hiện nếu có test fail trên code lỗi nhưng pass trên bản
đã sửa."

## Slide 11 — Kết quả Python (2 phút, 2 slide)
"Kết quả Python lượt 1, 5 module. Coverage đã khoảng 99% ngay từ lần sinh đầu nên phản hồi coverage gần như không có gì
để cải thiện. Khác biệt thật nằm ở test fail: baseline để lại 1,2 test fail mỗi module; agent đưa về 0, sửa test viết sai
và gắn nhãn đúng cả 2 bug, không nhãn sai. Mutation feedback: nếu chấm như MuTAP, tính cả mutant đã đưa cho AI, thì điểm
tăng từ 83 lên 86 %; nhưng chỉ tính mutant AI chưa thấy thì đứng yên ở 91,8 % — em chỉ thấy được điều này nhờ tách tập
held-out. Đây là chỗ kết quả của em khác MuTAP, và em nghĩ một phần là do cách chấm. Chi phí: số lần gọi LLM tăng từ 1 lên 2,4 đến 3,2. Đây là
1 lần chạy, chỉ là quan sát ban đầu."

## Slide 12 — Kết quả JavaScript/TypeScript (1 phút)
"Với JS em mới có các lần chạy thử agent thật, chưa có lượt thực nghiệm A/B/C/D vì model miễn phí giới hạn 50 request
mỗi ngày — em nói thẳng là phần này chưa đủ số liệu. Hai lần chạy thử cho thấy: cùng vòng lặp chạy được trên TypeScript,
bắt đúng bug `shippingFee(500)` với cả 3 nhãn đúng, coverage 100%, mutation 90%. Với `bank_account`, agent chỉ đúng nguyên
nhân bug, nhưng nhiều test bắt bug bằng cách đọc thuộc tính nội bộ `withdrawnToday` — tức là dựa vào chi tiết cài đặt — và
có 1 nhãn sai; lần chạy này bị dừng vì hết quota nhưng agent dừng êm, vẫn lưu log."
*(Nếu đã chạy xong `evaluate.py --languages javascript`: thay bằng bảng A/B/C/D của JS và biểu đồ
`results/language_comparison.png`.)*

## Slide 13 — Demo (3-4 phút)
Theo `DEMO_CHECKLIST.md` mục C.

## Slide 14 — Hạn chế & hướng phát triển (1 phút 30)
"Hạn chế: mới hiện thực 2 ngôn ngữ và thực nghiệm còn nhỏ; công cụ đo mỗi ngôn ngữ khác nhau nên so sánh chéo chỉ
tương đối; phần JS dùng bộ quét ngoặc nên không gắn nhãn được test nằm trong `describe`; LLM có thể phân loại sai, và test
tối ưu cho mutation có thể bám chi tiết cài đặt. Hướng phát triển: Java với JUnit 5, JaCoCo và PIT — em đã phác thảo
adapter và ước lượng 5 đến 6 ngày; Go; benchmark trên dự án thật và so sánh với Pynguin, EvoSuite."

## Slide 15 — Kết luận (30 giây)
"Tóm lại, em đã xây dựng agent sinh – chạy – đo – sửa chạy được cho Python và JavaScript/TypeScript; kiến trúc Adapter
giúp vòng lặp không phụ thuộc ngôn ngữ, và phần Python được chứng minh không đổi hành vi sau refactor. Phản hồi thực
thi giữ lại test phát hiện bug thay vì sửa cho khớp code sai. Cái giá là nhiều lần gọi LLM hơn, và con người vẫn cần
review. Em cảm ơn thầy cô đã lắng nghe."

---

# 15 câu hỏi giảng viên có thể hỏi (kèm gợi ý trả lời)

**1. Agent của em khác gì so với hỏi ChatGPT viết test?**
→ ChatGPT sinh một lần, không chạy thử. Agent của em **chạy test thật**, đo coverage/mutation, và dùng kết quả đo làm
đầu vào cho lần sinh tiếp theo; đồng thời xử lý oracle problem bằng bước phân loại. Cấu hình A trong thực nghiệm chính
là "hỏi một lần" để so sánh.

**2. Oracle problem là gì, em giải quyết đến đâu?**
→ Là bài toán "làm sao biết kết quả đúng để viết assert". Em dùng docstring/JSDoc làm đặc tả, và khi test fail thì hỏi
LLM test sai hay code sai; nếu nghi code sai thì giữ test và gắn nhãn. Chỉ giải quyết **một phần**: đặc tả mơ hồ hoặc LLM
phân loại sai thì vẫn sai. Em đo tỉ lệ nhãn đúng/sai bằng bản code đã sửa (ví dụ `bank_account`: 8 đúng, 1 sai).

**3. Làm sao em chắc LLM không "nhìn thấy" bug?**
→ Code mục tiêu không có comment nào về bug; `BUGS.md` và bản sửa `evaluation/fixed_targets/` không bao giờ được đưa vào
prompt (kiểm tra được trong `prompts.py` và log JSON). LLM chỉ thấy mã nguồn + đặc tả.

**4. Coverage 100% rồi sao còn cần mutation testing?**
→ Coverage đo code **có chạy qua** không; mutation đo assert **có đủ chặt** không. Ví dụ calculator: coverage 100% nhưng
2 mutant biên còn sống. Bug 4 (JS) còn rõ hơn: coverage 100% vẫn không lộ bug vì bug là một câu lệnh bị **thiếu**.

**5. Mutation testing chậm, em làm thế nào cho demo chạy kịp?**
→ Chỉ đột biến một module, lấy mẫu tối đa 20 mutant với seed cố định, chạy song song; Python dừng ngay khi có test fail;
JS dùng Stryker với phân tích coverage theo từng test và nhớ tạm kết quả. Đánh đổi: điểm là ước lượng trên mẫu.

**6. Thiết kế ghép cặp A/B từ lần chạy C có công bằng không?**
→ A chính là bước sinh đầu tiên của agent (cùng prompt, cùng một lần gọi), B là trạng thái đúng lúc agent kết thúc phase
coverage — chạy B riêng thì B cũng dừng đúng điểm đó. Cách này giảm nhiễu và tiết kiệm khoảng một nửa số request.

**7. Bộ nhớ "tự học" có thật sự học không?**
→ Học theo nghĩa **in-context learning**: tích luỹ kinh nghiệm và đưa lại vào prompt; trọng số không đổi. Thực nghiệm
chưa đủ lớn để kết luận bộ nhớ có tác dụng. Bộ nhớ chia theo ngôn ngữ để tránh đưa kinh nghiệm pytest vào prompt Jest.

**8. Nếu LLM trả về code sai cú pháp hoặc xoá test cũ thì sao?**
→ Code được kiểm tra (Python: `ast.parse`; JS: bộ quét ngoặc) trước khi ghép; sai thì bỏ qua lần đó. LLM chỉ trả về test
mới/đã sửa, chương trình tự ghép nên không xoá được test cũ. File hỏng quá số lần cho phép → quay lui phiên bản chạy được.

**9. Vòng lặp có thể chạy mãi và tốn tiền không?**
→ 4 chốt chặn: số vòng tối đa, dừng khi không cải thiện sau 2 lần, giới hạn số lần sửa mỗi test, timeout mỗi lần chạy.
Hết quota giữa chừng thì agent dừng êm, giữ bộ test tốt nhất (có log mẫu `bank_account_agent_js_*`).

**10. Kết quả của em có tổng quát được không?**
→ Chưa. Module nhỏ tự viết, bug tự cài, một model, ít lần chạy; JS chưa có lượt A/B/C/D. Kết quả cho thấy **xu hướng**
và chứng minh pipeline hoạt động trên 2 ngôn ngữ; muốn tổng quát cần benchmark lớn hơn.

**11. Kiến trúc Adapter là gì, lợi ích cụ thể trong đồ án?**
→ Adapter là "bộ chuyển đổi" giữa giao diện agent cần (`run_tests`, `run_mutation`, `merge_tests`...) và công cụ thật
(pytest, Jest...). Agent chọn adapter theo đuôi file lúc chạy — cũng là tinh thần của Strategy pattern. Lợi ích đo được:
thêm JS **không sửa một dòng logic nào** của vòng lặp, oracle, bộ nhớ, thực nghiệm; giao diện chỉ thêm ô chọn ngôn ngữ.
Refactor được kiểm chứng bằng ảnh chụp hành vi: phần Python giống hệt trước.

**12. Vì sao chọn JavaScript làm ngôn ngữ thứ hai?**
→ (1) Phổ biến nhất (web, Node.js), có hệ sinh thái test trưởng thành: Jest có sẵn coverage, StrykerJS là công cụ mutation
tốt. (2) **Khác Python đủ nhiều** để kiểm chứng kiến trúc: không có `ast` trong Python để đọc file test, cần import kiểu
module, TypeScript có kiểu, Jest không có xfail mà có `test.failing` (hành vi hơi khác — em phải xử lý riêng khi chạy
mutation). (3) Vẫn **động kiểu, không cần biên dịch** như Python nên phù hợp vòng lặp nhanh; Java thì chậm hơn nhiều (JVM +
Maven) và test sai kiểu làm hỏng cả file.

**13. Thêm một ngôn ngữ mới mất bao lâu?**
→ Theo kinh nghiệm làm adapter JS: khoảng **3,5 ngày** (cài công cụ, `run_tests` + đọc báo cáo, `run_mutation`, bộ đọc/sửa
file test, prompt hints, module mục tiêu). Java ước lượng **5–6 ngày** (Maven/JaCoCo/PIT chậm, test nằm trong lớp, không
có "expected failure" chuẩn). Hướng dẫn chi tiết và bảng phương thức cần viết: `docs/THEM_NGON_NGU_MOI.md`.

**14. Đề tài của em dựa trên bài nghiên cứu nào, và khác bài đó ở đâu?**
→ Dựa trên **MuTAP** (Dakhel và cộng sự, Information and Software Technology, 2024): dùng mutant còn sống làm phản hồi
cho LLM. Em khác ở: (1) không mặc định code đúng — phân loại test fail theo đặc tả, giữ test nghi bug; (2) gửi kèm thông
báo lỗi khi sửa test; (3) thêm phản hồi coverage; (4) chấm mutation trên tập held-out; (5) đa ngôn ngữ qua Adapter.
Chi tiết: `docs/BAO_CAO_MUTAP.md`.

**15. MuTAP thấy mutation feedback giúp nhiều, sao của em không?**
→ Ba lý do có thể: (1) MuTAP chấm trên chính các mutant đã đưa vào prompt; khi em chấm như vậy cũng thấy tăng (83 → 86 %),
chỉ trên tập held-out mới không tăng; (2) module của em nhỏ, điểm ban đầu đã cao (89–92 %) nên ít chỗ để tăng; (3) em mới
chạy 1 lượt với 5 module nên chưa đủ để kết luận. Em không khẳng định MuTAP sai, chỉ nói cách chấm ảnh hưởng tới kết luận.
