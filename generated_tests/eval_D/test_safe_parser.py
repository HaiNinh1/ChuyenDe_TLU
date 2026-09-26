import pytest
import safe_parser


# ------------------- parse_int -------------------
def test_parse_int_valid_with_whitespace():
    """Chuỗi có khoảng trắng hai đầu được chuyển thành số nguyên."""
    assert safe_parser.parse_int(" 42 ") == 42


def test_parse_int_valid_zero():
    """Chuỗi '0' chuyển thành 0."""
    assert safe_parser.parse_int("0") == 0


def test_parse_int_valid_negative():
    """Chuỗi số nguyên âm được xử lý đúng."""
    assert safe_parser.parse_int("-7") == -7


def test_parse_int_invalid_raises_valueerror():
    """Chuỗi không phải số nguyên gây ValueError khi default=None."""
    with pytest.raises(ValueError) as exc:
        safe_parser.parse_int("abc")
    assert "Không phải số nguyên" in str(exc.value)


def test_parse_int_invalid_with_default_returns_default():
    """Khi chuyển thất bại và default được cung cấp, trả về default."""
    assert safe_parser.parse_int("abc", default=99) == 99


def test_parse_int_none_with_default():
    """None với default không None trả về default."""
    assert safe_parser.parse_int(None, default=5) == 5


def test_parse_int_none_without_default_raises():
    """None mà default=None gây ValueError."""
    with pytest.raises(ValueError) as exc:
        safe_parser.parse_int(None)
    assert "Không phải số nguyên" in str(exc.value)


def test_parse_int_empty_string_with_default():
    """Chuỗi rỗng với default trả về default."""
    assert safe_parser.parse_int("", default=10) == 10


def test_parse_int_empty_string_without_default_raises():
    """Chuỗi rỗng mà default=None gây ValueError."""
    with pytest.raises(ValueError):
        safe_parser.parse_int("")


def test_parse_int_whitespace_only_with_default():
    """Chuỗi chỉ chứa khoảng trắng được xử lý như chuỗi rỗng."""
    assert safe_parser.parse_int("   ", default=42) == 42


def test_parse_int_whitespace_only_without_default_raises():
    """Chuỗi chỉ chứa khoảng trắng mà default=None gây ValueError."""
    with pytest.raises(ValueError):
        safe_parser.parse_int("   ")


# ------------------- parse_config -------------------
def test_parse_config_basic():
    """Chuỗi cấu hình hợp lệ được chuyển thành dict."""
    assert safe_parser.parse_config("a=1;b=2") == {"a": "1", "b": "2"}


def test_parse_config_with_spaces_and_empty_parts():
    """Bỏ qua khoảng trắng và các đoạn rỗng."""
    assert safe_parser.parse_config(" a = 1; b=2 ;") == {"a": "1", "b": "2"}
    assert safe_parser.parse_config(";;a=1;;b=2;;") == {"a": "1", "b": "2"}


def test_parse_config_missing_equal_raises():
    """Đoạn không có '=' gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.parse_config("a")
    assert "Thiếu dấu '='" in str(exc.value)


def test_parse_config_empty_key_raises():
    """Key rỗng gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.parse_config("=value")
    assert "Key rỗng" in str(exc.value)


def test_parse_config_duplicate_key_raises():
    """Key trùng lặp gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.parse_config("a=1;a=2")
    assert "Key bị trùng" in str(exc.value)


def test_parse_config_value_with_spaces():
    """Value có khoảng trắng được strip đúng cách."""
    assert safe_parser.parse_config("key =  value with spaces ") == {"key": "value with spaces"}


def test_parse_config_key_internal_spaces_allowed():
    """Khoảng trắng bên trong key được giữ lại."""
    assert safe_parser.parse_config("ke y=1") == {"ke y": "1"}


def test_parse_config_empty_string_returns_empty_dict():
    """Chuỗi rỗng hoặc chỉ chứa dấu ';' trả về dict rỗng."""
    assert safe_parser.parse_config("") == {}
    assert safe_parser.parse_config(";;") == {}


# ------------------- get_port -------------------
def test_get_port_missing_returns_default():
    """Thiếu key 'port' trả về 8080."""
    assert safe_parser.get_port({}) == 8080
    assert safe_parser.get_port({"other": 5}) == 8080


def test_get_port_valid_string():
    """Giá trị port hợp lệ dưới dạng chuỗi được chuyển thành int."""
    assert safe_parser.get_port({"port": "8080"}) == 8080
    assert safe_parser.get_port({"port": " 8080 "}) == 8080


def test_get_port_non_string_raises():
    """Giá trị port không phải chuỗi (ví dụ int) gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.get_port({"port": 8080})
    assert "Port phải là số nguyên" in str(exc.value)


def test_get_port_invalid_string_raises():
    """Giá trị port không thể chuyển thành int gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.get_port({"port": "abc"})
    assert "Port phải là số nguyên" in str(exc.value)


def test_get_port_out_of_range_low():
    """Port nhỏ hơn 1 gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.get_port({"port": "0"})
    assert "Port ngoài khoảng cho phép" in str(exc.value)


def test_get_port_out_of_range_high():
    """Port lớn hơn 65535 gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.get_port({"port": "65536"})
    assert "Port ngoài khoảng cho phép" in str(exc.value)


def test_get_port_edge_values():
    """Port ở các biên 1 và 65535 được chấp nhận."""
    assert safe_parser.get_port({"port": "1"}) == 1
    assert safe_parser.get_port({"port": "65535"}) == 65535


def test_get_port_negative():
    """Port âm gây ConfigError."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.get_port({"port": "-10"})
    assert "Port ngoài khoảng cho phép" in str(exc.value)


# ------------------- safe_ratio -------------------
def test_safe_ratio_normal():
    """Tính tỉ lệ bình thường và làm tròn 2 chữ số thập phân."""
    assert safe_parser.safe_ratio(1, 2) == 0.5
    assert safe_parser.safe_ratio(5, 2) == 2.5
    assert safe_parser.safe_ratio(1, 3) == 0.33   # round(0.333..., 2)
    assert safe_parser.safe_ratio(2, 3) == 0.67   # round(0.666..., 2)
    assert safe_parser.safe_ratio(-1, 2) == -0.5
    assert safe_parser.safe_ratio(1, -2) == -0.5


def test_safe_ratio_denominator_zero_returns_none():
    """Mẫu số bằng 0 (int hoặc float) trả về None."""
    assert safe_parser.safe_ratio(5, 0) is None
    assert safe_parser.safe_ratio(5, 0.0) is None


def test_safe_ratio_type_error_returns_none():
    """Tham số không phải số (gây TypeError) trả về None."""
    assert safe_parser.safe_ratio("a", 2) is None
    assert safe_parser.safe_ratio(5, "b") is None
    assert safe_parser.safe_ratio(None, 5) is None
    assert safe_parser.safe_ratio(5, None) is None


def test_safe_ratio_both_invalid_type():
    """Cả hai tham số không phải số cũng trả về None."""
    assert safe_parser.safe_ratio("a", "b") is None


def test_parse_config_value_contains_equal_sign():
    """Giá trị có chứa dấu '=' được giữ lại như là phần giá trị."""
    # Một dấu '=' trong giá trị không được phân tách lại
    assert safe_parser.parse_config("a=b=c") == {"a": "b=c"}
    # Khoảng trắng quanh key/value vẫn được bỏ qua, nhưng '=' trong giá trị không bị ảnh hưởng
    assert safe_parser.parse_config("key = val=ue; other=thing") == {"key": "val=ue", "other": "thing"}
    # Nhiều dấu '=' liên tiếp trong giá trị cũng được giữ nguyên
    assert safe_parser.parse_config("x==y") == {"x": "=y"}
    assert safe_parser.parse_config("a===b") == {"a": "==b"}


def test_parse_int_invalid_exact_message():
    """ValueError message phải exatamente như trong source khi chuyển thất bại và default=None."""
    with pytest.raises(ValueError) as exc:
        safe_parser.parse_int("abc")
    assert exc.value.args[0] == "Không phải số nguyên: 'abc'"


def test_parse_config_missing_equal_exact_message():
    """ConfigError message phải exatamente như trong source khi thiếu dấu '='."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.parse_config("a")
    assert exc.value.args[0] == "Thiếu dấu '=' trong: 'a'"


def test_parse_config_empty_key_exact_message():
    """ConfigError message phải exatamente như trong source khi key rỗng."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.parse_config("=value")
    assert exc.value.args[0] == "Key rỗng"


def test_parse_config_duplicate_key_exact_message():
    """ConfigError message phải exactamente như trong source khi key trùng lặp."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.parse_config("a=1;a=2")
    assert exc.value.args[0] == "Key bị trùng: 'a'"


def test_get_port_non_string_exact_message():
    """ConfigError message phải exactamente như trong source khi port không phải chuỗi."""
    with pytest.raises(safe_parser.ConfigError) as exc:
        safe_parser.get_port({"port": 8080})
    assert exc.value.args[0] == "Port phải là số nguyên"
