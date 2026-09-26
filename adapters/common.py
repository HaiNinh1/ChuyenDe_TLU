"""Tiện ích dùng chung cho mọi adapter: chạy tiến trình con có timeout, cắt bớt chuỗi dài."""
import os
import subprocess

SUSPECTED_TAG = "SUSPECTED_BUG"   # nhãn đánh dấu test nghi phát hiện bug (mọi ngôn ngữ dùng chung)


def run_subprocess(cmd, cwd, timeout, extra_env=None):
    """Chạy lệnh với timeout. Trả về CompletedProcess, hoặc None nếu quá thời gian.

    extra_env: biến môi trường thêm cho tiến trình con (mỗi adapter tự quyết, ví dụ PYTHONPATH cho Python).
    """
    env = dict(os.environ)
    env.update(extra_env or {})
    try:
        return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def tail(text: str, max_chars: int) -> str:
    """Giữ phần CUỐI của chuỗi dài (thông tin lỗi quan trọng thường nằm ở cuối)."""
    return text if len(text) <= max_chars else "...\n" + text[-max_chars:]
