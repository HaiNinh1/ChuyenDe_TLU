import pytest
from shopping_cart import ShoppingCart

def test_add_item_new():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 2)
    assert cart.items["apple"]["price"] == 1.0
    assert cart.items["apple"]["quantity"] == 2

def test_add_item_existing_same_price():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0)
    cart.add_item("apple", 1.0, 3)
    assert cart.items["apple"]["quantity"] == 4

def test_add_item_existing_diff_price_raises():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0)
    with pytest.raises(ValueError):
        cart.add_item("apple", 2.0)

def test_add_item_price_nonpositive_raises():
    cart = ShoppingCart()
    with pytest.raises(ValueError):
        cart.add_item("apple", 0)
    with pytest.raises(ValueError):
        cart.add_item("apple", -5)

def test_add_item_quantity_less_than_one_raises():
    cart = ShoppingCart()
    with pytest.raises(ValueError):
        cart.add_item("apple", 1.0, 0)
    with pytest.raises(ValueError):
        cart.add_item("apple", 1.0, -3)

def test_remove_item_existing():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 5)
    cart.remove_item("apple", 2)
    assert cart.items["apple"]["quantity"] == 3

@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: Docstring states that when quantity reaches 0 the item should be removed, but the code only deletes when quantity < 0, leaving zero‑quantity items in ")
def test_remove_item_to_zero_removes():
    # According to docstring: quantity remaining 0 => item removed
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 3)
    cart.remove_item("apple", 3)
    assert "apple" not in cart.items

def test_remove_item_partial_remains():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 5)
    cart.remove_item("apple", 2)
    assert cart.items["apple"]["quantity"] == 3

def test_remove_item_nonexistent_raises():
    cart = ShoppingCart()
    with pytest.raises(KeyError):
        cart.remove_item("orange")

def test_remove_item_quantity_exceeds_raises():
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 2)
    with pytest.raises(ValueError):
        cart.remove_item("apple", 5)

def test_item_count():
    cart = ShoppingCart()
    assert cart.item_count() == 0
    cart.add_item("a", 1.0, 2)
    cart.add_item("b", 2.0, 3)
    assert cart.item_count() == 5

def test_unique_items():
    cart = ShoppingCart()
    assert cart.unique_items() == 0
    cart.add_item("a", 1.0)
    cart.add_item("b", 2.0)
    assert cart.unique_items() == 2
    cart.add_item("a", 1.0, 5)  # same product again
    assert cart.unique_items() == 2

def test_subtotal():
    cart = ShoppingCart()
    assert cart.subtotal() == 0
    cart.add_item("a", 10.0, 2)
    cart.add_item("b", 5.0, 3)
    assert cart.subtotal() == 10 * 2 + 5 * 3  # 35

def test_apply_discount_valid():
    cart = ShoppingCart()
    cart.add_item("a", 10.0)
    cart.apply_discount("SALE10")
    assert cart.discount_code == "SALE10"
    # applying another discount should raise
    with pytest.raises(ValueError):
        cart.apply_discount("SALE20")

def test_apply_discount_invalid_code():
    cart = ShoppingCart()
    with pytest.raises(ValueError):
        cart.apply_discount("INVALID")

def test_apply_discount_after_clear():
    cart = ShoppingCart()
    cart.add_item("a", 10.0)
    cart.apply_discount("SALE10")
    cart.clear()
    # after clear, can apply a new discount
    cart.apply_discount("SALE20")
    assert cart.discount_code == "SALE20"

def test_total_no_discount():
    cart = ShoppingCart()
    cart.add_item("a", 1.0, 3)
    cart.add_item("b", 2.0, 4)
    assert cart.total() == pytest.approx(1 * 3 + 2 * 4)  # 11

def test_total_with_discount():
    cart = ShoppingCart()
    cart.add_item("a", 10.0, 2)  # subtotal 20
    cart.apply_discount("SALE10")  # 10% off => 18
    assert cart.total() == pytest.approx(18.0)

    # test rounding
    cart2 = ShoppingCart()
    cart2.add_item("a", 1.005, 1)  # subtotal 1.005
    cart2.apply_discount("SALE10")  # => 0.9045 -> round to 0.90
    assert cart2.total() == 0.90

    cart3 = ShoppingCart()
    cart3.add_item("a", 1.0, 1)
    cart3.apply_discount("SALE20")  # => 0.8
    assert cart3.total() == 0.8

def test_total_empty_cart():
    cart = ShoppingCart()
    assert cart.total() == 0
    # applying discount to empty cart is allowed
    cart.apply_discount("SALE10")
    assert cart.total() == 0

def test_clear():
    cart = ShoppingCart()
    cart.add_item("a", 1.0, 2)
    cart.apply_discount("SALE10")
    cart.clear()
    assert cart.items == {}
    assert cart.discount_code is None
