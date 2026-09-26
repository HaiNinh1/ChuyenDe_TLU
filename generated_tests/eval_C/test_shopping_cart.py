import pytest
from shopping_cart import ShoppingCart


def test_add_item_valid():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 3)
    assert cart.items["apple"]["price"] == 1.0
    assert cart.items["apple"]["quantity"] == 3


def test_add_item_price_nonpositive():
    cart = ShoppingCart()
    with pytest.raises(ValueError, match="Giá phải lớn hơn 0"):
        cart.add_item("apple", 0)
    with pytest.raises(ValueError, match="Giá phải lớn hơn 0"):
        cart.add_item("apple", -5)


def test_add_item_quantity_less_than_one():
    cart = ShoppingCart()
    with pytest.raises(ValueError, match="Số lượng phải >= 1"):
        cart.add_item("apple", 1.0, 0)
    with pytest.raises(ValueError, match="Số lượng phải >= 1"):
        cart.add_item("apple", 1.0, -2)


def test_add_item_duplicate_same_price():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 2)
    cart.add_item("apple", 1.0, 3)
    assert cart.items["apple"]["quantity"] == 5


def test_add_item_duplicate_different_price():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 1)
    with pytest.raises(ValueError, match="Đơn giá không khớp với sản phẩm đã có"):
        cart.add_item("apple", 2.0, 1)


def test_remove_item_keyerror():
    cart = ShoppingCart()
    with pytest.raises(KeyError):
        cart.remove_item("nonexistent")


def test_remove_item_quantity_exceeds():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 2)
    with pytest.raises(ValueError, match="Không đủ số lượng để bớt"):
        cart.remove_item("apple", 5)


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: remove_item leaves item with quantity 0 in cart, but docstring says it should be deleted.")
def test_remove_item_to_zero_deletes():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 2)
    cart.remove_item("apple", 2)
    assert "apple" not in cart.items


def test_remove_item_partial():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 5)
    cart.remove_item("apple", 2)
    assert cart.items["apple"]["quantity"] == 3


def test_item_count():
    cart = ShoppingCart()
    assert cart.item_count() == 0
    cart.add_item("apple", 1.0, 2)
    cart.add_item("banana", 0.5, 3)
    assert cart.item_count() == 5
    cart.remove_item("apple", 1)
    assert cart.item_count() == 4


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: unique_items counts items with zero quantity due to remove_item bug, contradicting docstring.")
def test_unique_items():
    cart = ShoppingCart()
    assert cart.unique_items() == 0
    cart.add_item("apple", 1.0, 1)
    cart.add_item("banana", 0.5, 1)
    assert cart.unique_items() == 2
    cart.add_item("apple", 1.0, 2)  # same product, unique count unchanged
    assert cart.unique_items() == 2
    cart.remove_item("apple", 3)  # remove all apples
    assert cart.unique_items() == 1


def test_subtotal():
    cart = ShoppingCart()
    assert cart.subtotal() == 0
    cart.add_item("apple", 1.0, 2)
    cart.add_item("banana", 0.5, 4)
    assert cart.subtotal() == pytest.approx(1.0 * 2 + 0.5 * 4)


def test_apply_discount_invalid_code():
    cart = ShoppingCart()
    with pytest.raises(ValueError, match="Mã giảm giá không hợp lệ"):
        cart.apply_discount("INVALID")


def test_apply_discount_already_applied():
    cart = ShoppingCart()
    cart.apply_discount("SALE10")
    with pytest.raises(ValueError, match="Giỏ hàng đã áp dụng mã giảm giá"):
        cart.apply_discount("SALE20")


def test_apply_discount_valid():
    cart = ShoppingCart()
    cart.apply_discount("SALE10")
    assert cart.discount_code == "SALE10"


def test_total_empty():
    cart = ShoppingCart()
    assert cart.total() == 0


def test_total_with_discount():
    cart = ShoppingCart()
    cart.add_item("book", 10.0, 2)  # subtotal = 20
    cart.apply_discount("SALE10")   # 10% off => 18
    assert cart.total() == pytest.approx(18.0)


def test_total_rounding():
    cart = ShoppingCart()
    # price that leads to more than 2 decimal places after discount
    cart.add_item("gadget", 0.1, 3)   # subtotal = 0.3
    cart.apply_discount("SALE10")     # 0.3 * 0.9 = 0.27 -> exactly 2 dec
    assert cart.total() == pytest.approx(0.27)
    # another case needing rounding
    cart2 = ShoppingCart()
    cart2.add_item("thing", 0.15, 2)  # subtotal = 0.30
    cart2.apply_discount("SALE20")    # 0.30 * 0.8 = 0.24 -> exact
    assert cart2.total() == pytest.approx(0.24)
    # case with repeating decimal
    cart3 = ShoppingCart()
    cart3.add_item("item", 1.0, 1)    # subtotal = 1.0
    cart3.apply_discount("SALE10")    # 0.9 -> exact
    assert cart3.total() == pytest.approx(0.9)
    # force rounding: 1.005 * 1 = 1.005, 10% off => 0.9045 -> round to 0.90
    cart4 = ShoppingCart()
    cart4.add_item("precise", 1.005, 1)
    cart4.apply_discount("SALE10")
    assert cart4.total() == pytest.approx(0.90)


def test_clear():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 2)
    cart.apply_discount("SALE20")
    assert cart.items
    assert cart.discount_code is not None
    cart.clear()
    assert cart.items == {}
    assert cart.discount_code is None
    # after clear we can add items and apply discount again
    cart.add_item("pear", 2.0, 1)
    cart.apply_discount("SALE10")
    assert cart.total() == pytest.approx(2.0 * 0.9)


def test_discount_only_one():
    cart = ShoppingCart()
    cart.apply_discount("SALE10")
    # trying to apply same code again should also raise
    with pytest.raises(ValueError, match="Giỏ hàng đã áp dụng mã giảm giá"):
        cart.apply_discount("SALE10")
    # after clear, can apply again
    cart.clear()
    cart.apply_discount("SALE10")
    assert cart.discount_code == "SALE10"
