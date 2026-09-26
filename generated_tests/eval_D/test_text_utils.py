import text_utils
import pytest


def test_reverse_words_basic():
    assert text_utils.reverse_words("xin chao ban") == "ban chao xin"


def test_reverse_words_extra_spaces():
    assert text_utils.reverse_words("  xin   chao ban ") == "ban chao xin"


def test_reverse_words_single_word():
    assert text_utils.reverse_words("hello") == "hello"


def test_reverse_words_empty():
    assert text_utils.reverse_words("") == ""


def test_reverse_words_multiple_spaces_between():
    assert text_utils.reverse_words("a  b   c") == "c b a"


def test_reverse_words_punctuation_preserved():
    assert text_utils.reverse_words("hello, world!") == "world! hello,"


def test_is_palindrome_example():
    assert text_utils.is_palindrome("A man, a plan, a canal: Panama") is True


def test_is_palindrome_non_palindrome():
    assert text_utils.is_palindrome("hello") is False


def test_is_palindrome_empty():
    assert text_utils.is_palindrome("") is True


def test_is_palindrome_single_char():
    assert text_utils.is_palindrome("x") is True


def test_is_palindrome_case_insensitive():
    assert text_utils.is_palindrome("RaceCar") is True


def test_is_palindrome_only_non_alnum():
    assert text_utils.is_palindrome("!!!") is True


def test_is_palindrome_even_with_space():
    assert text_utils.is_palindrome("ab ba") is True


def test_is_palindrome_not_palindrome():
    assert text_utils.is_palindrome("ab ca") is False


def test_count_vowels_basic():
    assert text_utils.count_vowels("Hello World") == 3


def test_count_vowels_case_insensitive():
    assert text_utils.count_vowels("AEIOU") == 5


def test_count_vowels_no_vowels():
    assert text_utils.count_vowels("xyz") == 0


def test_count_vowels_empty():
    assert text_utils.count_vowels("") == 0


def test_count_vowels_mixed_case():
    assert text_utils.count_vowels("aEiOu") == 5


def test_count_vowels_non_letters():
    assert text_utils.count_vowels("123!@#") == 0


def test_truncate_when_short():
    assert text_utils.truncate("hello", 10) == "hello"


def test_truncate_exact_len():
    assert text_utils.truncate("hello", 5) == "hello"


def test_truncate_normal_case():
    assert text_utils.truncate("hello world", 8) == "hello..."


def test_truncate_custom_suffix():
    assert text_utils.truncate("hello world", 8, suffix="--") == "hello --"


def test_truncate_max_len_equals_suffix_len():
    # suffix default "..." length 3
    assert text_utils.truncate("abcd", 3) == "..."


def test_truncate_max_len_greater_than_suffix_but_prefix_zero():
    # max_len == len(suffix) -> prefix length 0
    assert text_utils.truncate("", 3) == ""


def test_truncate_raises_value_error():
    with pytest.raises(ValueError):
        text_utils.truncate("any", 2)  # suffix "..." length 3 > max_len 2


def test_slugify_example():
    assert text_utils.slugify("  Hello, World!! 2024 ") == "hello-world-2024"


def test_slugify_leading_trailing_spaces():
    assert text_utils.slugify("   leading and trailing   ") == "leading-and-trailing"


def test_slugify_multiple_non_alnum():
    assert text_utils.slugify("Hello---World") == "hello-world"


def test_slugify_only_non_alnum():
    assert text_utils.slugify("!!!") == ""


def test_slugify_mixed_alnum_and_non_alnum():
    assert text_utils.slugify("a1b2!@#c3d4") == "a1b2-c3d4"


def test_slugify_already_slug():
    assert text_utils.slugify("hello-world") == "hello-world"


def test_slugify_empty_string():
    assert text_utils.slugify("") == ""


def test_count_vowels_lowercase_x():
    """'x' không phải nguyên âm nên phải được đếm là 0."""
    assert text_utils.count_vowels("x") == 0


def test_count_vowels_uppercase_X():
    """'X' (chữ hoa của x) cũng không phải nguyên âm, đếm là 0."""
    assert text_utils.count_vowels("X") == 0


def test_count_vowels_only_x_characters():
    """Chuỗi chứa chỉ các ký tự 'x'/'X' phải trả về 0."""
    assert text_utils.count_vowels("xxXx") == 0
