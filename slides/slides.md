---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 28px; }
  h1 { color: #1f4e9a; }
  h2 { color: #1f4e9a; }
  code { font-size: 0.85em; }
  table { font-size: 0.8em; }
  pre { font-size: 0.72em; }
  .small { font-size: 0.7em; color: #555; }
  .red { color: #c0392b; font-weight: bold; }
  .green { color: #1e8449; font-weight: bold; }
---

<!-- _paginate: false -->

# LLM Agent tự sinh unit test đa ngôn ngữ

### Vòng lặp tự cải tiến dựa trên phản hồi coverage và mutation testing

<br>

Sinh viên: ……………… · MSSV: ………………
Giảng viên hướng dẫn: ………………
Môn: ……………… · 2026

---

## 1. Vấn đề

- Viết unit test **tốn thời gian**, hay bị bỏ qua
- LLM viết test rất nhanh, **nhưng**:
  - test có thể **không chạy được** (sai import, sai cú pháp)
  - test có thể **thiếu** nhánh quan trọng
  - test có thể **sai**, hoặc tệ hơn: **"hợp thức hoá" bug**
    ```python
    assert letter_grade(80) == "C"   # code sai, test viết theo code sai
    ```
- ❓ Làm sao để LLM **tự kiểm tra và cải thiện** bộ test — cho **nhiều ngôn ngữ**, không viết lại từ đầu?

---

## 2. Các hướng tiếp cận hiện có

| Hướng | Ví dụ | Ưu | Nhược |
|---|---|---|---|
| Tìm kiếm / tiến hoá | **EvoSuite** (Java), **Pynguin** (Python) | coverage cao, có hệ thống | assert "chụp" hành vi hiện tại; **mỗi công cụ một ngôn ngữ** |
| LLM sinh một lần | ChatGPT, Copilot | test dễ đọc, hiểu docstring | không kiểm chứng, hay lỗi |
| **LLM + phản hồi** | CoverUp, MuTAP, TestPilot… | kết hợp cả hai | tốn nhiều lần gọi LLM; thường gắn 1 ngôn ngữ |

➡️ Đồ án: **LLM + vòng lặp phản hồi**, tự cài đặt đơn giản, tách phần phụ thuộc ngôn ngữ ra **Adapter**.

---

<style scoped>li { font-size: 0.85em; } table { font-size: 0.72em; }</style>

## 2.1. Bài nghiên cứu nền tảng: MuTAP

**Dakhel và cộng sự**, *Effective Test Generation Using Pre-trained LLMs and Mutation Testing*,
Information and Software Technology, 2024 — [doi:10.1016/j.infsof.2024.107468](https://doi.org/10.1016/j.infsof.2024.107468)

**Ý tưởng:** mutant còn sống cho LLM biết **chính xác** bộ test đang bỏ sót lỗi nào → đưa mutant đó vào prompt

1. LLM sinh test → 2. sửa cú pháp → 3. **sửa giá trị mong đợi theo kết quả của code**
4. đo mutation (MutPy) → 5. chưa đạt 100 %: thêm **1 mutant sống** vào prompt, sinh thêm → lặp 4–5 → 6. rút gọn bộ test

| Kết quả (llama-2-chat few-shot) | MuTAP | Pynguin |
|---|---|---|
| HumanEval — mutation score | 93,57 % | 65,94 % |
| Refactory (lỗi thật của sinh viên) — phát hiện | 94,91 % | 67,54 % |

<span class="small">Số liệu trích từ bài (bản arXiv 2308.16557), không phải do em chạy lại.</span>

---

<style scoped>table { font-size: 0.7em; } li { font-size: 0.85em; }</style>

## 2.2. Kế thừa và cải tiến so với MuTAP

| | MuTAP | Đồ án |
|---|---|---|
| Mutant còn sống làm phản hồi | ✓ | ✓ **kế thừa** |
| Test fail trên code | sửa test **cho khớp code** (giả định code đúng) | so với **đặc tả**: test sai → sửa; nghi code sai → **giữ test**, gắn `SUSPECTED_BUG` |
| Sửa test hỏng | chỉ yêu cầu sửa lại | gửi kèm **thông báo lỗi thật** |
| Phản hồi coverage | — | có, chạy trước mutation |
| Chấm mutation score | trên **chính các mutant đã đưa vào prompt** | thêm tập **held-out** (mutant LLM chưa thấy) |
| Ngôn ngữ | Python | Python + JS/TS (Adapter) |

- Hai điểm yếu của MuTAP mà đồ án nhắm tới: **oracle problem** (bước 3 hợp thức hoá bug) và **chấm trên đề đã lộ**

---

## 3. Mục tiêu và phạm vi

**Mục tiêu**
- Agent sinh test → **chạy, đo** → dùng kết quả đo để **tự sửa / bổ sung**
- Xử lý **oracle problem**: test fail là do *test sai* hay *code sai*?
- **Một vòng lặp, nhiều ngôn ngữ** (kiến trúc Adapter); so sánh định lượng 4 cấu hình

**Phạm vi**
- **2 ngôn ngữ**: Python (5 module) và JavaScript/TypeScript (4 module); **4 bug cài sẵn**
- Không dùng LangChain / framework agent — vòng lặp tự viết
- LLM qua API (OpenRouter / DeepSeek / OpenAI / Claude / Ollama)

---

## 4. Kiến trúc Adapter

```
                  prompt = common template + language hints
 +-----------------+  ------------------------------------>  +-------+
 |  AGENT (for+if) |                                         |  LLM  |
 | language-blind  |  <------------------------------------  +-------+
 +--------+--------+               test code
          |  run_tests() get_coverage() run_mutation() merge_tests() add_suspected_marker()
          v
 +-----------------------+          registry: file extension -> adapter
 |  LanguageAdapter (ABC)|
 +-----+-----------+-----+
       |           |                      .  (future work)
       v           v                      v
 +-----------+ +----------------+ +--------------+
 | Python    | | JavaScript/TS  | | Java         |
 | pytest    | | Jest           | | JUnit 5      |
 | coverage  | | Istanbul       | | JaCoCo       |
 | mutmut    | | StrykerJS      | | PIT          |
 +-----------+ +----------------+ +--------------+
```

<span class="small">Thêm ngôn ngữ = viết 1 lớp con + 1 dòng đăng ký. Vòng lặp, oracle, bộ nhớ, thực nghiệm, giao diện dùng lại nguyên vẹn.</span>

---

## 5. Vòng lặp tự cải tiến

1. LLM **sinh** bộ test ban đầu
2. **Chạy** test + đo coverage (qua adapter)
3. File lỗi cú pháp/import → LLM **sửa cả file**
4. Test fail → LLM **phân loại**:
   - `TEST_WRONG` → sửa test đó
   - `SUSPECTED_BUG` → <span class="red">GIỮ test</span>, gắn nhãn `xfail` (Python) / `test.failing` (Jest)
5. Coverage < ngưỡng → gửi **dòng/nhánh chưa phủ** → LLM viết thêm
6. Mutation score < ngưỡng → gửi **mutant còn sống** → LLM viết thêm
7. Dừng: đạt ngưỡng · không cải thiện 2 lần · hết số vòng

<span class="small">LLM chỉ trả về test mới/đã sửa; chương trình tự ghép (Python: `ast`; JS: bộ quét ngoặc) → LLM không thể xoá test cũ.</span>

---

## 6. Coverage — ví dụ

```python
def pass_status(score, attendance_rate):
    if attendance_rate < 0.7:      # nhánh True / False
        return "CẤM THI"
    if score >= 50:
        return "ĐẬU"
    ...
```

- **Line coverage**: bao nhiêu % dòng được chạy · **Branch coverage**: bao nhiêu % *nhánh* được đi qua
- Agent gửi cho LLM đúng chỗ chưa phủ, **mô tả theo công cụ của từng ngôn ngữ**:
  - Python: *"Nhánh từ dòng 2 sang `return "CẤM THI"` chưa được đi qua"*
  - JS: *"case thứ 2 của switch ở dòng 33 (`switch (zone) {`) chưa được đi qua"*

---

## 7. Mutation testing — ví dụ

Coverage 100% ≠ test tốt. **Mutant** = code bị sửa nhẹ một chỗ:

```python
if score >= 90: return "A"     ─►     if score > 90: return "A"     # mutant
```

| Test | Code gốc | Mutant | Kết luận |
|---|---|---|---|
| `letter_grade(95) == "A"` | pass | pass | mutant **sống sót** → test chưa đủ chặt |
| `letter_grade(90) == "A"` | pass | **fail** | mutant **bị giết** <span class="green">✓</span> |

**Mutation score** = mutant bị giết / tổng mutant

<span class="small">Python: toán tử mutmut 2.5.1 + runner tự viết (mutmut 3 không chạy trên Windows). JS/TS: StrykerJS. Chưa cài / lỗi → "không khả dụng", agent vẫn chạy phần coverage.</span>

---

## 8. Bộ nhớ "tự học" — theo từng ngôn ngữ

- File **JSON**: **bài học sửa lỗi** (chỉ lưu khi vòng sau xác nhận lỗi đã hết) + **mẫu test tốt**
- Chọn kinh nghiệm liên quan theo **nhãn** của module (`class`, `exception`, `branches`…)
- **Chia theo ngôn ngữ**: prompt Jest không nhận bài học "dùng `pytest.approx`"
  → tránh *chuyển giao tiêu cực*; dữ liệu cũ (chỉ Python) được **tự chuyển đổi**, không mất

⚠️ "Học" = **học trong ngữ cảnh** (in-context learning):
trọng số LLM **không đổi**, chỉ có thêm "sổ tay kinh nghiệm" trong prompt.

---

## 9. Refactor an toàn: chứng minh phần Python không hỏng

Chụp hành vi **trước** refactor → so sánh **sau mỗi bước**:

| Kiểm tra | Kết quả |
|---|---|
| Mã băm 8 prompt Python | **giống từng ký tự** |
| Chạy lại 4 bộ test đã lưu: pass/fail, coverage, dòng chưa phủ | **giống hệt** |
| Trạng thái **từng mutant** (160 mutant) | **giống hệt** |
| Agent + LLM giả lập (7 hành động, có mutation) | **giống hệt** |
| Chấm lại thực nghiệm cũ (`evaluate --measure-only`) | `results.csv` **giống từng byte** |
| Agent + **LLM thật** (`grading`, không tất định) | tương đương: cùng hành động, 97,5/96,9 %, mutation 95 % |

<span class="small">`scripts/snapshot_python.py` · 117 test của công cụ (64 cũ + 53 mới) · review độc lập: 17 lỗi ở phần JS/chấm đã sửa.</span>

---

## 10. Thiết lập thực nghiệm

| Cấu hình | Mô tả |
|---|---|
| **A** | Baseline — sinh test một lần |
| **B** | Agent + phản hồi coverage |
| **C** | B + mutation testing |
| **D** | C + bộ nhớ |

- Python 5 module (bug 1–2) · JS/TS 4 module (bug 3–4, cùng loại: 1 lỗi biên + 1 lỗi trạng thái)
- **Chấm lại công bằng** qua adapter; mutation chấm trên mutant **LLM chưa thấy** (held-out)
- **Phát hiện bug** = test fail trên code lỗi **và** pass trên bản đã sửa
- LLM: `nemotron-3-super-120b` (miễn phí, OpenRouter, **50 request/ngày**)

---

<style scoped>table { font-size: 0.68em; } li { font-size: 0.85em; }</style>

## 11. Kết quả — Python (lượt 1)

| Cấu hình | Line / branch | Mutation held-out | Test fail còn lại | Bug gắn nhãn đúng | Gọi LLM |
|---|---|---|---|---|---|
| **A** Baseline | 99 / 98 % | 89.1 % | 1.2 / module | 0 / 2 | 1.0 |
| **B** + coverage | 99 / 98 % | 91.8 % | **0** | **2 / 2** | 2.4 |
| **C** + mutation | 99 / 98 % | 91.8 % | **0** | **2 / 2** | 2.6 |
| **D** + memory | 99 / 98 % | 91.8 % | **0** | **2 / 2** | 3.2 |

- Coverage **đã bão hoà** ngay lần sinh đầu → khác biệt nằm ở **xử lý test fail**: 0 nhãn sai (FP)
- Mutation feedback (B → C): chấm **như MuTAP** (gồm mutant đã đưa cho LLM) 83,0 → 86,0 %;
  chấm **held-out** 91,8 → 91,8 % → **không** tăng trên mutant mới

<span class="small">5 module × 1 lần chạy — quan sát ban đầu, chưa có ý nghĩa thống kê.</span>

---

## 11. Kết quả — Python (biểu đồ)

![h:560](../results/summary_python.png)

---

<style scoped>table { font-size: 0.7em; } li { font-size: 0.85em; }</style>

## 12. Kết quả — JavaScript/TypeScript (chạy thử agent thật)

| Module | Hành động | Line / branch | Mutation | Nhãn nghi bug đúng / sai |
|---|---|---|---|---|
| `shipping.ts` (bug 3, biên) | sửa test → tăng coverage → dừng | **100 / 100 %** | 90 % | **3 / 0** |
| `bank_account.js` (bug 4, trạng thái) | … → **hết quota, dừng êm** | 96.6 / 95 % | — | 8 / **1** |

- Cùng một vòng lặp chạy được trên **TypeScript**: bắt đúng bug `shippingFee(500)`
- `bank_account`: nhiều test "bắt bug" bằng cách đọc thuộc tính nội bộ `withdrawnToday` → **bám chi tiết cài đặt**
- **Thực nghiệm A/B/C/D cho JS: chưa có số liệu** (hết hạn mức 50 request/ngày) → `python evaluate.py --languages javascript`

<span class="small">Chỉ số "đúng" = test fail trên code lỗi nhưng pass trên bản đã sửa bug. Không có số nào được điền tay.</span>

---

## 13. Demo

**Streamlit** — `streamlit run app.py`

1. Chọn ngôn ngữ **JavaScript/TypeScript** → `shipping.ts` → thanh bên hiện *Jest + Istanbul + StrykerJS*
2. **Chạy agent** → LLM phân loại test fail là **SUSPECTED_BUG** → `test.failing`, <span class="red">tô đỏ</span>
3. Chọn **Python** → `grading.py`: cùng vòng lặp, công cụ khác
4. **Dán code** bất kỳ → tự nhận diện Python / JavaScript / TypeScript

<span class="small">Dự phòng: chế độ **REPLAY** phát lại từ log JSON của cả hai ngôn ngữ — không cần mạng.</span>

---

<style scoped>li { font-size: 0.82em; } p { margin: 0.3em 0; }</style>

## 14. Hạn chế & hướng phát triển

**Hạn chế**
- **Mới hiện thực 2 ngôn ngữ**; thực nghiệm nhỏ (Python 1 lượt, JS chưa có lượt A/B/C/D), 1 model miễn phí
- Công cụ đo khác nhau giữa ngôn ngữ (coverage.py vs Istanbul, mutmut vs Stryker) → so sánh chéo chỉ **tương đối**
- JS không có parser trong Python → bộ quét ngoặc: không gắn nhãn được test trong `describe`
- LLM có thể **phân loại sai**; test tối ưu mutation có thể **bám chi tiết cài đặt**

**Hướng phát triển**
- **Java** (JUnit 5 + JaCoCo + PIT) — đã phác thảo adapter, ước lượng 5–6 ngày; **Go** (`go test -cover`, go-mutesting)
- Benchmark dự án thật, so sánh với Pynguin / EvoSuite; bộ nhớ dùng embedding; tích hợp CI

---

## 15. Kết luận

- Agent **sinh → chạy → đo → sửa/bổ sung** hoàn chỉnh, không framework, chạy được cho **Python và JS/TS**
- **Kiến trúc Adapter**: vòng lặp không biết ngôn ngữ; phần Python được **chứng minh không đổi hành vi**
- **Phản hồi thực thi** đưa test fail về 0 và **giữ lại test phát hiện bug** thay vì sửa cho khớp code sai
  (Python 2/2 bug; TypeScript bắt đúng bug biên)
- Kế thừa ý tưởng của **MuTAP**, bổ sung phân loại test fail theo đặc tả và chấm held-out
- Mutation feedback **chưa** cải thiện trên mutant mới — phải chấm held-out mới thấy (cách chấm của MuTAP không thấy được)
- Đổi lại: nhiều lần gọi LLM hơn, và vẫn cần con người review nhãn SUSPECTED_BUG

<br>

### Cảm ơn thầy/cô đã lắng nghe! 🙏
