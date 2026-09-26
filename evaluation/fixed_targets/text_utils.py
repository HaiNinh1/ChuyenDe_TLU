"""Module 2 (dễ - trung bình): xử lý chuỗi."""


def reverse_words(sentence):
    """Đảo ngược thứ tự các từ trong câu, các từ cách nhau bởi đúng một dấu cách.

    Khoảng trắng thừa ở đầu/cuối/giữa bị bỏ.
    Ví dụ: reverse_words("  xin   chao ban ") == "ban chao xin"
    """
    words = sentence.split()
    return " ".join(reversed(words))


def is_palindrome(text):
    """Kiểm tra chuỗi đối xứng, KHÔNG phân biệt hoa thường và BỎ QUA ký tự không phải chữ/số.

    Ví dụ: is_palindrome("A man, a plan, a canal: Panama") == True
    Chuỗi rỗng được coi là đối xứng.
    """
    cleaned = [ch.lower() for ch in text if ch.isalnum()]
    return cleaned == cleaned[::-1]


def count_vowels(text):
    """Đếm số nguyên âm tiếng Anh (a, e, i, o, u), không phân biệt hoa thường."""
    count = 0
    for ch in text.lower():
        if ch in "aeiou":
            count += 1
    return count


def truncate(text, max_len, suffix="..."):
    """Cắt chuỗi để độ dài KẾT QUẢ (tính cả suffix) không vượt quá max_len.

    - Nếu len(text) <= max_len: trả về nguyên text.
    - Ngược lại: giữ phần đầu của text rồi nối suffix sao cho tổng độ dài đúng bằng max_len.
    - Ném ValueError nếu max_len < len(suffix).
    Ví dụ: truncate("hello world", 8) == "hello..."
    """
    if max_len < len(suffix):
        raise ValueError("max_len quá nhỏ")
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def slugify(title):
    """Chuyển tiêu đề thành slug cho URL.

    - Chữ thường
    - Ký tự chữ/số giữ nguyên, mọi nhóm ký tự còn lại thay bằng một dấu "-"
    - Bỏ dấu "-" ở đầu và cuối
    Ví dụ: slugify("  Hello, World!! 2024 ") == "hello-world-2024"
    """
    result = []
    previous_dash = False
    for ch in title.lower():
        if ch.isalnum():
            result.append(ch)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True
    return "".join(result).strip("-")
