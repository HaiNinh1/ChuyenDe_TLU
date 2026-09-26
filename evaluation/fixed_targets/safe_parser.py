"""Module 4 (trung bình - khó): xử lý ngoại lệ khi phân tích dữ liệu đầu vào."""


class ConfigError(Exception):
    """Lỗi cấu hình không hợp lệ."""


def parse_int(text, default=None):
    """Chuyển chuỗi sang số nguyên (cho phép khoảng trắng ở hai đầu).

    - Chuyển được -> trả về số nguyên.
    - Không chuyển được (hoặc text là None):
        + nếu default khác None -> trả về default
        + nếu default là None   -> ném ValueError
    """
    try:
        return int(text.strip())
    except (ValueError, AttributeError):
        if default is not None:
            return default
        raise ValueError(f"Không phải số nguyên: {text!r}")


def parse_config(text):
    """Phân tích chuỗi cấu hình dạng "key1=value1;key2=value2" thành dict.

    - Bỏ qua khoảng trắng quanh key/value và các đoạn rỗng (ví dụ ";;").
    - Đoạn không có dấu "=" -> ném ConfigError.
    - Key rỗng -> ném ConfigError.
    - Key trùng lặp -> ném ConfigError.
    Ví dụ: parse_config(" a = 1; b=2 ;") == {"a": "1", "b": "2"}
    """
    result = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ConfigError(f"Thiếu dấu '=' trong: {part!r}")
        key, value = part.split("=", 1)
        key = key.strip()
        if not key:
            raise ConfigError("Key rỗng")
        if key in result:
            raise ConfigError(f"Key bị trùng: {key!r}")
        result[key] = value.strip()
    return result


def get_port(config):
    """Lấy cổng (port) từ dict cấu hình.

    - Không có key "port" -> trả về 8080.
    - Giá trị không phải số nguyên -> ném ConfigError.
    - Port ngoài khoảng [1, 65535] -> ném ConfigError.
    """
    if "port" not in config:
        return 8080
    try:
        port = parse_int(config["port"])
    except ValueError as exc:
        raise ConfigError("Port phải là số nguyên") from exc
    if port < 1 or port > 65535:
        raise ConfigError("Port ngoài khoảng cho phép")
    return port


def safe_ratio(numerator, denominator):
    """Tính tỉ lệ numerator / denominator an toàn.

    - denominator == 0 -> trả về None (không ném lỗi).
    - Tham số không phải số (TypeError) -> trả về None.
    - Ngược lại -> trả về kết quả làm tròn 2 chữ số thập phân.
    """
    try:
        return round(numerator / denominator, 2)
    except ZeroDivisionError:
        return None
    except TypeError:
        return None
