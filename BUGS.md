# BUGS.md — Danh sách bug CỐ TÌNH cài vào `targets/` (Python và JavaScript/TypeScript)

> Không có comment nào trong code nhắc tới các bug này (để LLM không "nhìn thấy đáp án").
> LLM chỉ có thể phát hiện bug bằng cách so **đặc tả trong docstring (Python) / JSDoc (JS/TS)** với **hành vi thực tế**
> của code. Bản đã sửa: `evaluation/fixed_targets/python/` và `evaluation/fixed_targets/javascript/`.

| # | Module | Hàm | Mô tả bug | Đặc tả (docstring) nói | Code thực tế làm | Input phát hiện |
|---|--------|-----|-----------|------------------------|------------------|-----------------|
| 1 | `targets/python/grading.py` | `letter_grade` | Lỗi biên (boundary / off-by-one) | `80 <= score < 90 -> "B"` | dùng `score > 80` nên 80 rơi xuống nhánh `"C"` | `letter_grade(80)` trả về `"C"` thay vì `"B"` |
| 2 | `targets/python/shopping_cart.py` | `ShoppingCart.remove_item` | Sai điều kiện xoá sản phẩm | "Nếu số lượng còn lại bằng 0 thì sản phẩm bị XOÁ khỏi giỏ" | dùng `quantity < 0` (không bao giờ đúng) nên sản phẩm với số lượng 0 vẫn nằm trong giỏ | thêm 2 cái rồi bớt 2 cái → `unique_items()` trả về `1` thay vì `0`, `"tao" in cart.items` vẫn True |
| 3 | `targets/javascript/shipping.ts` (TypeScript) | `shippingFee` | Lỗi biên (boundary / off-by-one) | `total >= 500 -> miễn phí (0)` | dùng `total > 500` nên đơn đúng 500 vẫn bị tính phí 15 | `shippingFee(500)` trả về `15` thay vì `0` (kéo theo `totalToPay(500)` = 515) |
| 4 | `targets/javascript/bank_account.js` | `BankAccount.withdraw` / `transfer` | Quên cập nhật trạng thái (thiếu một câu lệnh) | "TỔNG tiền đã rút trong ngày (cộng dồn mọi lần rút) vượt dailyLimit -> ném Error" | kiểm tra hạn mức nhưng **không cộng dồn** `withdrawnToday` sau mỗi lần rút, nên hạn mức ngày không bao giờ bị chạm tới qua nhiều lần rút | `new BankAccount("An", 10000)`, `withdraw(3000)` rồi `withdraw(3000)` → lần 2 lẽ ra ném lỗi (6000 > 5000) nhưng vẫn rút được |

## Tại sao chọn các bug này?
Hai bug JavaScript được chọn **cùng loại** với hai bug Python (1 lỗi biên + 1 lỗi trạng thái cần chuỗi thao tác) để so
sánh giữa hai ngôn ngữ công bằng hơn.

- **Bug 1 (biên):** loại bug kinh điển mà kỹ thuật *kiểm thử giá trị biên* (boundary value analysis) nhắm tới.
  Coverage **không** giúp tìm bug này: test `letter_grade(85)` đã phủ nhánh `"B"` nhưng không lộ bug.
  Mutation testing có thể gián tiếp giúp: mutant đổi `> 80` thành `>= 80` chỉ bị "giết" nếu có test ở đúng biên 80.
- **Bug 2 (trạng thái):** bug nằm trong class có trạng thái, cần *chuỗi thao tác* (thêm rồi bớt hết) mới lộ.
  Dòng `del self.items[name]` trở thành **code chết** (không bao giờ chạy tới) → coverage không thể đạt 100%.
  Đây là tín hiệu thú vị: nếu agent cố phủ dòng này mà không được, nó có thể nghi ngờ có bug.
- **Bug 3 (biên, TypeScript):** cùng loại bug 1, nằm trong file `.ts` để kiểm tra adapter chạy được TypeScript.
- **Bug 4 (trạng thái, JavaScript):** khác bug 2 ở chỗ **không có code chết**: mọi dòng vẫn chạy được, coverage có thể
  đạt 100% mà bug vẫn còn (câu lệnh cần có thì bị THIẾU). Chỉ lộ ra khi test gọi `withdraw` nhiều lần liên tiếp và
  kiểm tra đúng quy tắc cộng dồn trong JSDoc → đo được khả năng "đọc đặc tả" của LLM chứ không nhờ coverage.

## Cách chấm "phát hiện bug" (dùng trong evaluate.py)
Bug được coi là phát hiện nếu tồn tại ít nhất một test:
- FAIL hoặc được đánh dấu `SUSPECTED_BUG` (xfail) khi chạy với code có bug, **và**
- PASS khi chạy với bản đã sửa trong `evaluation/fixed_targets/<ngôn ngữ>/` (JS: nhãn `test.failing` được bỏ trước khi chạy bản đã sửa).
