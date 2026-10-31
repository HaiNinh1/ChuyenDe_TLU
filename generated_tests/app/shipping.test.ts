import { shippingFee, deliveryDays, totalToPay } from './shipping';

test('shippingFee ném RangeError khi total âm', () => {
  expect(() => shippingFee(-1)).toThrow(RangeError);
  expect(() => shippingFee(-0.001)).toThrow(RangeError);
});

// SUSPECTED_BUG: JSDoc quy định total >= 500 miễn phí (0), nhưng code chỉ miễn phí khi total > 500, nên tại 500 code trả 15 vi phạm spec.
test.failing('shippingFee trả 0 khi total bằng 500 theo quy tắc miễn phí', () => {
  expect(shippingFee(500)).toBeCloseTo(0);
});

test('shippingFee trả 0 khi total lớn hơn 500', () => {
  expect(shippingFee(600)).toBeCloseTo(0);
  expect(shippingFee(1000)).toBeCloseTo(0);
});

test('shippingFee trả 15 khi total bằng 200 (biên dưới khoảng 200-500)', () => {
  expect(shippingFee(200)).toBeCloseTo(15);
});

test('shippingFee trả 15 khi total trong khoảng 200 <= total < 500', () => {
  expect(shippingFee(300)).toBeCloseTo(15);
  expect(shippingFee(499.999)).toBeCloseTo(15);
});

test('shippingFee trả 30 khi total nhỏ hơn 200', () => {
  expect(shippingFee(100)).toBeCloseTo(30);
  expect(shippingFee(199.999)).toBeCloseTo(30);
});

test('shippingFee trả 30 khi total bằng 0', () => {
  expect(shippingFee(0)).toBeCloseTo(30);
});

test('shippingFee giảm 50% cho thành viên khi total 100', () => {
  expect(shippingFee(100, true)).toBeCloseTo(15);
});

test('shippingFee giảm 50% cho thành viên khi total 250', () => {
  expect(shippingFee(250, true)).toBeCloseTo(7.5);
});

test('shippingFee giảm 50% cho thành viên khi total 600', () => {
  expect(shippingFee(600, true)).toBeCloseTo(0);
});

test('shippingFee không giảm phí khi không phải thành viên (mặc định)', () => {
  expect(shippingFee(100)).toBeCloseTo(30);
  expect(shippingFee(100, false)).toBeCloseTo(30);
});

test('deliveryDays trả 1 cho khu vực inner', () => {
  expect(deliveryDays("inner")).toBe(1);
});

test('deliveryDays trả 3 cho khu vực outer', () => {
  expect(deliveryDays("outer")).toBe(3);
});

test('deliveryDays trả 7 cho khu vực remote', () => {
  expect(deliveryDays("remote")).toBe(7);
});

test('deliveryDays ném Error khi khu vực không hợp lệ', () => {
  expect(() => deliveryDays("invalid" as any)).toThrow(Error);
});

test('totalToPay(250, true) bằng 257.5 theo ví dụ', () => {
  expect(totalToPay(250, true)).toBeCloseTo(257.5);
});

test('totalToPay(100, false) bằng 130', () => {
  expect(totalToPay(100, false)).toBeCloseTo(130);
});

test('totalToPay(100, true) bằng 115', () => {
  expect(totalToPay(100, true)).toBeCloseTo(115);
});

test('totalToPay(600) bằng 600 vì miễn phí ship', () => {
  expect(totalToPay(600)).toBeCloseTo(600);
});

// SUSPECTED_BUG: Theo JSDoc, totalToPay(500) = 500 + shippingFee(500) = 500 + 0 = 500, nhưng code trả 515 do shippingFee(500) sai spec.
test.failing('totalToPay(500) bằng 500 theo quy tắc miễn phí ship khi total >= 500', () => {
  expect(totalToPay(500)).toBeCloseTo(500);
});

test('totalToPay(200) bằng 215', () => {
  expect(totalToPay(200)).toBeCloseTo(215);
});

test('totalToPay làm tròn kết quả đến 1 chữ số thập phân', () => {
  expect(totalToPay(199.99)).toBeCloseTo(230);
});

test('totalToPay ném RangeError khi total âm', () => {
  expect(() => totalToPay(-10)).toThrow(RangeError);
});
