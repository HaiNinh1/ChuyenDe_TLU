"""Module 1 (dễ): các hàm tính toán đơn giản."""


def add(a, b):
    """Trả về tổng a + b."""
    return a + b


def divide(a, b):
    """Trả về a / b.

    Ném ZeroDivisionError với thông báo "Không thể chia cho 0" nếu b == 0.
    """
    if b == 0:
        raise ZeroDivisionError("Không thể chia cho 0")
    return a / b


def average(numbers):
    """Trả về trung bình cộng của danh sách số.

    Danh sách rỗng thì trả về 0.
    Ví dụ: average([1, 2, 3]) == 2.0
    """
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)


def clamp(value, low, high):
    """Giới hạn value trong đoạn [low, high].

    - value < low  -> trả về low
    - value > high -> trả về high
    - còn lại      -> trả về value
    Ném ValueError nếu low > high.
    """
    if low > high:
        raise ValueError("low phải nhỏ hơn hoặc bằng high")
    if value < low:
        return low
    if value > high:
        return high
    return value


def factorial(n):
    """Trả về n! (n giai thừa) với n là số nguyên không âm.

    factorial(0) == 1, factorial(5) == 120.
    Ném ValueError nếu n < 0.
    """
    if n < 0:
        raise ValueError("n phải >= 0")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
