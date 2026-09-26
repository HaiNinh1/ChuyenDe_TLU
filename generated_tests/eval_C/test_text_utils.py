import text_utils

# ------------------- reverse_words -------------------
def test_reverse_words_basic():
    assert text_utils.reverse_words("  xin   chao ban ") == "ban chao xin"

def test_reverse_words_single_word():
    assert text_utils.reverse_words("hello") == "hello"

def test_reverse_words_multiple_spaces():
    assert text_utils.reverse_words("a  b   c    d") == "d c b a"

def test_reverse_words_leading_trailing():
    assert text_utils.reverse_words("   leading and trailing   ") == "trailing and leading"

def test_reverse_words_empty():
    assert text_utils.reverse_words("") == ""

def test_reverse_words_only_spaces():
    assert text_utils.reverse_words("   ") == ""

# ------------------- is_palindrome -------------------
def test_is_palindrome_empty():
    assert text_utils.is_palindrome("") is True

def test_is_palindrome_simple():
    assert text_utils.is_palindrome("Racecar") is True

def test_is_palindrome_with_punctuation():
    assert text_utils.is_palindrome("A man, a plan, a canal: Panama") is True

def test_is_palindrome_non_palindrome():
    assert text_utils.is_palindrome("hello") is False

def test_is_palindrome_single_char():
    assert text_utils.is_palindrome("x") is True

def test_is_palindrome_only_non_alnum():
    assert text_utils.is_palindrome("!!! ???") is True  # cleaned becomes []

def test_is_palindrome_mixed():
    assert text_utils.is_palindrome("Was it a car or a cat I saw?") is True

# ------------------- count_vowels -------------------
def test_count_vowels_basic():
    assert text_utils.count_vowels("Hello World") == 3  # e, o, o

def test_count_vowels_case_insensitive():
    assert text_utils.count_vowels("AEIOUaeiou") == 10

def test_count_vowels_no_vowels():
    assert text_utils.count_vowels("xyz") == 0

def test_count_vowels_empty():
    assert text_utils.count_vowels("") == 0

def test_count_vowels_with_non_letters():
    assert text_utils.count_vowels("a1!e2@i3#o4$u5%") == 5

# ------------------- truncate -------------------
def test_truncate_within_limit():
    assert text_utils.truncate("short", 10) == "short"

def test_truncate_exact_limit():
    assert text_utils.truncate("hello", 5) == "hello"

def test_truncate_needs_cutting():
    assert text_utils.truncate("hello world", 8) == "hello..."

def test_truncate_custom_suffix():
    assert text_utils.truncate("abcdefgh", 6, suffix="!!") == "abcd!!"

def test_truncate_suffix_len_equals_maxlen():
    # max_len == len(suffix) should keep only suffix
    assert text_utils.truncate("anything", 3, suffix="...") == "..."

def test_truncate_raises_when_maxlen_too_small():
    try:
        text_utils.truncate("test", 2, suffix="...")
    except ValueError as e:
        assert str(e) == "max_len quá nhỏ"
    else:
        assert False, "Expected ValueError"

def test_truncate_raises_when_maxlen_less_than_suffix():
    try:
        text_utils.truncate("test", 1, suffix="....")
    except ValueError as e:
        assert str(e) == "max_len quá nhỏ"
    else:
        assert False, "Expected ValueError"

# ------------------- slugify -------------------
def test_slugify_basic():
    assert text_utils.slugify("  Hello, World!! 2024 ") == "hello-world-2024"

def test_slugify_only_alnum():
    assert text_utils.slugify("Abc123") == "abc123"

def test_slugify_multiple_separators():
    assert text_utils.slugify("Foo___Bar---Baz") == "foo-bar-baz"

def test_slugify_leading_trailing_hyphens_removed():
    assert text_utils.slugify("---!!!Hello!!!---") == "hello"

def test_slugify_empty_string():
    assert text_utils.slugify("") == ""

def test_slugify_only_non_alnum():
    assert text_utils.slugify("!!! ???") == ""

def test_slugify_single_char():
    assert text_utils.slugify("A") == "a"

def test_slugify_mixed_with_numbers():
    assert text_utils.slugify("Version 2.0-beta!") == "version-2-0-beta"
