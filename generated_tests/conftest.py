"""Cho phép chạy trực tiếp các test do LLM sinh ra từ thư mục gốc dự án, ví dụ:

    pytest generated_tests/baseline/test_calculator.py

Test sinh ra dùng `import calculator`, nên cần thêm thư mục targets/python/ vào sys.path.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "targets" / "python"))
