from safe_parser import ConfigError, parse_int, parse_config, get_port
from safe_parser import get_port
import pytest
from safe_parser import (
    ConfigError,
    parse_int,
    parse_config,
    get_port,
    safe_ratio,
)


# ------------------- parse_int -------------------
def test_parse_int_valid():
    assert parse_int("42") == 42
    assert parse_int("  -7  ") == -7


def test_parse_int_with_default():
    assert parse_int(None, default=5) == 5
    assert parse_int("not_a_number", default=0) == 0


def test_parse_int_invalid_raises():
    with pytest.raises(ValueError):
        parse_int("abc")
    with pytest.raises(ValueError):
        parse_int("")  # empty string after strip raises


# ------------------- parse_config -------------------
def test_parse_config_basic():
    assert parse_config("a=1;b=2") == {"a": "1", "b": "2"}


def test_parse_config_whitespace_and_empty_parts():
    assert parse_config(" a = 1 ; b=2 ;") == {"a": "1", "b": "2"}
    assert parse_config(";;a=1;;b=2;;") == {"a": "1", "b": "2"}


def test_parse_config_value_contains_equal():
    assert parse_config("key=val=ue") == {"key": "val=ue"}


def test_parse_config_missing_equal():
    with pytest.raises(ConfigError):
        parse_config("noglue")


def test_parse_config_empty_key():
    with pytest.raises(ConfigError):
        parse_config("=value")


def test_parse_config_duplicate_key():
    with pytest.raises(ConfigError):
        parse_config("a=1;a=2")


# ------------------- get_port -------------------
def test_get_port_missing_returns_default():
    assert get_port({}) == 8080
    assert get_port({"host": "localhost"}) == 8080


def test_get_port_valid_values():
    assert get_port({"port": "8080"}) == 8080
    assert get_port({"port": "1"}) == 1
    assert get_port({"port": "65535"}) == 65535


def test_get_port_out_of_range_raises():
    with pytest.raises(ConfigError):
        get_port({"port": "0"})
    with pytest.raises(ConfigError):
        get_port({"port": "-10"})
    with pytest.raises(ConfigError):
        get_port({"port": "65536"})


def test_get_port_non_integer_raises():
    with pytest.raises(ConfigError):
        get_port({"port": "abc"})
    with pytest.raises(ConfigError):
        get_port({"port": None})  # None causes ValueError in parse_int -> ConfigError


# ------------------- safe_ratio -------------------
def test_safe_ratio_normal():
    assert safe_ratio(1, 2) == 0.5
    assert safe_ratio(2, 3) == pytest.approx(0.67)  # 0.666... rounded to 2 dp
    assert safe_ratio(-1, 4) == -0.25
    assert safe_ratio(1.5, 2) == pytest.approx(0.75)


def test_safe_ratio_denominator_zero():
    assert safe_ratio(5, 0) is None
    assert safe_ratio(0, 0) is None


def test_safe_ratio_type_error():
    assert safe_ratio("a", 2) is None
    assert safe_ratio(5, "b") is None
    assert safe_ratio(None, 5) is None
    assert safe_ratio(5, None) is None
    assert safe_ratio("x", "y") is None


# Optional: test that rounding behaves as described (two decimal places)
def test_safe_ratio_rounding_edge():
    # 1/3 = 0.333... -> 0.33
    assert safe_ratio(1, 3) == pytest.approx(0.33)
    # 2/3 = 0.666... -> 0.67
    assert safe_ratio(2, 3) == pytest.approx(0.67)
    # 1/6 = 0.1666... -> 0.17
    assert safe_ratio(1, 6) == pytest.approx(0.17)


def test_parse_int_value_error_message():
    with pytest.raises(ValueError) as excinfo:
        parse_int("abc")
    assert str(excinfo.value) == "Không phải số nguyên: 'abc'"


def test_parse_int_empty_string_message():
    with pytest.raises(ValueError) as excinfo:
        parse_int("")
    assert str(excinfo.value) == "Không phải số nguyên: ''"


def test_parse_config_missing_equal_message():
    with pytest.raises(ConfigError) as excinfo:
        parse_config("noglue")
    assert str(excinfo.value) == "Thiếu dấu '=' trong: 'noglue'"


def test_parse_config_empty_key_message():
    with pytest.raises(ConfigError) as excinfo:
        parse_config("=value")
    assert str(excinfo.value) == "Key rỗng"


def test_parse_config_duplicate_key_message():
    with pytest.raises(ConfigError) as excinfo:
        parse_config("a=1;a=2")
    assert str(excinfo.value) == "Key bị trùng: 'a'"


def test_get_port_non_integer_message():
    with pytest.raises(ConfigError) as excinfo:
        get_port({"port": "abc"})
    assert str(excinfo.value) == "Port phải là số nguyên"
