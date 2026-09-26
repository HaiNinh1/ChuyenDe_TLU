"""Module 3 (trung bình): nhiều nhánh if/else — xếp loại điểm sinh viên."""


def letter_grade(score):
    """Đổi điểm số (thang 100) sang điểm chữ.

    - 90 <= score <= 100 -> "A"
    - 80 <= score < 90   -> "B"
    - 65 <= score < 80   -> "C"
    - 50 <= score < 65   -> "D"
    - 0  <= score < 50   -> "F"
    Ném ValueError nếu score < 0 hoặc score > 100.
    """
    if score < 0 or score > 100:
        raise ValueError("Điểm phải trong khoảng 0-100")
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 65:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def final_score(midterm, final, homework, bonus=0):
    """Tính điểm tổng kết = 30% giữa kỳ + 50% cuối kỳ + 20% bài tập + bonus.

    - Mỗi điểm thành phần phải trong [0, 100], nếu không ném ValueError.
    - bonus phải trong [0, 10], nếu không ném ValueError.
    - Kết quả tối đa là 100 (nếu vượt thì lấy 100), làm tròn 1 chữ số thập phân.
    """
    for value in (midterm, final, homework):
        if value < 0 or value > 100:
            raise ValueError("Điểm thành phần phải trong khoảng 0-100")
    if bonus < 0 or bonus > 10:
        raise ValueError("Bonus phải trong khoảng 0-10")
    total = midterm * 0.3 + final * 0.5 + homework * 0.2 + bonus
    if total > 100:
        total = 100
    return round(total, 1)


def pass_status(score, attendance_rate):
    """Xác định trạng thái qua môn.

    - attendance_rate < 0.7 (dự lớp dưới 70%) -> "CẤM THI" (bất kể điểm)
    - score >= 50                              -> "ĐẬU"
    - 40 <= score < 50                         -> "THI LẠI"
    - score < 40                               -> "RỚT"
    """
    if attendance_rate < 0.7:
        return "CẤM THI"
    if score >= 50:
        return "ĐẬU"
    if score >= 40:
        return "THI LẠI"
    return "RỚT"


def scholarship_level(gpa, conduct_score, has_failed_course):
    """Xét mức học bổng.

    - Có môn rớt (has_failed_course=True) -> "KHÔNG"
    - gpa >= 3.6 và conduct_score >= 90 -> "XUẤT SẮC"
    - gpa >= 3.2 và conduct_score >= 80 -> "GIỎI"
    - gpa >= 2.5 và conduct_score >= 65 -> "KHÁ"
    - còn lại -> "KHÔNG"
    """
    if has_failed_course:
        return "KHÔNG"
    if gpa >= 3.6 and conduct_score >= 90:
        return "XUẤT SẮC"
    if gpa >= 3.2 and conduct_score >= 80:
        return "GIỎI"
    if gpa >= 2.5 and conduct_score >= 65:
        return "KHÁ"
    return "KHÔNG"
