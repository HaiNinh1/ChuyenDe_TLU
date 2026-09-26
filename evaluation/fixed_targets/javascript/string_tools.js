/**
 * Viết hoa chữ cái đầu, các chữ còn lại viết thường.
 * Ví dụ: capitalize("hELLO") -> "Hello"; capitalize("") -> "".
 * @param {string} word
 * @returns {string}
 */
export function capitalize(word) {
  if (word.length === 0) {
    return "";
  }
  return word[0].toUpperCase() + word.slice(1).toLowerCase();
}

/**
 * Kiểm tra chuỗi đối xứng (palindrome), KHÔNG phân biệt hoa/thường và BỎ QUA mọi ký tự
 * không phải chữ cái hoặc chữ số (khoảng trắng, dấu câu...).
 * Ví dụ: isPalindrome("A man, a plan, a canal: Panama") -> true; isPalindrome("abc") -> false.
 * Chuỗi rỗng (hoặc chỉ có dấu câu) được coi là đối xứng.
 * @param {string} text
 * @returns {boolean}
 */
export function isPalindrome(text) {
  const cleaned = text.toLowerCase().replace(/[^a-z0-9]/g, "");
  return cleaned === cleaned.split("").reverse().join("");
}

/**
 * Đếm số nguyên âm (a, e, i, o, u — không phân biệt hoa/thường) trong chuỗi.
 * Ví dụ: countVowels("Hello World") -> 3.
 * @param {string} text
 * @returns {number}
 */
export function countVowels(text) {
  let count = 0;
  for (const ch of text.toLowerCase()) {
    if ("aeiou".includes(ch)) {
      count += 1;
    }
  }
  return count;
}

/**
 * Rút gọn chuỗi cho vừa `maxLength` ký tự.
 * - Nếu độ dài chuỗi <= maxLength: trả về nguyên chuỗi.
 * - Ngược lại: cắt bớt và thêm "..." ở cuối sao cho TỔNG độ dài đúng bằng maxLength.
 *   Ví dụ: truncate("Hello World", 8) -> "Hello...".
 * - maxLength < 3 -> ném RangeError.
 * @param {string} text
 * @param {number} maxLength
 * @returns {string}
 */
export function truncate(text, maxLength) {
  if (maxLength < 3) {
    throw new RangeError("maxLength phải >= 3");
  }
  if (text.length <= maxLength) {
    return text;
  }
  return text.slice(0, maxLength - 3) + "...";
}
