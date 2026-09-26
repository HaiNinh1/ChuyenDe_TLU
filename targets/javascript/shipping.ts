/** Khu vực giao hàng. */
export type Zone = "inner" | "outer" | "remote";

/**
 * Tính phí giao hàng (đơn vị: nghìn đồng) theo tổng tiền đơn hàng.
 * - total < 0 -> ném RangeError.
 * - total >= 500 -> miễn phí (0).
 * - 200 <= total < 500 -> 15.
 * - total < 200 -> 30.
 * - Thành viên (isMember = true) được giảm 50% phí giao hàng.
 * Ví dụ: shippingFee(100) -> 30; shippingFee(100, true) -> 15; shippingFee(600) -> 0.
 */
export function shippingFee(total: number, isMember: boolean = false): number {
  if (total < 0) {
    throw new RangeError("Tổng tiền không được âm");
  }
  let fee: number;
  if (total > 500) {
    fee = 0;
  } else if (total >= 200) {
    fee = 15;
  } else {
    fee = 30;
  }
  return isMember ? fee / 2 : fee;
}

/**
 * Số ngày giao hàng dự kiến theo khu vực: "inner" -> 1, "outer" -> 3, "remote" -> 7.
 * Khu vực khác -> ném Error("Khu vực không hợp lệ").
 */
export function deliveryDays(zone: Zone): number {
  switch (zone) {
    case "inner":
      return 1;
    case "outer":
      return 3;
    case "remote":
      return 7;
    default:
      throw new Error("Khu vực không hợp lệ");
  }
}

/**
 * Tổng tiền phải trả = total + shippingFee(total, isMember), làm tròn đến 1 chữ số thập phân.
 * Ví dụ: totalToPay(250, true) -> 257.5.
 */
export function totalToPay(total: number, isMember: boolean = false): number {
  return Math.round((total + shippingFee(total, isMember)) * 10) / 10;
}
