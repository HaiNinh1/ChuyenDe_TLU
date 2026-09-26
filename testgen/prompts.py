"""Toàn bộ prompt gửi cho LLM nằm ở đây để dễ đọc, dễ chỉnh — KHUNG CHUNG cho mọi ngôn ngữ.

Phần riêng của từng ngôn ngữ (tên framework test, cú pháp import, cách viết ngoại lệ, nhãn nghi bug...)
lấy từ `hints = adapter.prompt_hints()` (xem adapters/python_adapter.py: PYTHON_HINTS).
Với Python, các prompt ghép ra GIỐNG HỆT TỪNG KÝ TỰ bản trước refactor (đã kiểm tra bằng mã băm).

Nguyên tắc chung của các prompt:
- Luôn đưa ĐẶC TẢ (docstring / JSDoc) và yêu cầu LLM viết assert theo đặc tả, không theo cài đặt
  -> giảm "oracle problem" (test hợp thức hoá bug).
- Yêu cầu trả về đúng MỘT khối code để code dễ tách ra.
- Với các bước bổ sung/sửa, chỉ yêu cầu LLM trả về các test MỚI hoặc ĐÃ SỬA; chương trình tự ghép
  vào file. Như vậy LLM không thể vô tình xoá test cũ hay gỡ nhãn SUSPECTED_BUG.

Các khoá của `hints`:
    language, framework, fence   tên ngôn ngữ, framework test, thẻ khối code (python / javascript / typescript)
    spec                         nơi chứa đặc tả: "docstring" (Python), "JSDoc" (JS/TS)
    import_rule, libs_rule, structure_rule, assert_rule   quy tắc 2-5 trong system prompt
    keep_marker                  câu yêu cầu giữ nhãn nghi bug khi sửa cả file
    test_id, keep_name, test_unit   cách gọi "một test" trong ngôn ngữ đó (tên hàm / tiêu đề test)
    impl_details                 ví dụ về "chi tiết cài đặt" không được kiểm tra khi giết mutant
"""


def system_prompt(hints: dict) -> str:
    return f"""Bạn là kỹ sư kiểm thử phần mềm {hints['language']} giàu kinh nghiệm, chuyên viết unit test bằng {hints['framework']}.
Quy tắc bắt buộc:
1. Viết assert theo ĐẶC TẢ trong {hints['spec']}, KHÔNG suy ra kết quả mong đợi từ cách code cài đặt.
   Nếu code có vẻ làm khác {hints['spec']}, vẫn viết assert theo {hints['spec']}.
2. {hints['import_rule']}
3. {hints['libs_rule']}
4. {hints['structure_rule']}
5. {hints['assert_rule']}
6. Trả lời bằng DUY NHẤT một khối ```{hints['fence']} ... ``` (trừ khi được yêu cầu thêm dòng LESSON hoặc JSON)."""


def _lessons_block(lessons: str) -> str:
    """Đoạn "bài học từ bộ nhớ" chèn vào prompt (rỗng nếu không có)."""
    if not lessons:
        return ""
    return f"\nBÀI HỌC TỪ CÁC LẦN TRƯỚC (hãy áp dụng, tránh lặp lại lỗi cũ):\n{lessons}\n"


def initial_prompt(hints: dict, module_name: str, source: str, lessons: str = "") -> str:
    """Prompt sinh bộ test ban đầu (cũng là prompt duy nhất của baseline)."""
    fence = hints["fence"]
    return f"""Tên module: `{module_name}`

Mã nguồn:
```{fence}
{source}
```
{_lessons_block(lessons)}
Hãy viết một file test {hints['framework']} đầy đủ cho module trên, gồm:
- trường hợp bình thường,
- giá trị biên (ví dụ đúng các ngưỡng được nêu trong {hints['spec']}),
- các ngoại lệ được mô tả trong {hints['spec']}.
Cố gắng phủ mọi nhánh if/else. Trả về toàn bộ file test trong một khối ```{fence}```."""


def fix_collection_prompt(hints: dict, module_name: str, source: str, test_code: str, error_output: str,
                          lessons: str = "") -> str:
    """File test không chạy được (lỗi cú pháp, import, thu thập test) -> sửa cả file."""
    fence = hints["fence"]
    return f"""Tên module: `{module_name}`

Mã nguồn module:
```{fence}
{source}
```

File test hiện tại KHÔNG CHẠY ĐƯỢC:
```{fence}
{test_code}
```

Lỗi khi chạy {hints['framework']}:
```
{error_output}
```
{_lessons_block(lessons)}
Hãy sửa lỗi và trả về TOÀN BỘ file test đã sửa trong một khối ```{fence}```.
Giữ nguyên các test đang đúng và {hints['keep_marker']}.
Sau khối code, viết đúng một dòng bắt đầu bằng `LESSON:` tóm tắt quy tắc chung để tránh lỗi này lần sau
(một câu, không nhắc tên hàm cụ thể của module)."""


def classify_prompt(hints: dict, module_name: str, source: str, failing_code: str, failures: str) -> str:
    """Xử lý oracle problem: test fail là do test sai hay do code có bug?"""
    fence, spec = hints["fence"], hints["spec"]
    return f"""Tên module: `{module_name}`

Mã nguồn module ({spec} là ĐẶC TẢ đúng):
```{fence}
{source}
```

Các test sau đang FAIL:
```{fence}
{failing_code}
```

Thông tin lỗi:
```
{failures}
```

Với MỖI test đang fail, hãy phân loại:
- "TEST_WRONG": test viết sai (assert sai so với {spec}, gọi hàm sai cách, giả định không có trong {spec}...).
- "SUSPECTED_BUG": test ĐÚNG theo {spec} nhưng code chạy khác {spec} -> nghi code có bug.
Chỉ chọn SUSPECTED_BUG khi {spec} nói RÕ RÀNG hành vi mong đợi và code vi phạm điều đó.

Chỉ trả về JSON đúng định dạng sau, không giải thích thêm:
{{"verdicts": [{{"test": "<{hints['test_id']}>", "verdict": "TEST_WRONG hoặc SUSPECTED_BUG", "reason": "<lý do ngắn>"}}]}}"""


def fix_tests_prompt(hints: dict, module_name: str, source: str, failing_code: str, failures: str,
                     lessons: str = "") -> str:
    """Sửa các test bị phân loại TEST_WRONG. Chỉ trả về các test đã sửa."""
    fence, spec = hints["fence"], hints["spec"]
    return f"""Tên module: `{module_name}`

Mã nguồn module ({spec} là ĐẶC TẢ đúng):
```{fence}
{source}
```

Các test sau bị xác định là VIẾT SAI:
```{fence}
{failing_code}
```

Thông tin lỗi:
```
{failures}
```
{_lessons_block(lessons)}
Hãy sửa các test này cho đúng theo {spec}. {hints['keep_name']}.
Chỉ trả về các {hints['test_unit']} đã sửa (kèm các import cần thiết) trong một khối ```{fence}```.
Sau khối code, viết đúng một dòng bắt đầu bằng `LESSON:` tóm tắt quy tắc chung để tránh lỗi này lần sau."""


def coverage_prompt(hints: dict, module_name: str, numbered_source: str, test_code: str, line_cov: float,
                    branch_cov: float, missing_desc: str) -> str:
    """Coverage chưa đạt ngưỡng -> đưa dòng/nhánh chưa phủ cho LLM để viết thêm test."""
    fence, spec = hints["fence"], hints["spec"]
    return f"""Tên module: `{module_name}`

Mã nguồn module (có số dòng):
```
{numbered_source}
```

Bộ test hiện tại:
```{fence}
{test_code}
```

Bộ test hiện tại đạt line coverage {line_cov:.1f}% và branch coverage {branch_cov:.1f}%.
Các dòng / nhánh CHƯA được test chạy tới:
{missing_desc}

Hãy viết THÊM các test MỚI để chạy tới các dòng/nhánh trên. Assert theo {spec}.
Nếu theo {spec} một dòng lẽ ra phải chạy được mà code lại không cho chạy tới, đó có thể là dấu hiệu bug:
hãy vẫn viết test theo {spec} cho tình huống đó.
Không lặp lại test đã có, đặt tên test mới khác tên cũ.
Chỉ trả về các {hints['test_unit']} MỚI (kèm import cần thiết) trong một khối ```{fence}```."""


def mutation_prompt(hints: dict, module_name: str, numbered_source: str, test_code: str, mutants_desc: str) -> str:
    """Mutant còn sống -> yêu cầu test mới "giết" được mutant."""
    fence, spec = hints["fence"], hints["spec"]
    return f"""Tên module: `{module_name}`

Mã nguồn module GỐC (có số dòng):
```
{numbered_source}
```

Bộ test hiện tại:
```{fence}
{test_code}
```

Mutation testing: chương trình đã sửa nhẹ code gốc (tạo "mutant"). Các mutant sau vẫn SỐNG,
nghĩa là bộ test hiện tại KHÔNG phát hiện được thay đổi:
{mutants_desc}

Hãy viết THÊM các test MỚI để phân biệt code gốc với từng mutant: test phải đúng theo {spec}
(pass với code đúng đặc tả) nhưng FAIL khi chạy với mutant. Thường cần kiểm tra đúng giá trị biên
hoặc kiểm tra chính xác giá trị trả về.
Chỉ kiểm tra hành vi ĐƯỢC MÔ TẢ trong {spec}. KHÔNG kiểm tra chi tiết cài đặt mà {spec} không quy định
({hints['impl_details']}).
Nếu một mutant chỉ phân biệt được bằng chi tiết cài đặt như vậy, coi nó là mutant tương đương và bỏ qua.
Không lặp lại test đã có, đặt tên test mới khác tên cũ.
Chỉ trả về các {hints['test_unit']} MỚI (kèm import cần thiết) trong một khối ```{fence}```."""
