# Bản ĐÃ SỬA của code mục tiêu

Thư mục này chứa bản đúng (đã sửa bug cài sẵn) của các module trong `targets/`.
Chỉ dùng trong `evaluate.py` để chấm tiêu chí "bộ test có phát hiện bug không":
một bug được coi là **phát hiện** nếu có ít nhất một test FAIL (hoặc bị đánh dấu SUSPECTED_BUG)
trên bản có bug nhưng PASS trên bản đã sửa.

LLM **không bao giờ** được xem các file này.
