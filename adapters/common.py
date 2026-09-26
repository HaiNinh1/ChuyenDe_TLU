"""Tiện ích dùng chung cho mọi adapter: chạy tiến trình con có timeout, cắt bớt chuỗi dài."""
import os
import signal
import subprocess

SUSPECTED_TAG = "SUSPECTED_BUG"   # nhãn đánh dấu test nghi phát hiện bug (mọi ngôn ngữ dùng chung)
IS_WINDOWS = os.name == "nt"


def _kill_tree(proc: subprocess.Popen):
    """Dừng tiến trình VÀ mọi tiến trình con của nó (vd. Stryker sinh nhiều tiến trình node).

    Chỉ kill() tiến trình trực tiếp là chưa đủ: tiến trình cháu vẫn giữ ống dẫn (pipe) nên chương trình chính
    phải chờ tới khi chúng tự thoát — có thể là mãi mãi nếu mutant gây vòng lặp vô hạn.
    """
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=30)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    proc.kill()


def run_subprocess(cmd, cwd, timeout, extra_env=None):
    """Chạy lệnh với timeout. Trả về CompletedProcess, hoặc None nếu quá thời gian.

    extra_env: biến môi trường thêm cho tiến trình con (mỗi adapter tự quyết, ví dụ PYTHONPATH cho Python).
    Không tìm thấy chương trình (vd. máy chưa cài Node.js) -> CompletedProcess mã 127 kèm thông báo, không ném lỗi.
    """
    env = dict(os.environ)
    env.update(extra_env or {})
    group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WINDOWS else {"start_new_session": True}
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace", **group)
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", f"Không chạy được {cmd[0]}: {exc}")
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        return None
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def tail(text: str, max_chars: int) -> str:
    """Giữ phần CUỐI của chuỗi dài (thông tin lỗi quan trọng thường nằm ở cuối)."""
    return text if len(text) <= max_chars else "...\n" + text[-max_chars:]
