# BUGS.md — Danh sách bug CỐ TÌNH cài vào `targets/`

> Không có comment nào trong code nhắc tới các bug này (để LLM không "nhìn thấy đáp án").
> LLM chỉ có thể phát hiện bug bằng cách so **đặc tả trong docstring** với **hành vi thực tế** của code.
> Bản đã sửa: `evaluation/fixed_targets/`.

| # | Module | Hàm | Mô tả bug | Đặc tả (docstring) nói | Code thực tế làm | Input phát hiện |
|---|--------|-----|-----------|------------------------|------------------|-----------------|
| 1 | `targets/grading.py` | `letter_grade` | Lỗi biên (boundary / off-by-one) | `80 <= score < 90 -> "B"` | dùng `score > 80` nên 80 rơi xuống nhánh `"C"` | `letter_grade(80)` trả về `"C"` thay vì `"B"` |
| 2 | `targets/shopping_cart.py` | `ShoppingCart.remove_item` | Sai điều kiện xoá sản phẩm | "Nếu số lượng còn lại bằng 0 thì sản phẩm bị XOÁ khỏi giỏ" | dùng `quantity < 0` (không bao giờ đúng) nên sản phẩm với số lượng 0 vẫn nằm trong giỏ | thêm 2 cái rồi bớt 2 cái → `unique_items()` trả về `1` thay vì `0`, `"tao" in cart.items` vẫn True |

## Tại sao chọn 2 bug này?
- **Bug 1 (biên):** loại bug kinh điển mà kỹ thuật *kiểm thử giá trị biên* (boundary value analysis) nhắm tới.
  Coverage **không** giúp tìm bug này: test `letter_grade(85)` đã phủ nhánh `"B"` nhưng không lộ bug.
  Mutation testing có thể gián tiếp giúp: mutant đổi `> 80` thành `>= 80` chỉ bị "giết" nếu có test ở đúng biên 80.
- **Bug 2 (trạng thái):** bug nằm trong class có trạng thái, cần *chuỗi thao tác* (thêm rồi bớt hết) mới lộ.
  Dòng `del self.items[name]` trở thành **code chết** (không bao giờ chạy tới) → coverage không thể đạt 100%.
  Đây là tín hiệu thú vị: nếu agent cố phủ dòng này mà không được, nó có thể nghi ngờ có bug.

## Cách chấm "phát hiện bug" (dùng trong evaluate.py)
Bug được coi là phát hiện nếu tồn tại ít nhất một test:
- FAIL hoặc được đánh dấu `SUSPECTED_BUG` (xfail) khi chạy với code có bug, **và**
- PASS khi chạy với bản đã sửa trong `evaluation/fixed_targets/`.
