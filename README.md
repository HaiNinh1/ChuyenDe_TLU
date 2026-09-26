# LLM Agent tự sinh unit test cho Python

Agent dùng LLM để sinh unit test (pytest) cho code Python, sau đó **tự cải tiến** bộ test qua nhiều vòng
dựa trên phản hồi từ **coverage** (dòng/nhánh chưa được chạy) và **mutation testing** (mutant còn sống).

> README đầy đủ sẽ được hoàn thiện ở GĐ10. Xem tiến độ và giải thích trong `HOC_TAP.md`.

## Cài đặt nhanh

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
copy .env.example .env          # rồi điền API key
```
