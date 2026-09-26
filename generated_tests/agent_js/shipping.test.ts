import { shippingFee, deliveryDays, totalToPay } from './shipping';

test('shippingFee throws RangeError for negative total', () => {
  expect(() => shippingFee(-1)).toThrow(RangeError);
});

test('shippingFee returns 30 for total < 200 (non-member)', () => {
  expect(shippingFee(0)).toBe(30);
  expect(shippingFee(199)).toBe(30);
});

test('shippingFee returns 15 for 200 <= total < 500 (non-member)', () => {
  expect(shippingFee(200)).toBe(15);
  expect(shippingFee(499)).toBe(15);
});

// SUSPECTED_BUG: JSDoc says total >= 500 => fee 0, but code only free for total > 500
test.failing('shippingFee returns 0 for total >= 500 (non-member)', () => {
  expect(shippingFee(500)).toBe(0);
  expect(shippingFee(501)).toBe(0);
  expect(shippingFee(1000)).toBe(0);
});

// SUSPECTED_BUG: JSDoc says total >= 500 => fee 0, but code only free for total > 500
test.failing('shippingFee applies 50% discount for members', () => {
  expect(shippingFee(0, true)).toBe(15);      // 30 * 0.5
  expect(shippingFee(199, true)).toBe(15);    // 30 * 0.5
  expect(shippingFee(200, true)).toBe(7.5);   // 15 * 0.5
  expect(shippingFee(499, true)).toBe(7.5);   // 15 * 0.5
  expect(shippingFee(500, true)).toBe(0);     // 0 * 0.5
  expect(shippingFee(501, true)).toBe(0);
});

test('deliveryDays returns correct days for each zone', () => {
  expect(deliveryDays('inner')).toBe(1);
  expect(deliveryDays('outer')).toBe(3);
  expect(deliveryDays('remote')).toBe(7);
});

test('deliveryDays throws Error for invalid zone', () => {
  expect(() => deliveryDays('unknown' as any)).toThrow(Error('Khu vực không hợp lệ'));
});

// SUSPECTED_BUG: Depends on shippingFee bug; JSDoc expects free shipping for total >= 500, code gives fee 15
test.failing('totalToPay computes total + shippingFee and rounds to one decimal', () => {
  expect(totalToPay(250, true)).toBe(257.5);
  expect(totalToPay(0)).toBe(30);
  expect(totalToPay(0, true)).toBe(15);
  expect(totalToPay(199)).toBe(229);
  expect(totalToPay(199, true)).toBe(214);
  expect(totalToPay(200)).toBe(215);
  expect(totalToPay(200, true)).toBe(207.5);
  expect(totalToPay(500)).toBe(500);
  expect(totalToPay(500, true)).toBe(500);
  expect(totalToPay(1000)).toBe(1000);
});

test('totalToPay throws RangeError for negative total via shippingFee', () => {
  expect(() => totalToPay(-10)).toThrow(RangeError);
});

test('shippingFee returns 0 for total > 500 (non-member)', () => {
  expect(shippingFee(501)).toBe(0);
  expect(shippingFee(600)).toBe(0);
});

test('shippingFee returns 0 for total > 500 (member)', () => {
  expect(shippingFee(501, true)).toBe(0);
  expect(shippingFee(600, true)).toBe(0);
});

test('totalToPay returns total for total > 500 (non-member)', () => {
  expect(totalToPay(501)).toBe(501);
  expect(totalToPay(600)).toBe(600);
});

test('totalToPay returns total for total > 500 (member)', () => {
  expect(totalToPay(501, true)).toBe(501);
  expect(totalToPay(600, true)).toBe(600);
});
