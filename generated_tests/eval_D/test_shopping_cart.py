import pytest
from shopping_cart import ShoppingCart

# Helper constants from the module's spec
VALID_DISCOUNTS = {"SALE10": 0.10, "SALE20": 0.20}


def test_add_item_valid_price_and_quantity():
    """price > 0 và quantity >= 1 được chấp nhận."""
    cart = ShoppingCart()
    cart.add_item("apple", 1.0, 1)
    assert cart.item_count() == 1
    assert cart.unique_items() == 1
    assert cart.subtotal() == 1.0


def test_add_item_price_must_be_positive():
    """price <= 0 -> ValueError."""
    cart = ShoppingCart()
    with pytest.raises(ValueError) as exc:
        cart.add_item("apple", 0, 1)
    assert "Giá phải lớn hơn 0" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        cart.add_item("apple", -5, 1)
    assert "Giá phải lớn hơn 0" in str(exc.value)


def test_add_item_quantity_must_be_at_least_one():
    """quantity < 1 -> ValueError."""
    cart = ShoppingCart()
    with pytest.raises(ValueError) as exc:
        cart.add_item("apple", 1.0, 0)
    assert "Số lượng phải >= 1" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        cart.add_item("apple", 1.0, -3)
    assert "Số lượng phải >= 1" in str(exc.value)


def test_add_item_existing_same_price_increases_quantity():
    """Sản phẩm đã có: cộng dồn số lượng nếu đơn giá khớp."""
    cart = ShoppingCart()
    cart.add_item("banana", 2.0, 2)
    cart.add_item("banana", 2.0, 3)
    assert cart.item_count() == 5
    assert cart.unique_items() == 1
    assert cart.subtotal() == 2.0 * 5


def test_add_item_existing_different_price_raises():
    """Sản phẩm đã có nhưng đơn giá khác -> ValueError."""
    cart = ShoppingCart()
    cart.add_item("banana", 2.0, 1)
    with pytest.raises(ValueError) as exc:
        cart.add_item("banana", 3.0, 1)
    assert "Đơn giá không khớp với sản phẩm đã có" in str(exc.value)
    # Ensure original item unchanged
    assert cart.item_count() == 1
    assert cart.subtotal() == 2.0


def test_remove_item_unknown_product_raises_keyerror():
    """Sản phẩm không có -> KeyError."""
    cart = ShoppingCart()
    with pytest.raises(KeyError) as exc:
        cart.remove_item("pear")
    assert exc.value.args[0] == "pear"


def test_remove_item_excess_quantity_raises_valueerror():
    """quantity > số lượng hiện có -> ValueError."""
    cart = ShoppingCart()
    cart.add_item("pear", 1.5, 2)
    with pytest.raises(ValueError) as exc:
        cart.remove_item("pear", 3)
    assert "Không đủ số lượng để bớt" in str(exc.value)
    # State unchanged
    assert cart.item_count() == 2


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: remove_item should delete product when quantity reaches 0 per docstring; bug leaves zero‑quantity item, causing unique_items to be 1 instead of 0.")
def test_remove_item_exact_quantity_removes_product():
    """Số lượng còn lại bằng 0 -> sản phẩm bị xoá."""
    cart = ShoppingCart()
    cart.add_item("pear", 1.5, 2)
    cart.remove_item("pear", 2)
    assert cart.item_count() == 0
    assert cart.unique_items() == 0
    assert cart.subtotal() == 0.0


def test_remove_item_partial_quantity():
    """Bớt phần số lượng, sản phẩm vẫn còn."""
    cart = ShoppingCart()
    cart.add_item("pear", 1.5, 5)
    cart.remove_item("pear", 2)
    assert cart.item_count() == 3
    assert cart.unique_items() == 1
    assert cart.subtotal() == pytest.approx(1.5 * 3)


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: remove_item should delete product when quantity reaches 0 per docstring; bug leaves zero‑quantity item, making unique_items too high.")
def test_item_count_and_unique_items():
    """item_count trả về tổng số lượng; unique_items trả về số loại."""
    cart = ShoppingCart()
    cart.add_item("a", 10, 2)
    cart.add_item("b", 5, 3)
    assert cart.item_count() == 5
    assert cart.unique_items() == 2
    cart.remove_item("a", 1)
    assert cart.item_count() == 4
    assert cart.unique_items() == 2
    cart.remove_item("a", 1)
    assert cart.item_count() == 3
    assert cart.unique_items() == 1  # only 'b' remains


def test_subtotal_calculation():
    """subtotal = Σ price * quantity."""
    cart = ShoppingCart()
    cart.add_item("x", 2.5, 4)
    cart.add_item("y", 3.0, 1)
    assert cart.subtotal() == pytest.approx(2.5 * 4 + 3.0 * 1)


def test_apply_discount_valid_code():
    """Mã hợp lệ được áp dụng nếu chưa có mã."""
    cart = ShoppingCart()
    cart.add_item("item", 10.0, 1)
    cart.apply_discount("SALE10")
    assert cart.discount_code == "SALE10"


def test_apply_discount_invalid_code_raises():
    """Mã không hợp lệ -> ValueError."""
    cart = ShoppingCart()
    with pytest.raises(ValueError) as exc:
        cart.apply_discount("INVALID")
    assert "Mã giảm giá không hợp lệ" in str(exc.value)


def test_apply_discount_when_already_applied_raises():
    """Giỏ đã có mã giảm giá -> ValueError."""
    cart = ShoppingCart()
    cart.apply_discount("SALE10")
    with pytest.raises(ValueError) as exc:
        cart.apply_discount("SALE20")
    assert "Giỏ hàng đã áp dụng mã giảm giá" in str(exc.value)


def test_total_empty_cart_is_zero():
    """Giỏ rỗng -> total = 0."""
    cart = ShoppingCart()
    assert cart.total() == 0.0


def test_total_no_discount():
    """total = subtotal khi không có mã giảm giá."""
    cart = ShoppingCart()
    cart.add_item("a", 4.0, 2)   # 8.0
    cart.add_item("b", 1.5, 2)   # 3.0
    assert cart.total() == pytest.approx(11.0)


def test_total_with_discount_ten_percent():
    """total = subtotal * (1 - 0.10) làm tròn 2 chữ số."""
    cart = ShoppingCart()
    cart.add_item("book", 15.0, 2)   # subtotal = 30.0
    cart.apply_discount("SALE10")
    # 30.0 * 0.9 = 27.0 -> round 27.0
    assert cart.total() == pytest.approx(27.0)


def test_total_with_discount_twenty_percent():
    """total = subtotal * (1 - 0.20) làm tròn 2 chữ số."""
    cart = ShoppingCart()
    cart.add_item("book", 15.0, 2)   # subtotal = 30.0
    cart.apply_discount("SALE20")
    # 30.0 * 0.8 = 24.0 -> round 24.0
    assert cart.total() == pytest.approx(24.0)


def test_total_requires_rounding():
    """Kết quả cần làm tròn đến 2 chữ số thập phân."""
    cart = ShoppingCart()
    # price = 0.15, quantity = 1 => subtotal = 0.15
    cart.add_item("cheap", 0.15, 1)
    cart.apply_discount("SALE10")   # 10% off => 0.15 * 0.9 = 0.135 -> round to 0.14
    assert cart.total() == pytest.approx(0.14)


def test_total_after_clear_is_zero_and_discount_removed():
    """clear() xoá sản phẩm và mã giảm giá."""
    cart = ShoppingCart()
    cart.add_item("a", 5.0, 1)
    cart.apply_discount("SALE10")
    cart.clear()
    assert cart.item_count() == 0
    assert cart.unique_items() == 0
    assert cart.subtotal() == 0.0
    assert cart.discount_code is None
    assert cart.total() == 0.0


def test_apply_discount_after_clear_allowed():
    """Sau clear, có thể áp dụng mã mới."""
    cart = ShoppingCart()
    cart.add_item("a", 10.0, 1)
    cart.apply_discount("SALE10")
    cart.clear()
    # Sau clear, giỏ hàng trống nên có thể áp dụng mã giảm giá mới
    cart.apply_discount("SALE20")
    assert cart.discount_code == "SALE20"
    assert cart.total() == pytest.approx(0.0)
