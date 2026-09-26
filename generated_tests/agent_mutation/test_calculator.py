import pytest
import calculator


def test_add():
    # Trường hợp bình thường
    assert calculator.add(2, 3) == 5
    assert calculator.add(-1, 1) == 0
    assert calculator.add(0, 0) == 0
    assert calculator.add(2.5, 3.5) == 6.0
    # Trường hợp biên: số lớn
    assert calculator.add(10**6, -10**6) == 0


def test_divide():
    # Trường hợp bình thường
    assert calculator.divide(10, 2) == 5
    assert calculator.divide(5, 2) == 2.5
    assert calculator.divide(-6, 3) == -2.0
    assert calculator.divide(0, 5) == 0
    # Trường hợp biên: chia cho 1
    assert calculator.divide(7, 1) == 7
    # Ngoại lệ: chia cho 0
    with pytest.raises(ZeroDivisionError) as excinfo:
        calculator.divide(5, 0)
    assert str(excinfo.value) == "Không thể chia cho 0"


def test_average():
    # Danh sách rỗng
    assert calculator.average([]) == 0
    # Một phần tử
    assert calculator.average([42]) == 42.0
    # Trường hợp bình thường
    assert calculator.average([1, 2, 3]) == 2.0
    assert calculator.average([10, 20, 30, 40]) == 25.0
    # Số thực
    assert calculator.average([1.5, 2.5, 3.0]) == pytest.approx(2.333333333333333)
    # Trường hợp biên: danh sách lớn
    big_list = [1] * 1000
    assert calculator.average(big_list) == 1.0
    # Danh sách với số âm
    assert calculator.average([-5, 0, 5]) == 0.0


def test_clamp():
    # Trường hợp bình thường: giá trị trong khoảng
    assert calculator.clamp(5, 0, 10) == 5
    assert calculator.clamp(0, 0, 10) == 0
    assert calculator.clamp(10, 0, 10) == 10
    # Giá trị dưới low
    assert calculator.clamp(-3, 0, 10) == 0
    # Giá trị trên high
    assert calculator.clamp(15, 0, 10) == 10
    # Trường hợp biên: low == high
    assert calculator.clamp(7, 5, 5) == 5
    assert calculator.clamp(5, 5, 5) == 5
    assert calculator.clamp(3, 5, 5) == 5
    assert calculator.clamp(9, 5, 5) == 5
    # Số thực
    assert calculator.clamp(2.5, 2.0, 3.0) == 2.5
    assert calculator.clamp(1.0, 2.0, 3.0) == 2.0
    assert calculator.clamp(4.0, 2.0, 3.0) == 3.0
    # Ngoại lệ: low > high
    with pytest.raises(ValueError) as excinfo:
        calculator.clamp(5, 10, 0)
    assert str(excinfo.value) == "low phải nhỏ hơn hoặc bằng high"


def test_factorial():
    # Trường hợp bình thường
    assert calculator.factorial(0) == 1
    assert calculator.factorial(1) == 1
    assert calculator.factorial(5) == 120
    assert calculator.factorial(7) == 5040
    # Trường hợp biên: n lớn (nhưng vẫn hợp lý cho test)
    assert calculator.factorial(10) == 3628800
    # Ngoại lệ: n < 0
    with pytest.raises(ValueError) as excinfo:
        calculator.factorial(-1)
    assert str(excinfo.value) == "n phải >= 0"


class _Wrap:
    """Simple wrapper for testing identity in clamp."""
    def __init__(self, val):
        self.val = val
    def __lt__(self, other):
        return self.val < other.val
    def __le__(self, other):
        return self.val <= other.val
    def __gt__(self, other):
        return self.val > other.val
    def __ge__(self, other):
        return self.val >= other.val
    def __eq__(self, other):
        return isinstance(other, _Wrap) and self.val == other.val


def test_clamp_returns_same_object_when_value_equals_low():
    """When value equals low (and low < high) clamp should return the value object itself."""
    low = _Wrap(5)
    high = _Wrap(10)
    value = _Wrap(5)  # equal to low
    result = calculator.clamp(value, low, high)
    # Original implementation returns `value`; mutant #11 would return `low`.
    assert result is value


def test_clamp_returns_same_object_when_value_equals_high():
    """When value equals high (and low < high) clamp should return the value object itself."""
    low = _Wrap(5)
    high = _Wrap(10)
    value = _Wrap(10)  # equal to high
    result = calculator.clamp(value, low, high)
    # Original implementation returns `value`; mutant #12 would return `high`.
    assert result is value
