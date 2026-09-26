import pytest
import grading


# ------------------- letter_grade -------------------
def test_letter_grade_a_range():
    assert grading.letter_grade(100) == "A"
    assert grading.letter_grade(90) == "A"
    assert grading.letter_grade(95) == "A"


def test_letter_grade_b_range():
    assert grading.letter_grade(89) == "B"
    assert grading.letter_grade(80) == "B"
    assert grading.letter_grade(85) == "B"


def test_letter_grade_c_range():
    assert grading.letter_grade(79) == "C"
    assert grading.letter_grade(65) == "C"
    assert grading.letter_grade(70) == "C"


def test_letter_grade_d_range():
    assert grading.letter_grade(64) == "D"
    assert grading.letter_grade(50) == "D"
    assert grading.letter_grade(55) == "D"


def test_letter_grade_f_range():
    assert grading.letter_grade(49) == "F"
    assert grading.letter_grade(0) == "F"
    assert grading.letter_grade(30) == "F"


def test_letter_grade_invalid():
    with pytest.raises(ValueError):
        grading.letter_grade(-1)
    with pytest.raises(ValueError):
        grading.letter_grade(101)


# ------------------- final_score -------------------
def test_final_score_normal():
    # mid=30, final=40, hw=50, bonus=0 => 0.3*30+0.5*40+0.2*50 = 9+20+10 = 39
    assert grading.final_score(30, 40, 50, 0) == 39.0
    # mid=70, final=80, hw=90, bonus=5 => 21+40+18+5 = 84
    assert grading.final_score(70, 80, 90, 5) == 84.0


def test_final_score_boundaries():
    # all zeros, bonus zero
    assert grading.final_score(0, 0, 0, 0) == 0.0
    # all max, bonus zero => 100
    assert grading.final_score(100, 100, 100, 0) == 100.0
    # all max, bonus max => raw 110 -> capped to 100
    assert grading.final_score(100, 100, 100, 10) == 100.0
    # fractional rounding
    assert grading.final_score(33, 66, 99, 2) == 64.7


def test_final_score_invalid_components():
    with pytest.raises(ValueError):
        grading.final_score(-5, 50, 50, 0)
    with pytest.raises(ValueError):
        grading.final_score(50, 105, 50, 0)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, -1, 0)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 101, 0)


def test_final_score_invalid_bonus():
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 50, -1)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 50, 11)


# ------------------- pass_status -------------------
def test_pass_status_attendance_fails():
    # attendance below 0.7 => CẤM THI regardless of score
    assert grading.pass_status(100, 0.69) == "CẤM THI"
    assert grading.pass_status(0, 0.0) == "CẤM THI"
    assert grading.pass_status(49, 0.699) == "CẤM THI"


def test_pass_status_score_boundaries():
    # attendance sufficient (>=0.7)
    # score >=50 => ĐẬU
    assert grading.pass_status(50, 0.7) == "ĐẬU"
    assert grading.pass_status(80, 0.8) == "ĐẬU"
    # 40 <= score < 50 => THI LẠI
    assert grading.pass_status(40, 0.7) == "THI LẠI"
    assert grading.pass_status(49.9, 0.9) == "THI LẠI"
    # score < 40 => RỚT
    assert grading.pass_status(39, 0.7) == "RỚT"
    assert grading.pass_status(0, 1.0) == "RỚT"


def test_pass_status_attendance_exact_boundary():
    # attendance_rate == 0.7 is NOT < 0.7, so falls to score checks
    assert grading.pass_status(60, 0.7) == "ĐẬU"   # score >=50
    assert grading.pass_status(45, 0.7) == "THI LẠI"
    assert grading.pass_status(30, 0.7) == "RỚT"


# ------------------- scholarship_level -------------------
def test_scholarship_has_failed_course():
    assert grading.scholarship_level(4.0, 100, True) == "KHÔNG"
    assert grading.scholarship_level(2.0, 50, True) == "KHÔNG"


def test_scholarship_xuat_sac():
    assert grading.scholarship_level(3.6, 90, False) == "XUẤT SẮC"
    assert grading.scholarship_level(4.0, 95, False) == "XUẤT SẮC"
    # just below thresholds should not be XUẤT SẮC
    assert grading.scholarship_level(3.59, 90, False) != "XUẤT SẮC"
    assert grading.scholarship_level(3.6, 89, False) != "XUẤT SẮC"


def test_scholarship_gioi():
    assert grading.scholarship_level(3.2, 80, False) == "GIỎI"
    assert grading.scholarship_level(3.5, 85, False) == "GIỎI"
    # below GPA threshold but conduct high enough -> not GIỎI
    assert grading.scholarship_level(3.19, 80, False) != "GIỎI"
    # GPA enough but conduct below threshold -> not GIỎI
    assert grading.scholarship_level(3.2, 79, False) != "GIỎI"


def test_scholarship_kha():
    assert grading.scholarship_level(2.5, 65, False) == "KHÁ"
    assert grading.scholarship_level(3.0, 70, False) == "KHÁ"
    # below GPA threshold
    assert grading.scholarship_level(2.49, 65, False) != "KHÁ"
    # below conduct threshold
    assert grading.scholarship_level(2.5, 64, False) != "KHÁ"


def test_scholarship_khong_otherwise():
    assert grading.scholarship_level(2.0, 50, False) == "KHÔNG"
    assert grading.scholarship_level(3.0, 50, False) == "KHÔNG"   # conduct too low
    assert grading.scholarship_level(2.0, 80, False) == "KHÔNG"   # GPA too low
