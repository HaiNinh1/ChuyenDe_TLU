import calculator
import pytest


def test_add_positive_integers():
    assert calculator.add(2, 3) == 5


def test_add_negative_and_positive():
    assert calculator.add(-5, 10) == 5


def test_add_zero():
    assert calculator.add(0, 0) == 0
    assert calculator.add(7, 0) == 7
    assert calculator.add(0, -3) == -3


def test_add_floats():
    assert calculator.add(1.5, 2.5) == 4.0
    assert calculator.add(-1.2, 3.4) == pytest.approx(2.2)


def test_divide_normal():
    assert calculator.divide(10, 2) == 5
    assert calculator.divide(5, 2) == 2.5
    assert calculator.divide(-9, 3) == -3


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError, match="Không thể chia cho 0"):
        calculator.divide(5, 0)


def test_divide_floats():
    assert calculator.divide(1.0, 4.0) == pytest.approx(0.25)
    assert calculator.divide(-2.5, 0.5) == pytest.approx(-5.0)


def test_average_normal():
    assert calculator.average([1, 2, 3]) == 2.0
    assert calculator.average([10, 20, 30, 40]) == 25.0


def test_average_empty_list():
    assert calculator.average([]) == 0


def test_average_single_element():
    assert calculator.average([42]) == 42.0
    assert calculator.average([-7]) == -7.0


def test_average_floats():
    assert calculator.average([1.5, 2.5, 3.0]) == pytest.approx(2.333333333333333)


def test_clamp_below_low():
    assert calculator.clamp(value=5, low=10, high=20) == 10


def test_clamp_above_high():
    assert calculator.clamp(value=25, low=10, high=20) == 20


def test_clamp_within_range():
    assert calculator.clamp(value=15, low=10, high=20) == 15
    assert calculator.clamp(value=10.5, low=10, high=20) == 10.5
    assert calculator.clamp(value=19.9, low=10, high=20) == 19.9


def test_clamp_edge_equal_low():
    assert calculator.clamp(value=10, low=10, high=20) == 10


def test_clamp_edge_equal_high():
    assert calculator.clamp(value=20, low=10, high=20) == 20


def test_clamp_low_gt_high_raises():
    with pytest.raises(ValueError, match="low phải nhỏ hơn hoặc bằng high"):
        calculator.clamp(value=0, low=5, high=3)


def test_factorial_zero():
    assert calculator.factorial(0) == 1


def test_factorial_one():
    assert calculator.factorial(1) == 1


def test_factorial_positive():
    assert calculator.factorial(5) == 120
    assert calculator.factorial(3) == 6
    assert calculator.factorial(7) == 5040


def test_factorial_negative_raises():
    with pytest.raises(ValueError, match="n phải >= 0"):
        calculator.factorial(-1)

    with pytest.raises(ValueError, match="n phải >= 0"):
        calculator.factorial(-10)


def test_divide_by_zero_exact_message():
    """Kiểm tra thông báo lỗi ZeroDivisionError chính xác."""
    with pytest.raises(ZeroDivisionError) as excinfo:
        calculator.divide(5, 0)
    assert str(excinfo.value) == "Không thể chia cho 0"


def test_clamp_low_eq_high_no_error():
    """Khi low == high, hàm clamp không ném lỗi và trả về giá trị đó (hoặc low)."""
    assert calculator.clamp(value=0, low=5, high=5) == 5
    assert calculator.clamp(value=5, low=5, high=5) == 5
    assert calculator.clamp(value=10, low=5, high=5) == 5


def test_clamp_low_gt_high_exact_message():
    """Kiểm tra thông báo lỗi ValueError khi low > high chính xác."""
    with pytest.raises(ValueError) as excinfo:
        calculator.clamp(value=0, low=5, high=3)
    assert str(excinfo.value) == "low phải nhỏ hơn hoặc bằng high"


def test_factorial_negative_exact_message():
    """Kiểm tra thông báo lỗi ValueError cho factorial với n < 0 chính xác."""
    with pytest.raises(ValueError) as excinfo:
        calculator.factorial(-1)
    assert str(excinfo.value) == "n phải >= 0"
