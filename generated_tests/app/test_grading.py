import pytest
from grading import letter_grade, final_score, pass_status, scholarship_level


def test_letter_grade_A_range():
    assert letter_grade(90) == "A"
    assert letter_grade(95) == "A"
    assert letter_grade(100) == "A"


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: Docstring quy định 80 <= score < 90 trả về 'B', nhưng code dùng `score > 80` khiến score=80 rơi vào nhánh 'C'. Test đúng theo docstring, code vi phạm.")
def test_letter_grade_B_range():
    assert letter_grade(80) == "B"
    assert letter_grade(85) == "B"
    assert letter_grade(89) == "B"


def test_letter_grade_C_range():
    assert letter_grade(65) == "C"
    assert letter_grade(70) == "C"
    assert letter_grade(79) == "C"


def test_letter_grade_D_range():
    assert letter_grade(50) == "D"
    assert letter_grade(55) == "D"
    assert letter_grade(64) == "D"


def test_letter_grade_F_range():
    assert letter_grade(0) == "F"
    assert letter_grade(25) == "F"
    assert letter_grade(49) == "F"


def test_letter_grade_negative_score_raises_ValueError():
    with pytest.raises(ValueError):
        letter_grade(-0.1)


def test_letter_grade_above_100_score_raises_ValueError():
    with pytest.raises(ValueError):
        letter_grade(100.1)


def test_final_score_weighted_sum():
    assert final_score(80, 90, 70) == pytest.approx(83.0)


def test_final_score_with_bonus():
    assert final_score(80, 90, 70, bonus=5) == pytest.approx(88.0)


def test_final_score_capped_at_100():
    assert final_score(100, 100, 100, bonus=10) == pytest.approx(100.0)


def test_final_score_zero_components():
    assert final_score(0, 0, 0) == pytest.approx(0.0)


def test_final_score_component_min_boundary():
    assert final_score(0, 100, 100) == pytest.approx(70.0)


def test_final_score_component_max_boundary():
    assert final_score(100, 0, 0) == pytest.approx(30.0)


def test_final_score_bonus_min_boundary():
    assert final_score(0, 0, 0, bonus=0) == pytest.approx(0.0)


def test_final_score_bonus_max_boundary():
    assert final_score(0, 0, 0, bonus=10) == pytest.approx(10.0)


def test_final_score_rounds_to_one_decimal():
    assert final_score(33, 33, 33) == pytest.approx(33.0)


def test_final_score_midterm_below_zero_raises():
    with pytest.raises(ValueError):
        final_score(-1, 50, 50)


def test_final_score_midterm_above_100_raises():
    with pytest.raises(ValueError):
        final_score(101, 50, 50)


def test_final_score_final_below_zero_raises():
    with pytest.raises(ValueError):
        final_score(50, -1, 50)


def test_final_score_final_above_100_raises():
    with pytest.raises(ValueError):
        final_score(50, 101, 50)


def test_final_score_homework_below_zero_raises():
    with pytest.raises(ValueError):
        final_score(50, 50, -1)


def test_final_score_homework_above_100_raises():
    with pytest.raises(ValueError):
        final_score(50, 50, 101)


def test_final_score_bonus_below_zero_raises():
    with pytest.raises(ValueError):
        final_score(50, 50, 50, bonus=-1)


def test_final_score_bonus_above_10_raises():
    with pytest.raises(ValueError):
        final_score(50, 50, 50, bonus=11)


def test_pass_status_attendance_below_70_percent_cam_thi():
    assert pass_status(100, 0.69) == "CẤM THI"
    assert pass_status(50, 0.0) == "CẤM THI"


def test_pass_status_attendance_exact_70_percent_not_banned():
    assert pass_status(40, 0.7) == "THI LẠI"


def test_pass_status_score_50_or_above_dau():
    assert pass_status(50, 0.8) == "ĐẬU"
    assert pass_status(100, 1.0) == "ĐẬU"


def test_pass_status_score_40_to_less_than_50_thi_lai():
    assert pass_status(40, 0.8) == "THI LẠI"
    assert pass_status(49, 0.8) == "THI LẠI"


def test_pass_status_score_below_40_rot():
    assert pass_status(39, 0.8) == "RỚT"
    assert pass_status(0, 0.8) == "RỚT"


def test_scholarship_has_failed_course_returns_khong():
    assert scholarship_level(4.0, 100, True) == "KHÔNG"
    assert scholarship_level(3.6, 90, True) == "KHÔNG"


def test_scholarship_xuat_sac():
    assert scholarship_level(3.6, 90, False) == "XUẤT SẮC"
    assert scholarship_level(4.0, 100, False) == "XUẤT SẮC"


def test_scholarship_gioi():
    assert scholarship_level(3.2, 80, False) == "GIỎI"
    assert scholarship_level(3.5, 85, False) == "GIỎI"


def test_scholarship_kha():
    assert scholarship_level(2.5, 65, False) == "KHÁ"
    assert scholarship_level(3.0, 70, False) == "KHÁ"


def test_scholarship_below_all_thresholds_returns_khong():
    assert scholarship_level(2.4, 65, False) == "KHÔNG"
    assert scholarship_level(2.5, 64, False) == "KHÔNG"
    assert scholarship_level(3.0, 50, False) == "KHÔNG"
    assert scholarship_level(0.0, 0.0, False) == "KHÔNG"
