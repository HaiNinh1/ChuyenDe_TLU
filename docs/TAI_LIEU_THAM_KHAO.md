# Tài liệu tham khảo — ghi chú đọc

Dùng cho slide "Tổng quan tài liệu" (buổi họp nhóm) và phần *Công trình liên quan* của báo cáo.
Số thứ tự `[n]` trùng với slide. Mỗi mục có: nơi công bố, DOI/đường dẫn, **ý chính** (số liệu trích từ phần tóm tắt
của bài), và **liên hệ với đồ án**.

Tất cả đã được kiểm tra là có thật qua DOI / arXiv / trang nhà xuất bản (26/09/2026). Các điểm chưa chắc chắn ghi ở
mục cuối. **Trước khi trình bày: tự đọc ít nhất phần tóm tắt + phương pháp của từng bài, đọc kỹ 6 bài đánh dấu ★.**

## A. Nền tảng: coverage, mutation testing, oracle

**[1]** R. A. DeMillo, R. J. Lipton, F. G. Sayward. *Hints on Test Data Selection: Help for the Practicing
Programmer.* IEEE Computer 11(4):34–41, 1978. https://doi.org/10.1109/C-M.1978.218136
- Bài khởi đầu mutation testing; *hiệu ứng ghép cặp* (coupling effect): test bắt được lỗi đơn giản cũng bắt được phần
  lớn lỗi phức tạp hơn.
- Đồ án: lý do dùng các mutant nhỏ (mutmut / Stryker) làm tín hiệu phản hồi.

**[2]** Y. Jia, M. Harman. *An Analysis and Survey of the Development of Mutation Testing.* IEEE TSE 37(5):649–678,
2011. https://doi.org/10.1109/TSE.2010.62
- Khảo sát hơn 390 bài (1977–2009): lý thuyết, giảm chi phí, mutant tương đương, công cụ.
- Đồ án: thuật ngữ mutation score, mutant bị giết / sống sót / tương đương.

**[3]** M. Papadakis, M. Kintis, J. Zhang, Y. Jia, Y. Le Traon, M. Harman. *Mutation Testing Advances: An Analysis and
Survey.* Advances in Computers 112, ch. 6, 2019. https://doi.org/10.1016/bs.adcom.2018.03.015
- Mutation dùng để đánh giá bộ test, dẫn hướng sinh test và làm thực nghiệm; có "sổ tay nhỏ" về cách dùng mutation
  trong nghiên cứu thực nghiệm.
- Đồ án: cơ sở cho cách chấm cẩn thận (mutation held-out, nhiều lượt chạy).

**[4]** R. Just, D. Jalali, L. Inozemtseva, M. D. Ernst, R. Holmes, G. Fraser. *Are Mutants a Valid Substitute for
Real Faults in Software Testing?* FSE 2014, 654–665. https://doi.org/10.1145/2635868.2635929
- 357 lỗi thật, 5 ứng dụng, 321.000 dòng code: phát hiện mutant tương quan có ý nghĩa thống kê với phát hiện lỗi
  thật, độc lập với coverage.
- Đồ án: căn cứ dùng mutation score như thước đo khả năng bắt bug.

**[5] ★** L. Inozemtseva, R. Holmes. *Coverage Is Not Strongly Correlated with Test Suite Effectiveness.* ICSE 2014
(Distinguished Paper). https://doi.org/10.1145/2568225.2568271
- 31.000 bộ test, 5 hệ thống Java đến 724.000 LOC: tương quan coverage – hiệu quả chỉ thấp đến vừa khi cố định số
  lượng test; coverage không nên là mục tiêu chất lượng.
- Đồ án: lý do vòng lặp không dừng ở coverage mà thêm mutation.

**[6]** G. Petrović, M. Ivanković, G. Fraser, R. Just. *Practical Mutation Testing at Scale: A View from Google.* IEEE
TSE 48(10):3900–3912, 2022. https://doi.org/10.1109/TSE.2021.3107634 (arXiv:2102.11378)
- Mutation tăng dần trong code review, lọc mutant không liên quan; hơn 24.000 lập trình viên, hơn 1.000 dự án.
  (Bài trước: *State of Mutation Testing at Google*, ICSE-SEIP 2018, https://doi.org/10.1145/3183519.3183521)
- Đồ án: giới hạn và chọn mẫu mutant gửi cho LLM.

**[7] ★** E. T. Barr, M. Harman, P. McMinn, M. Shahbaz, S. Yoo. *The Oracle Problem in Software Testing: A Survey.*
IEEE TSE 41(5):507–525, 2015. https://doi.org/10.1109/TSE.2014.2372785
- Oracle problem: phân biệt hành vi đúng mong muốn với hành vi có thể sai; con người vẫn là nguồn oracle cuối cùng.
- Đồ án: bước phân loại `TEST_WRONG` / `SUSPECTED_BUG`, và lý do nhãn nghi bug cần người duyệt.

**[8]** P. Ammann, J. Offutt. *Introduction to Software Testing*, 2nd ed. Cambridge University Press, 2016.
https://www.cambridge.org/9781107172012
- Chương 7 (graph coverage), 8 (logic coverage), 9 (syntax-based testing — mutation), 14 (test oracle).
- Đồ án: định nghĩa line / branch coverage và mutation adequacy.

## B. Sinh test tự động không dùng LLM

**[9]** C. Pacheco, S. K. Lahiri, M. D. Ernst, T. Ball. *Feedback-Directed Random Test Generation* (Randoop). ICSE
2007, 75–84. https://doi.org/10.1109/ICSE.2007.37
- Sinh chuỗi lời gọi, chạy ngay, dùng kết quả để loại đầu vào thừa / không hợp lệ; tìm lỗi mới trong 14 thư viện
  (780 KLOC).
- Đồ án: tổ tiên ý tưởng "sinh → chạy → dùng phản hồi".

**[10]** G. Fraser, A. Arcuri. *EvoSuite: Automatic Test Suite Generation for Object-Oriented Software.* ESEC/FSE
2011, 416–419. https://doi.org/10.1145/2025113.2025179
- Thuật toán di truyền tối ưu cả bộ test JUnit theo coverage, sinh assert hồi quy.

**[11]** S. Lukasczyk, G. Fraser. *Pynguin: Automated Unit Test Generation for Python.* ICSE 2022 Companion.
https://doi.org/10.1145/3510454.3516829 · https://www.pynguin.eu
- Sinh test dựa trên tìm kiếm cho Python (kiểu động). Đồ án: baseline cổ điển để so sánh (kế hoạch).

## C. LLM sinh unit test

**[12]** J. Wang, Y. Huang, C. Chen, Z. Liu, S. Wang, Q. Wang. *Software Testing with Large Language Models: Survey,
Landscape, and Vision.* IEEE TSE, 2024. https://arxiv.org/abs/2307.07221
- Khảo sát 102 nghiên cứu về LLM trong kiểm thử. Đồ án: điểm xuất phát để tìm tài liệu.

**[13]** C. Lemieux, J. P. Inala, S. K. Lahiri, S. Sen. *CodaMosa: Escaping Coverage Plateaus in Test Generation with
Pre-trained Large Language Models.* ICSE 2023. https://doi.org/10.1109/ICSE48619.2023.00085
- Chạy tìm kiếm (Pynguin/MOSA) đến khi coverage đứng yên, rồi gọi Codex sinh ví dụ cho hàm ít được phủ.
- Đồ án: coverage làm tín hiệu gọi LLM; đồ án thì gọi LLM trước và gửi đúng dòng/nhánh chưa phủ.

**[14] ★** M. Schäfer, S. Nadi, A. Eghbali, F. Tip. *An Empirical Evaluation of Using Large Language Models for
Automated Unit Test Generation* (TestPilot). IEEE TSE 50(1):85–105, 2024. https://doi.org/10.1109/TSE.2023.3334955
- JavaScript/npm; prompt có chữ ký hàm, phần cài đặt, ví dụ trong tài liệu; test fail thì gửi lại kèm lỗi.
  gpt-3.5-turbo trên 25 gói npm (1.684 hàm): trung vị 70,2 % statement coverage, 52,8 % branch coverage.
- Đồ án: công trình gần nhất cho adapter JS; căn cứ chọn JS làm ngôn ngữ thứ hai.

**[15]** Z. Yuan, M. Liu, S. Ding, K. Wang, Y. Chen, X. Peng, Y. Lou. *Evaluating and Improving ChatGPT for Unit Test
Generation* (ChatTester; bản arXiv tên "No More Manual Tests?…"). Proc. ACM Softw. Eng. 1(FSE), 2024.
https://doi.org/10.1145/3660783
- ChatTester: nhiều hơn 34,3 % test biên dịch được và 18,7 % test có assert đúng so với ChatGPT mặc định.
- Đồ án: bước LLM sửa test lỗi.

**[16]** Y. Chen, Z. Hu, C. Zhi, J. Han, S. Deng, J. Yin. *ChatUniTest: A Framework for LLM-Based Test Generation.* FSE
Companion 2024. https://doi.org/10.1145/3663529.3663801
- Vòng "sinh – kiểm – sửa" cho Java.

**[17]** M. L. Siddiq et al. *Using Large Language Models to Generate JUnit Tests: An Empirical Study.* EASE 2024.
https://arxiv.org/abs/2305.00418
- Đánh giá Codex, GPT-3.5, StarCoder sinh JUnit: tỉ lệ biên dịch, coverage, test smell. (Chưa trích số — xem cuối.)

**[18]** Y. Tang, Z. Liu, Z. Zhou, X. Luo. *ChatGPT vs SBST: A Comparative Assessment of Unit Test Suite Generation.*
IEEE TSE 50:1340–1359, 2024. https://doi.org/10.1109/TSE.2024.3382365
- So sánh ChatGPT với EvoSuite: đúng, dễ đọc, coverage, bắt bug. Đồ án: căn cứ cho việc so với công cụ cổ điển.

**[19]** G. Ryan, S. Jain, M. Shang, S. Wang, X. Ma, M. K. Ramanathan, B. Ray. *Code-Aware Prompting: A Study of
Coverage-Guided Test Generation in Regression Setting using LLM* (SymPrompt). Proc. ACM Softw. Eng. 1(FSE), 2024.
https://doi.org/10.1145/3643769
- Prompt nhiều bước theo từng đường thực thi; với GPT-4 coverage tăng hơn 2 lần so với prompt thường.

**[20] ★** N. Alshahwan et al. *Automated Unit Test Improvement using Large Language Models at Meta* (TestGen-LLM). FSE
Companion 2024. https://doi.org/10.1145/3663529.3663839
- LLM mở rộng test có sẵn; chỉ giữ test qua bộ lọc: 75 % build được, 57 % pass ổn định, 25 % tăng coverage; 73 % đề
  xuất được chấp nhận đưa vào sản phẩm.
- Đồ án: tinh thần "kiểm chứng rồi mới giữ" (ghép test, lưu bài học chỉ khi đã xác nhận).

**[21] ★** A. M. Dakhel, A. Nikanjam, V. Majdinasab, F. Khomh, M. C. Desmarais. *Effective Test Generation Using
Pre-trained Large Language Models and Mutation Testing* (MuTAP). Information and Software Technology, 2024.
https://doi.org/10.1016/j.infsof.2024.107468
- Đưa mutant còn sống vào prompt (Python); phát hiện thêm tới 28 % đoạn code lỗi; mutation score 93,57 % trên code
  lỗi tổng hợp.
- Đồ án: bước "giết mutant"; đồ án thêm chấm trên mutant held-out.

**[22] ★** J. Altmayer Pizzorno, E. D. Berger. *CoverUp: Effective High Coverage Test Generation for Python* (bản arXiv:
"Coverage-Guided LLM-Based Test Generation"). Proc. ACM Softw. Eng. 2(FSE), 2025. https://doi.org/10.1145/3729398
- Gửi dòng/nhánh còn thiếu + ngữ cảnh code, lặp lại. Trung vị theo module 80 % so với 47 % (CodaMosa); tổng 89 % so
  với 77 % (MuTAP).
- Đồ án: bước "tăng coverage".

**[23]** C. Foster, A. Gulati, M. Harman, I. Harper, K. Mao, J. Ritchey, H. Robert, S. Sengupta. *Mutation-Guided
LLM-based Test Generation at Meta* (ACH). FSE Companion 2025. https://doi.org/10.1145/3696630.3728544
- LLM sinh mutant có mục tiêu rồi sinh test giết chúng; 10.795 lớp Kotlin, 9.095 mutant, 571 test; kỹ sư chấp nhận
  73 %. Phát hiện mutant tương đương: precision 0,79, recall 0,47 (0,95 / 0,96 sau tiền xử lý).
- Đồ án: bằng chứng công nghiệp cho mutation-guided; vấn đề mutant tương đương (đồ án cũng gặp).

**[24]** G. Wang, Q. Xu, L. Briand, K. Liu. *Mutation-Guided Unit Test Generation with a Large Language Model*
(MutGen). IEEE TSE (accepted). https://arxiv.org/abs/2506.02954
- Đưa báo cáo mutation (vị trí, trạng thái, toán tử) vào prompt, lặp theo mutant còn sống; vượt EvoSuite và prompt
  thường về mutation score trên 204 đối tượng. Nêu ví dụ bộ test 100 % coverage nhưng chỉ 4 % mutation score.

**[25]** K. Jain, G. Synnaeve, B. Rozière. *TestGenEval: A Real World Unit Test Generation and Test Completion
Benchmark.* ICLR 2025. https://arxiv.org/abs/2410.00752
- 1.210 cặp file code–test từ 11 repo Python; model tốt nhất (GPT-4o) coverage trung bình chỉ 35,2 %.

**[26]** Y. Wang et al. *MultiFileTest: A Multi-File-Level LLM Unit Test Generation Benchmark and Impact of Error Fixing
Mechanisms* (trước tên ProjectTest). Findings of ACL 2026. https://arxiv.org/abs/2502.06556
- Benchmark Python, Java, JavaScript; LLM mạnh vẫn mắc lỗi cơ bản (không chạy được, lỗi dây chuyền); có đánh giá tự
  sửa lỗi. Đồ án: tài liệu đa ngôn ngữ gần nhất.

**[27]** G. Go, Q. Zhang, C. Zhou, Z. Wei, Y. Jiang. *LSPRAG: LSP-Guided RAG for Language-Agnostic Real-Time Unit Test
Generation.* arXiv:2510.22210, 2025. https://arxiv.org/abs/2510.22210
- Dùng Language Server có sẵn để lấy ngữ cảnh cho nhiều ngôn ngữ (Java, Go, Python). Đồ án: một cách "đa ngôn ngữ"
  khác (ngữ cảnh), so với Adapter của đồ án (chạy, đo, mutation).

**[28]** J. Zhao, S. Zhou, E. Cohen. *Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated
Unit Tests.* ISSTA 2026, PACMSE 3(ISSTA), Article ISSTA113. https://arxiv.org/abs/2607.22883
- Code có bug "dẫn dắt sai" LLM: tăng test khẳng định hành vi sai, giảm test bắt bug; đề xuất thay code trong prompt
  bằng docstring đặc tả do LLM sinh — giảm test sai, tăng test hiệu quả, cải thiện cả pipeline nhiều vòng có phản hồi.
- Đồ án: đúng hiện tượng "hợp thức hoá bug"; hướng thử nghiệm tiếp theo.

## D. Agent và tự cải tiến

**[29]** S. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR 2023.
https://arxiv.org/abs/2210.03629 — xen kẽ suy luận và hành động trên công cụ.

**[30] ★** N. Shinn et al. *Reflexion: Language Agents with Verbal Reinforcement Learning.* NeurIPS 2023.
https://arxiv.org/abs/2303.11366
- Học từ phản hồi bằng cách viết ra bài học và lưu vào bộ nhớ, không cập nhật trọng số; 91 % pass@1 trên HumanEval
  (GPT-4 trước đó 80 %). Đồ án: bộ nhớ bài học JSON (học trong ngữ cảnh).

**[31]** A. Madaan et al. *Self-Refine: Iterative Refinement with Self-Feedback.* NeurIPS 2023.
https://arxiv.org/abs/2303.17651 — sinh → tự nhận xét → sửa; cải thiện trung bình ~20 % tuyệt đối trên 7 nhiệm vụ.
Đồ án khác: phản hồi đến từ công cụ đo thật.

**[32]** X. Chen, M. Lin, N. Schärli, D. Zhou. *Teaching Large Language Models to Self-Debug.* ICLR 2024.
https://arxiv.org/abs/2304.05128 — chạy code, giải thích, tự sửa. Đồ án: bước sửa file test lỗi.

**[33]** Anthropic (E. Schluntz, B. Zhang). *Building Effective Agents.* Anthropic Engineering, 19/12/2024.
https://www.anthropic.com/engineering/building-effective-agents
- "The most successful implementations weren't using complex frameworks or specialized libraries. Instead, they were
  building with simple, composable patterns." Mẫu *evaluator–optimizer*.
- Đồ án: lý do tự viết vòng lặp, không dùng LangChain.

## E. Thiết kế phần mềm và công cụ

**[34]** E. Gamma, R. Helm, R. Johnson, J. Vlissides. *Design Patterns: Elements of Reusable Object-Oriented
Software.* Addison-Wesley, 1994. Hướng dẫn dễ đọc: https://refactoring.guru/design-patterns/adapter ,
https://refactoring.guru/design-patterns/strategy — Adapter (`LanguageAdapter`), Strategy (registry chọn adapter).

**[35]** M. C. Feathers. *Working Effectively with Legacy Code.* Prentice Hall, 2004. — *characterization test*: test
ghi lại hành vi hiện tại để giữ nguyên khi sửa code → `scripts/snapshot_python.py`.

**[36]** M. Fowler. *Refactoring: Improving the Design of Existing Code*, 2nd ed. Addison-Wesley, 2018.
https://martinfowler.com/bliki/SelfTestingCode.html — refactor an toàn nhờ "self-testing code".

**[37]** Tài liệu chính thức của công cụ:
- pytest: https://docs.pytest.org/en/stable/ (xfail: https://docs.pytest.org/en/stable/how-to/skipping.html)
- coverage.py: https://coverage.readthedocs.io/ (branch: https://coverage.readthedocs.io/en/latest/branch.html)
- mutmut: https://mutmut.readthedocs.io/ (bản 3.x cần `fork` → trên Windows phải dùng WSL; đồ án ghim 2.5.1)
- Jest: https://jestjs.io/docs/getting-started (`test.failing`: https://jestjs.io/docs/api#testfailingname-fn-timeout)
- Istanbul: https://istanbul.js.org/
- StrykerJS: https://stryker-mutator.io/docs/stryker-js/introduction/ (Jest runner:
  https://stryker-mutator.io/docs/stryker-js/jest-runner/)

## Ghi chú xác minh (điểm chưa chắc chắn)
- [12]: arXiv ghi "Accepted by IEEE TSE"; chưa đối chiếu DOI chính thức.
- [17]: số liệu (coverage > 80 % trên HumanEval, < 2 % trên SF110) lấy từ bản tóm lược, chưa đối chiếu nguyên văn →
  không đưa lên slide.
- [24]: bản arXiv v1 tháng 6/2025, ghi "accepted in IEEE TSE"; chưa có số tập/trang.
- [27]: arXiv có liên kết DOI 10.1145/3744916.3773189 (hội nghị ACM 2026) nhưng chưa xác nhận tên hội nghị.
- [30]: danh sách tác giả bản NeurIPS và bản arXiv v4 khác nhau (có/không có E. Berman) — khi trích dẫn chọn một bản.
- [1]: giả thuyết "lập trình viên có năng lực" thường được gán cho bài này; chưa kiểm tra nguyên văn.
- [35]: định nghĩa characterization test lấy từ nguồn thứ cấp, chưa đối chiếu sách.
