import calculator
import pytest


def test_add_basic():
    assert calculator.add(2, 3) == 5
    assert calculator.add(-1, 1) == 0
    assert calculator.add(0, 0) == 0
    assert calculator.add(2.5, 3.5) == 6.0


def test_divide_normal():
    assert calculator.divide(10, 2) == 5
    assert calculator.divide(5, 2) == 2.5
    assert calculator.divide(0, 5) == 0
    assert calculator.divide(-10, 2) == -5


def test_divide_by_zero_exception():
    with pytest.raises(ZeroDivisionError, match="Không thể chia cho 0"):
        calculator.divide(5, 0)


def test_average_normal():
    assert calculator.average([1, 2, 3]) == 2.0
    assert calculator.average([10, 20, 30, 40]) == 25.0
    assert calculator.average([-1, 0, 1]) == 0.0
    assert calculator.average([1.5, 2.5, 3.5]) == pytest.approx(2.5)


def test_average_empty():
    assert calculator.average([]) == 0


def test_clamp_within_range():
    assert calculator.clamp(5, 0, 10) == 5
    assert calculator.clamp(0, 0, 10) == 0
    assert calculator.clamp(10, 0, 10) == 10
    assert calculator.clamp(-5, -10, -1) == -5


def test_clamp_below_low():
    assert calculator.clamp(-5, 0, 10) == 0
    assert calculator.clamp(0, 5, 10) == 5


def test_clamp_above_high():
    assert calculator.clamp(15, 0, 10) == 10
    assert calculator.clamp(10, 0, 5) == 5


def test_clamp_edge_low_eq_high():
    assert calculator.clamp(7, 5, 5) == 5
    assert calculator.clamp(5, 5, 5) == 5
    assert calculator.clamp(3, 5, 5) == 5


def test_clamp_exception_low_gt_high():
    with pytest.raises(ValueError, match="low phải nhỏ hơn hoặc bằng high"):
        calculator.clamp(0, 10, 5)


def test_factorial_normal():
    assert calculator.factorial(1) == 1
    assert calculator.factorial(5) == 120
    assert calculator.factorial(3) == 6
    assert calculator.factorial(0) == 1


def test_factorial_exception_negative():
    with pytest.raises(ValueError, match="n phải >= 0"):
        calculator.factorial(-1)
    with pytest.raises(ValueError, match="n phải >= 0"):
        calculator.factorial(-10)
