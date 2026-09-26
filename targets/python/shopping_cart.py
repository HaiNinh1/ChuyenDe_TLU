"""Module 5 (khó nhất): một class có trạng thái — giỏ hàng."""


class ShoppingCart:
    """Giỏ hàng đơn giản.

    Mỗi sản phẩm lưu theo tên, gồm đơn giá (price) và số lượng (quantity).
    Mã giảm giá hợp lệ: "SALE10" (giảm 10%), "SALE20" (giảm 20%).
    Chỉ áp dụng được MỘT mã giảm giá cho mỗi giỏ.
    """

    DISCOUNT_CODES = {"SALE10": 0.10, "SALE20": 0.20}

    def __init__(self):
        self.items = {}  # tên -> {"price": ..., "quantity": ...}
        self.discount_code = None

    def add_item(self, name, price, quantity=1):
        """Thêm sản phẩm.

        - price phải > 0 và quantity phải >= 1, nếu không ném ValueError.
        - Nếu sản phẩm đã có: cộng dồn số lượng; đơn giá mới phải bằng đơn giá cũ,
          nếu khác ném ValueError.
        """
        if price <= 0:
            raise ValueError("Giá phải lớn hơn 0")
        if quantity < 1:
            raise ValueError("Số lượng phải >= 1")
        if name in self.items:
            if self.items[name]["price"] != price:
                raise ValueError("Đơn giá không khớp với sản phẩm đã có")
            self.items[name]["quantity"] += quantity
        else:
            self.items[name] = {"price": price, "quantity": quantity}

    def remove_item(self, name, quantity=1):
        """Bớt số lượng sản phẩm.

        - Sản phẩm không có trong giỏ -> ném KeyError.
        - quantity lớn hơn số lượng đang có -> ném ValueError.
        - Nếu số lượng còn lại bằng 0 thì sản phẩm bị XOÁ khỏi giỏ.
        """
        if name not in self.items:
            raise KeyError(name)
        current = self.items[name]["quantity"]
        if quantity > current:
            raise ValueError("Không đủ số lượng để bớt")
        self.items[name]["quantity"] = current - quantity
        if self.items[name]["quantity"] < 0:
            del self.items[name]

    def item_count(self):
        """Tổng số lượng tất cả sản phẩm trong giỏ."""
        return sum(item["quantity"] for item in self.items.values())

    def unique_items(self):
        """Số loại sản phẩm khác nhau trong giỏ."""
        return len(self.items)

    def subtotal(self):
        """Tổng tiền trước giảm giá."""
        return sum(item["price"] * item["quantity"] for item in self.items.values())

    def apply_discount(self, code):
        """Áp dụng mã giảm giá.

        - Mã không hợp lệ -> ném ValueError.
        - Giỏ đã có mã giảm giá -> ném ValueError.
        """
        if code not in self.DISCOUNT_CODES:
            raise ValueError("Mã giảm giá không hợp lệ")
        if self.discount_code is not None:
            raise ValueError("Giỏ hàng đã áp dụng mã giảm giá")
        self.discount_code = code

    def total(self):
        """Tổng tiền phải trả sau giảm giá, làm tròn 2 chữ số thập phân.

        Giỏ rỗng -> 0.
        """
        amount = self.subtotal()
        if self.discount_code is not None:
            amount = amount * (1 - self.DISCOUNT_CODES[self.discount_code])
        return round(amount, 2)

    def clear(self):
        """Xoá toàn bộ sản phẩm và mã giảm giá."""
        self.items = {}
        self.discount_code = None
