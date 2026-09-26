# Sơ đồ luồng của agent (vòng lặp tự cải tiến)

Xem sơ đồ: mở file này trên GitHub/GitLab, VS Code (extension "Markdown Preview Mermaid Support")
hoặc dán vào https://mermaid.live.

```mermaid
flowchart TD
    START([Bắt đầu: module Python]) --> MEM{Bật bộ nhớ?}
    MEM -- có --> LESSON[Lấy bài học liên quan<br/>từ memory.json]
    MEM -- không --> GEN
    LESSON --> GEN[LLM sinh bộ test ban đầu]
    GEN --> RUN[Runner: chạy pytest + coverage<br/>trong thư mục tạm, có timeout]
    RUN --> LOG[(Ghi log vòng lặp<br/>logs/*.json)]
    LOG --> MAX{Hết số vòng<br/>tối đa?}
    MAX -- có --> STOP([DỪNG + lưu kết quả])
    MAX -- chưa --> COL{File test chạy được?<br/>syntax / import}

    COL -- không --> FIXALL[LLM sửa CẢ FILE test<br/>+ rút ra LESSON]
    FIXALL --> RUN

    COL -- được --> FAIL{Có test FAIL?}
    FAIL -- có --> CLS[LLM phân loại từng test fail]
    CLS --> KIND{Loại?}
    KIND -- TEST_WRONG --> ATT{Đã sửa quá<br/>N lần?}
    ATT -- chưa --> FIXT[LLM sửa đúng hàm test đó]
    ATT -- rồi --> DEL[Xoá test]
    KIND -- SUSPECTED_BUG --> MARK[GIỮ test, gắn nhãn<br/>xfail SUSPECTED_BUG<br/>KHÔNG sửa cho khớp code]
    FIXT --> RUN
    DEL --> RUN
    MARK --> RUN

    FAIL -- không --> PHASE{Phase?}
    PHASE -- coverage --> COV{Coverage đạt ngưỡng?}
    COV -- chưa, vẫn đang tăng --> ADDCOV[Gửi dòng/nhánh chưa phủ<br/>LLM viết THÊM test]
    ADDCOV --> RUN
    COV -- đạt / không tăng nữa --> MUTON{Bật mutation?}
    MUTON -- không --> STOP
    MUTON -- có --> MUT

    PHASE -- mutation --> MUT[Chạy mutation testing<br/>giới hạn số mutant]
    MUT --> MSCORE{Mutation score đạt<br/>hoặc không tăng nữa?}
    MSCORE -- đạt / không tăng --> STOP
    MSCORE -- chưa --> KILL[Gửi mutant còn sống<br/>LLM viết test giết mutant]
    KILL --> RUN

    STOP --> SAVE[Lưu test cuối cùng<br/>+ bài học vào memory]
```

## Chú thích
- **Mỗi mũi tên quay về "Runner" là một vòng lặp.** Mỗi vòng thường tốn 1 lần gọi LLM
  (riêng bước phân loại + sửa test tốn 2 lần).
- **Thứ tự ưu tiên:** sửa file hỏng → xử lý test fail → tăng coverage → giết mutant. Không tăng coverage khi còn
  test fail, vì coverage của một bộ test "đỏ" không đáng tin.
- **Điều kiện dừng:** đạt ngưỡng, không cải thiện sau `patience` lần thử liên tiếp, hết `max_iterations`,
  hoặc lỗi gọi LLM (dừng êm, giữ bộ test tốt nhất).
