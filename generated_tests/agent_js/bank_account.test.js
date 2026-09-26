import { BankAccount } from './bank_account';

test('constructor creates account with valid owner and default values', () => {
  const acc = new BankAccount('Alice');
  expect(acc.owner).toBe('Alice');
  expect(acc.balance).toBe(0);
  expect(acc.dailyLimit).toBe(5000);
  expect(acc.withdrawnToday).toBe(0);
  expect(acc.history()).toEqual([]);
});

test('constructor accepts custom initialBalance and dailyLimit', () => {
  const acc = new BankAccount('Bob', 1000, 2000);
  expect(acc.balance).toBe(1000);
  expect(acc.dailyLimit).toBe(2000);
});

test('constructor throws Error for non-string owner', () => {
  expect(() => new BankAccount(123)).toThrow(Error);
  expect(() => new BankAccount(null)).toThrow(Error);
  expect(() => new BankAccount(undefined)).toThrow(Error);
});

test('constructor throws Error for empty string owner', () => {
  expect(() => new BankAccount('')).toThrow(Error);
});

test('constructor throws Error for whitespace-only owner', () => {
  expect(() => new BankAccount('   ')).toThrow(Error);
});

test('constructor throws Error for negative initialBalance', () => {
  expect(() => new BankAccount('Charlie', -1)).toThrow(Error);
});

test('deposit increases balance and records transaction', () => {
  const acc = new BankAccount('Dave');
  acc.deposit(300);
  expect(acc.balance).toBe(300);
  expect(acc.history()).toEqual([['deposit', 300]]);
});

test('deposit throws RangeError for zero amount', () => {
  const acc = new BankAccount('Eve');
  expect(() => acc.deposit(0)).toThrow(RangeError);
});

test('deposit throws RangeError for negative amount', () => {
  const acc = new BankAccount('Frank');
  expect(() => acc.deposit(-50)).toThrow(RangeError);
});

test('deposit throws RangeError for non-integer amount', () => {
  const acc = new BankAccount('Grace');
  expect(() => acc.deposit(10.5)).toThrow(RangeError);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('withdraw decreases balance and records transaction when within limits', () => {
  const acc = new BankAccount('Henry', 1000);
  acc.withdraw(400);
  expect(acc.balance).toBe(600);
  expect(acc.history()).toEqual([['withdraw', 400]]);
  expect(acc.withdrawnToday).toBe(400);
});

test('withdraw throws RangeError for zero amount', () => {
  const acc = new BankAccount('Ivy');
  expect(() => acc.withdraw(0)).toThrow(RangeError);
});

test('withdraw throws RangeError for negative amount', () => {
  const acc = new BankAccount('Jack');
  expect(() => acc.withdraw(-20)).toThrow(RangeError);
});

test('withdraw throws RangeError for non-integer amount', () => {
  const acc = new BankAccount('Kate');
  expect(() => acc.withdraw(30.7)).toThrow(RangeError);
});

test('withdraw throws Error when amount exceeds balance', () => {
  const acc = new BankAccount('Leo', 500);
  expect(() => acc.withdraw(600)).toThrow(Error);
  expect(acc.balance).toBe(500); // unchanged
  expect(acc.history()).toEqual([]);
  expect(acc.withdrawnToday).toBe(0);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('withdraw throws Error when amount exceeds daily limit', () => {
  const acc = new BankAccount('Mona', 2000, 500);
  acc.withdraw(300); // first withdrawal
  expect(() => acc.withdraw(300)).toThrow(Error); // 300+300 > 500
  expect(acc.balance).toBe(1400); // unchanged after failed attempt
  expect(acc.history()).toEqual([['withdraw', 300]]);
  expect(acc.withdrawnToday).toBe(300);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('withdraw allows exact balance usage', () => {
  const acc = new BankAccount('Nina', 500);
  acc.withdraw(500);
  expect(acc.balance).toBe(0);
  expect(acc.history()).toEqual([['withdraw', 500]]);
  expect(acc.withdrawnToday).toBe(500);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('withdraw allows exact daily limit usage', () => {
  const acc = new BankAccount('Oscar', 2000, 500);
  acc.withdraw(500);
  expect(acc.balance).toBe(1500);
  expect(acc.history()).toEqual([['withdraw', 500]]);
  expect(acc.withdrawnToday).toBe(500);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('multiple withdrawals sum up to daily limit correctly', () => {
  const acc = new BankAccount('Pam', 2000, 500);
  acc.withdraw(200);
  acc.withdraw(300);
  expect(acc.balance).toBe(1500);
  expect(acc.withdrawnToday).toBe(500);
  expect(() => acc.withdraw(1)).toThrow(Error); // would exceed limit
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('resetDay resets withdrawnToday to zero', () => {
  const acc = new BankAccount('Quinn', 2000, 500);
  acc.withdraw(400);
  acc.resetDay();
  expect(acc.withdrawnToday).toBe(0);
  // after reset, can withdraw up to limit again
  acc.withdraw(500);
  expect(acc.balance).toBe(1100);
  expect(acc.withdrawnToday).toBe(500);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('transfer moves money and records both transfer_out and transfer_in', () => {
  const src = new BankAccount('Rita', 1500);
  const dst = new BankAccount('Sam', 500);
  src.transfer(dst, 400);
  expect(src.balance).toBe(1100);
  expect(dst.balance).toBe(900);
  expect(src.history()).toEqual([['transfer_out', 400]]);
  expect(dst.history()).toEqual([['transfer_in', 400]]);
  expect(src.withdrawnToday).toBe(400);
});

test('transfer throws Error for same account target', () => {
  const acc = new BankAccount('Tina', 1000);
  expect(() => acc.transfer(acc, 200)).toThrow(Error);
  expect(acc.balance).toBe(1000);
  expect(acc.history()).toEqual([]);
});

test('transfer throws Error for non-BankAccount target', () => {
  const acc = new BankAccount('Uma', 1000);
  expect(() => acc.transfer(null, 100)).toThrow(Error);
  expect(() => acc.transfer({}, 100)).toThrow(Error);
  expect(() => acc.transfer(undefined, 100)).toThrow(Error);
  expect(acc.balance).toBe(1000);
  expect(acc.history()).toEqual([]);
});

test('transfer throws RangeError for zero amount', () => {
  const src = new BankAccount('Victor', 1000);
  const dst = new BankAccount('Wendy', 500);
  expect(() => src.transfer(dst, 0)).toThrow(RangeError);
  expect(src.balance).toBe(1000);
  expect(dst.balance).toBe(500);
  expect(src.history()).toEqual([]);
  expect(dst.history()).toEqual([]);
});

test('transfer throws RangeError for negative amount', () => {
  const src = new BankAccount('Xavier', 1000);
  const dst = new BankAccount('Yara', 500);
  expect(() => src.transfer(dst, -50)).toThrow(RangeError);
  expect(src.balance).toBe(1000);
  expect(dst.balance).toBe(500);
});

test('transfer throws RangeError for non-integer amount', () => {
  const src = new BankAccount('Zoe', 1000);
  const dst = new BankAccount('Amy', 500);
  expect(() => src.transfer(dst, 75.3)).toThrow(RangeError);
  expect(src.balance).toBe(1000);
  expect(dst.balance).toBe(500);
});

test('transfer throws Error when source balance insufficient', () => {
  const src = new BankAccount('Ben', 300);
  const dst = new BankAccount('Clara', 200);
  expect(() => src.transfer(dst, 500)).toThrow(Error);
  expect(src.balance).toBe(300);
  expect(dst.balance).toBe(200);
  expect(src.history()).toEqual([]);
  expect(dst.history()).toEqual([]);
  expect(src.withdrawnToday).toBe(0);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('transfer throws Error when source would exceed daily limit', () => {
  const src = new BankAccount('Dan', 2000, 600);
  const dst = new BankAccount('Eli', 500);
  src.withdraw(400); // withdrawnToday = 400, limit left 200
  expect(() => src.transfer(dst, 300)).toThrow(Error); // would exceed limit
  expect(src.balance).toBe(1600); // unchanged
  expect(dst.balance).toBe(500);
  expect(src.history()).toEqual([['withdraw', 400]]);
  expect(dst.history()).toEqual([]);
  expect(src.withdrawnToday).toBe(400);
});

// SUSPECTED_BUG: withdrawnToday not updated
test.failing('transfer respects daily limit after resetDay', () => {
  const src = new BankAccount('Frank', 2000, 600);
  const dst = new BankAccount('Gina', 500);
  src.withdraw(600); // reached limit
  src.resetDay();
  src.transfer(dst, 500); // allowed after reset
  expect(src.balance).toBe(900);
  expect(dst.balance).toBe(1000);
  expect(src.history()).toEqual([['withdraw', 600], ['transfer_out', 500]]);
  expect(dst.history()).toEqual([['transfer_in', 500]]);
  expect(src.withdrawnToday).toBe(500);
});

test('history returns a copy of transactions array', () => {
  const acc = new BankAccount('Hank', 1000);
  acc.deposit(200);
  const hist = acc.history();
  hist.push(['withdraw', 999]); // mutate copy
  expect(acc.history()).toEqual([['deposit', 200]]); // internal unchanged
});

test('history returns empty array when no transactions', () => {
  const acc = new BankAccount('Ivy');
  expect(acc.history()).toEqual([]);
});

test('constructor throws Error with specific message for negative initialBalance', () => {
  expect(() => new BankAccount('Test', -1)).toThrow('Số dư ban đầu không được âm');
});

test('withdraw succeeds when amount within balance and daily limit', () => {
  const acc = new BankAccount('Test', 1000, 5000);
  expect(() => acc.withdraw(300)).not.toThrow();
  expect(acc.balance).toBe(700);
  expect(acc.history()).toEqual([['withdraw', 300]]);
});

test('withdraw throws Error with specific message when amount exceeds daily limit', () => {
  const acc = new BankAccount('Test', 2000, 500);
  acc.withdraw(200);
  expect(() => acc.withdraw(400)).toThrow('Vượt hạn mức rút trong ngày');
  expect(acc.balance).toBe(1800);
  expect(acc.history()).toEqual([['withdraw', 200]]);
});

test('withdraw records correct amount in history', () => {
  const acc = new BankAccount('Test', 1000);
  acc.withdraw(250);
  expect(acc.history()).toEqual([['withdraw', 250]]);
});

test('withdraw records correct transaction type in history', () => {
  const acc = new BankAccount('Test', 1000);
  acc.withdraw(300);
  const hist = acc.history();
  expect(hist.length).toBe(1);
  expect(hist[0][0]).toBe('withdraw');
});
