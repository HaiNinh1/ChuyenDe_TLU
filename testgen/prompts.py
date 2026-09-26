"""Toàn bộ prompt gửi cho LLM nằm ở đây để dễ đọc, dễ chỉnh.

Nguyên tắc chung của các prompt:
- Luôn đưa ĐẶC TẢ (docstring) và yêu cầu LLM viết assert theo đặc tả, không theo cài đặt
  -> giảm "oracle problem" (test hợp thức hoá bug).
- Yêu cầu trả về đúng MỘT khối ```python``` để code dễ tách ra.
- Với các bước bổ sung/sửa, chỉ yêu cầu LLM trả về các hàm test MỚI hoặc ĐÃ SỬA; chương trình tự ghép
  vào file. Như vậy LLM không thể vô tình xoá test cũ hay gỡ nhãn SUSPECTED_BUG.
"""

SYSTEM_PROMPT = """Bạn là kỹ sư kiểm thử phần mềm Python giàu kinh nghiệm, chuyên viết unit test bằng pytest.
Quy tắc bắt buộc:
1. Viết assert theo ĐẶC TẢ trong docstring, KHÔNG suy ra kết quả mong đợi từ cách code cài đặt.
   Nếu code có vẻ làm khác docstring, vẫn viết assert theo docstring.
2. Module cần test nằm cùng thư mục với file test: dùng `import <module>` hoặc `from <module> import ...`.
3. Chỉ dùng pytest và thư viện chuẩn. Không đọc/ghi file, không gọi mạng, không sleep.
4. Viết các hàm test cấp module (không dùng class), mỗi test kiểm tra một ý, tên hàm mô tả rõ, bắt đầu bằng `test_`.
5. Dùng `pytest.raises` cho ngoại lệ và `pytest.approx` khi so sánh số thực.
6. Trả lời bằng DUY NHẤT một khối ```python ... ``` (trừ khi được yêu cầu thêm dòng LESSON hoặc JSON)."""


def _lessons_block(lessons: str) -> str:
    """Đoạn "bài học từ bộ nhớ" chèn vào prompt (rỗng nếu không có)."""
    if not lessons:
        return ""
    return f"\nBÀI HỌC TỪ CÁC LẦN TRƯỚC (hãy áp dụng, tránh lặp lại lỗi cũ):\n{lessons}\n"


def initial_prompt(module_name: str, source: str, lessons: str = "") -> str:
    """Prompt sinh bộ test ban đầu (cũng là prompt duy nhất của baseline)."""
    return f"""Tên module: `{module_name}`

Mã nguồn:
```python
{source}
```
{_lessons_block(lessons)}
Hãy viết một file test pytest đầy đủ cho module trên, gồm:
- trường hợp bình thường,
- giá trị biên (ví dụ đúng các ngưỡng được nêu trong docstring),
- các ngoại lệ được mô tả trong docstring.
Cố gắng phủ mọi nhánh if/else. Trả về toàn bộ file test trong một khối ```python```."""


def fix_collection_prompt(module_name: str, source: str, test_code: str, error_output: str,
                          lessons: str = "") -> str:
    """File test không chạy được (lỗi cú pháp, import, thu thập test) -> sửa cả file."""
    return f"""Tên module: `{module_name}`

Mã nguồn module:
```python
{source}
```

File test hiện tại KHÔNG CHẠY ĐƯỢC:
```python
{test_code}
```

Lỗi khi chạy pytest:
```
{error_output}
```
{_lessons_block(lessons)}
Hãy sửa lỗi và trả về TOÀN BỘ file test đã sửa trong một khối ```python```.
Giữ nguyên các test đang đúng và giữ nguyên các decorator `@pytest.mark.xfail` nếu có.
Sau khối code, viết đúng một dòng bắt đầu bằng `LESSON:` tóm tắt quy tắc chung để tránh lỗi này lần sau
(một câu, không nhắc tên hàm cụ thể của module)."""


def classify_prompt(module_name: str, source: str, failing_code: str, failures: str) -> str:
    """Xử lý oracle problem: test fail là do test sai hay do code có bug?"""
    return f"""Tên module: `{module_name}`

Mã nguồn module (docstring là ĐẶC TẢ đúng):
```python
{source}
```

Các test sau đang FAIL:
```python
{failing_code}
```

Thông tin lỗi:
```
{failures}
```

Với MỖI test đang fail, hãy phân loại:
- "TEST_WRONG": test viết sai (assert sai so với docstring, gọi hàm sai cách, giả định không có trong docstring...).
- "SUSPECTED_BUG": test ĐÚNG theo docstring nhưng code chạy khác docstring -> nghi code có bug.
Chỉ chọn SUSPECTED_BUG khi docstring nói RÕ RÀNG hành vi mong đợi và code vi phạm điều đó.

Chỉ trả về JSON đúng định dạng sau, không giải thích thêm:
{{"verdicts": [{{"test": "<tên hàm test>", "verdict": "TEST_WRONG hoặc SUSPECTED_BUG", "reason": "<lý do ngắn>"}}]}}"""


def fix_tests_prompt(module_name: str, source: str, failing_code: str, failures: str,
                     lessons: str = "") -> str:
    """Sửa các test bị phân loại TEST_WRONG. Chỉ trả về các hàm đã sửa."""
    return f"""Tên module: `{module_name}`

Mã nguồn module (docstring là ĐẶC TẢ đúng):
```python
{source}
```

Các test sau bị xác định là VIẾT SAI:
```python
{failing_code}
```

Thông tin lỗi:
```
{failures}
```
{_lessons_block(lessons)}
Hãy sửa các test này cho đúng theo docstring. GIỮ NGUYÊN TÊN HÀM TEST.
Chỉ trả về các hàm test đã sửa (kèm các import cần thiết) trong một khối ```python```.
Sau khối code, viết đúng một dòng bắt đầu bằng `LESSON:` tóm tắt quy tắc chung để tránh lỗi này lần sau."""


def coverage_prompt(module_name: str, numbered_source: str, test_code: str, line_cov: float,
                    branch_cov: float, missing_desc: str) -> str:
    """Coverage chưa đạt ngưỡng -> đưa dòng/nhánh chưa phủ cho LLM để viết thêm test."""
    return f"""Tên module: `{module_name}`

Mã nguồn module (có số dòng):
```
{numbered_source}
```

Bộ test hiện tại:
```python
{test_code}
```

Bộ test hiện tại đạt line coverage {line_cov:.1f}% và branch coverage {branch_cov:.1f}%.
Các dòng / nhánh CHƯA được test chạy tới:
{missing_desc}

Hãy viết THÊM các test MỚI để chạy tới các dòng/nhánh trên. Assert theo docstring.
Nếu theo docstring một dòng lẽ ra phải chạy được mà code lại không cho chạy tới, đó có thể là dấu hiệu bug:
hãy vẫn viết test theo docstring cho tình huống đó.
Không lặp lại test đã có, đặt tên test mới khác tên cũ.
Chỉ trả về các hàm test MỚI (kèm import cần thiết) trong một khối ```python```."""


def mutation_prompt(module_name: str, numbered_source: str, test_code: str, mutants_desc: str) -> str:
    """Mutant còn sống -> yêu cầu test mới "giết" được mutant."""
    return f"""Tên module: `{module_name}`

Mã nguồn module GỐC (có số dòng):
```
{numbered_source}
```

Bộ test hiện tại:
```python
{test_code}
```

Mutation testing: chương trình đã sửa nhẹ code gốc (tạo "mutant"). Các mutant sau vẫn SỐNG,
nghĩa là bộ test hiện tại KHÔNG phát hiện được thay đổi:
{mutants_desc}

Hãy viết THÊM các test MỚI để phân biệt code gốc với từng mutant: test phải đúng theo docstring
(pass với code đúng đặc tả) nhưng FAIL khi chạy với mutant. Thường cần kiểm tra đúng giá trị biên
hoặc kiểm tra chính xác giá trị trả về.
Nếu một mutant không thể phân biệt được (mutant tương đương) thì bỏ qua nó.
Không lặp lại test đã có, đặt tên test mới khác tên cũ.
Chỉ trả về các hàm test MỚI (kèm import cần thiết) trong một khối ```python```."""
