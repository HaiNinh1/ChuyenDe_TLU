from user_module import ticket_price
import pytest


def test_ticket_price_negative_age_raises_value_error():
    with pytest.raises(ValueError):
        ticket_price(-1)


def test_ticket_price_age_zero_is_free():
    assert ticket_price(0) == 0


def test_ticket_price_age_five_is_free():
    assert ticket_price(5) == 0


def test_ticket_price_age_six_is_child_price():
    assert ticket_price(6) == 50000


def test_ticket_price_age_seventeen_is_child_price():
    assert ticket_price(17) == 50000


def test_ticket_price_age_eighteen_is_adult_price():
    assert ticket_price(18) == 100000


def test_ticket_price_age_fifty_nine_is_adult_price():
    assert ticket_price(59) == 100000


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: Docstring quy định age >= 60 trả về 70000, nhưng code dùng `age <= 60` trả về 100000, vi phạm rõ ràng đặc tả.")
def test_ticket_price_age_sixty_is_senior_price():
    assert ticket_price(60) == 70000


def test_ticket_price_age_sixty_one_is_senior_price():
    assert ticket_price(61) == 70000


def test_ticket_price_age_one_hundred_is_senior_price():
    assert ticket_price(100) == 70000
