const UNIT_SECONDS = { h: 3600, m: 60, s: 1 };

/**
 * Chuyển chuỗi thời lượng sang tổng số giây.
 * Định dạng: một hoặc nhiều cặp <số nguyên không âm><đơn vị>, đơn vị là h (giờ), m (phút), s (giây),
 * viết liền nhau theo thứ tự bất kỳ, không có khoảng trắng.
 * Ví dụ: parseDuration("1h30m") -> 5400; parseDuration("45s") -> 45; parseDuration("2m10s") -> 130.
 * - Chuỗi rỗng, sai định dạng (vd. "abc", "10", "5x", "1h 30m") -> ném Error("Định dạng không hợp lệ").
 * - Một đơn vị xuất hiện 2 lần (vd. "1h2h") -> ném Error("Đơn vị bị lặp").
 * @param {string} text
 * @returns {number}
 */
export function parseDuration(text) {
  if (!/^(\d+[hms])+$/.test(text)) {
    throw new Error("Định dạng không hợp lệ");
  }
  const seen = new Set();
  let total = 0;
  for (const [, value, unit] of text.matchAll(/(\d+)([hms])/g)) {
    if (seen.has(unit)) {
      throw new Error("Đơn vị bị lặp");
    }
    seen.add(unit);
    total += Number(value) * UNIT_SECONDS[unit];
  }
  return total;
}

/**
 * Định dạng số giây thành chuỗi "XhYmZs", BỎ QUA các phần bằng 0.
 * Ví dụ: formatDuration(5400) -> "1h30m"; formatDuration(59) -> "59s"; formatDuration(3601) -> "1h1s".
 * - seconds = 0 -> "0s".
 * - seconds âm hoặc không phải số nguyên -> ném RangeError.
 * @param {number} seconds
 * @returns {string}
 */
export function formatDuration(seconds) {
  if (!Number.isInteger(seconds) || seconds < 0) {
    throw new RangeError("Số giây phải là số nguyên không âm");
  }
  if (seconds === 0) {
    return "0s";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  let result = "";
  if (hours > 0) {
    result += `${hours}h`;
  }
  if (minutes > 0) {
    result += `${minutes}m`;
  }
  if (secs > 0) {
    result += `${secs}s`;
  }
  return result;
}

/**
 * Cộng hai chuỗi thời lượng, trả về chuỗi đã định dạng.
 * Ví dụ: addDurations("1h", "30m") -> "1h30m"; addDurations("45s", "15s") -> "1m".
 * Chuỗi sai định dạng -> ném Error như parseDuration.
 * @param {string} a
 * @param {string} b
 * @returns {string}
 */
export function addDurations(a, b) {
  return formatDuration(parseDuration(a) + parseDuration(b));
}
