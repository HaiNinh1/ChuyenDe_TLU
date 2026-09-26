/**
 * Tài khoản ngân hàng đơn giản (số tiền là số nguyên, đơn vị nghìn đồng).
 *
 * - new BankAccount(owner, initialBalance = 0, dailyLimit = 5000):
 *     owner là chuỗi khác rỗng, initialBalance >= 0, nếu không -> ném Error.
 * - deposit(amount): nạp tiền; amount phải là số nguyên > 0, nếu không -> ném RangeError.
 * - withdraw(amount): rút tiền; amount phải là số nguyên > 0 (nếu không -> RangeError).
 *     + amount > số dư -> ném Error("Số dư không đủ").
 *     + TỔNG tiền đã rút trong ngày (cộng dồn mọi lần rút, kể cả lần này) vượt dailyLimit
 *       -> ném Error("Vượt hạn mức rút trong ngày").
 *     + Khi ném lỗi, số dư KHÔNG thay đổi.
 * - transfer(target, amount): chuyển tiền sang tài khoản target = rút ở tài khoản này (theo đúng quy tắc
 *     của withdraw) rồi nạp vào target. target phải là BankAccount khác chính nó, nếu không -> ném Error.
 * - resetDay(): sang ngày mới, tổng tiền đã rút trong ngày về 0.
 * - balance: số dư hiện tại. history(): danh sách giao dịch dạng [loại, số tiền],
 *     loại là "deposit" | "withdraw" | "transfer_out" | "transfer_in".
 */
export class BankAccount {
  constructor(owner, initialBalance = 0, dailyLimit = 5000) {
    if (typeof owner !== "string" || owner.trim() === "") {
      throw new Error("Tên chủ tài khoản không hợp lệ");
    }
    if (initialBalance < 0) {
      throw new Error("Số dư ban đầu không được âm");
    }
    this.owner = owner;
    this.balance = initialBalance;
    this.dailyLimit = dailyLimit;
    this.withdrawnToday = 0;
    this.transactions = [];
  }

  static checkAmount(amount) {
    if (!Number.isInteger(amount) || amount <= 0) {
      throw new RangeError("Số tiền phải là số nguyên dương");
    }
  }

  deposit(amount) {
    BankAccount.checkAmount(amount);
    this.balance += amount;
    this.transactions.push(["deposit", amount]);
  }

  takeOut(amount, kind) {
    BankAccount.checkAmount(amount);
    if (amount > this.balance) {
      throw new Error("Số dư không đủ");
    }
    if (this.withdrawnToday + amount > this.dailyLimit) {
      throw new Error("Vượt hạn mức rút trong ngày");
    }
    this.balance -= amount;
    this.withdrawnToday += amount;
    this.transactions.push([kind, amount]);
  }

  withdraw(amount) {
    this.takeOut(amount, "withdraw");
  }

  transfer(target, amount) {
    if (!(target instanceof BankAccount) || target === this) {
      throw new Error("Tài khoản nhận không hợp lệ");
    }
    this.takeOut(amount, "transfer_out");
    target.balance += amount;
    target.transactions.push(["transfer_in", amount]);
  }

  resetDay() {
    this.withdrawnToday = 0;
  }

  history() {
    return this.transactions.map((t) => [...t]);
  }
}
