import grading
import pytest


# ------------------- letter_grade -------------------
def test_letter_grade_A():
    assert grading.letter_grade(90) == "A"
    assert grading.letter_grade(95) == "A"
    assert grading.letter_grade(100) == "A"


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: Docstring specifies 80 <= score < 90 -> 'B', but code returns 'C' for score == 80 due to using 'score > 80' instead of 'score >= 80'.")
def test_letter_grade_B():
    assert grading.letter_grade(80) == "B"
    assert grading.letter_grade(85) == "B"
    assert grading.letter_grade(89.9) == "B"


def test_letter_grade_C():
    assert grading.letter_grade(65) == "C"
    assert grading.letter_grade(70) == "C"
    assert grading.letter_grade(79.9) == "C"


def test_letter_grade_D():
    assert grading.letter_grade(50) == "D"
    assert grading.letter_grade(55) == "D"
    assert grading.letter_grade(64.9) == "D"


def test_letter_grade_F():
    assert grading.letter_grade(0) == "F"
    assert grading.letter_grade(30) == "F"
    assert grading.letter_grade(49.9) == "F"


def test_letter_grade_invalid():
    with pytest.raises(ValueError):
        grading.letter_grade(-1)
    with pytest.raises(ValueError):
        grading.letter_grade(101)


# ------------------- final_score -------------------
def test_final_score_basic():
    assert grading.final_score(0, 0, 0, 0) == 0.0
    assert grading.final_score(100, 100, 100, 0) == 100.0
    assert grading.final_score(50, 60, 70, 5) == 64.0


def test_final_score_rounding():
    assert grading.final_score(33, 34, 35, 0) == 33.9
    assert grading.final_score(12, 34, 56, 0) == 31.8
    assert grading.final_score(0, 0, 1, 0) == 0.2  # 0.2 rounds to 0.2


def test_final_score_bonus_cap():
    assert grading.final_score(100, 100, 100, 10) == 100.0
    assert grading.final_score(80, 80, 80, 10) == 90.0
    assert grading.final_score(40, 40, 40, 10) == 40.0 + 10.0  # 40*0.3+40*0.5+40*0.2 = 40


def test_final_score_component_boundaries():
    # each component at 0 or 100
    assert grading.final_score(0, 0, 0, 0) == 0.0
    assert grading.final_score(100, 0, 0, 0) == 30.0
    assert grading.final_score(0, 100, 0, 0) == 50.0
    assert grading.final_score(0, 0, 100, 0) == 20.0
    assert grading.final_score(100, 100, 0, 0) == 80.0
    assert grading.final_score(100, 0, 100, 0) == 50.0
    assert grading.final_score(0, 100, 100, 0) == 70.0


def test_final_score_invalid_component():
    with pytest.raises(ValueError):
        grading.final_score(-1, 50, 50, 0)
    with pytest.raises(ValueError):
        grading.final_score(50, 101, 50, 0)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, -5, 0)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 105, 0)


def test_final_score_invalid_bonus():
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 50, -1)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 50, 11)


# ------------------- pass_status -------------------
def test_pass_status_attendance_low():
    assert grading.pass_status(100, 0.6) == "CẤM THI"
    assert grading.pass_status(0, 0.6) == "CẤM THI"
    assert grading.pass_status(30, 0.69) == "CẤM THI"


def test_pass_status_attendance_ok_score_high():
    assert grading.pass_status(60, 0.7) == "ĐẬU"
    assert grading.pass_status(50, 0.8) == "ĐẬU"
    assert grading.pass_status(100, 1.0) == "ĐẬU"


def test_pass_status_attendance_ok_score_border_50():
    assert grading.pass_status(50, 0.7) == "ĐẬU"
    assert grading.pass_status(49.9, 0.7) == "THI LẠI"


def test_pass_status_attendance_ok_score_range_40_50():
    assert grading.pass_status(40, 0.7) == "THI LẠI"
    assert grading.pass_status(45, 0.7) == "THI LẠI"
    assert grading.pass_status(49.9, 0.7) == "THI LẠI"


def test_pass_status_attendance_ok_score_border_40():
    assert grading.pass_status(40, 0.7) == "THI LẠI"
    assert grading.pass_status(39.9, 0.7) == "RỚT"


def test_pass_status_attendance_ok_score_low():
    assert grading.pass_status(0, 0.7) == "RỚT"
    assert grading.pass_status(30, 0.9) == "RỚT"


# ------------------- scholarship_level -------------------
def test_scholarship_failed_course():
    assert grading.scholarship_level(4.0, 100, True) == "KHÔNG"
    assert grading.scholarship_level(0, 0, True) == "KHÔNG"


def test_scholarship_xuat_sac():
    assert grading.scholarship_level(3.6, 90, False) == "XUẤT SẮC"
    assert grading.scholarship_level(4.0, 100, False) == "XUẤT SẮC"
    assert grading.scholarship_level(3.6, 95, False) == "XUẤT SẮC"


def test_scholarship_gioi():
    assert grading.scholarship_level(3.2, 80, False) == "GIỎI"
    assert grading.scholarship_level(3.5, 85, False) == "GIỎI"
    assert grading.scholarship_level(3.2, 90, False) == "GIỎI"


def test_scholarship_kha():
    assert grading.scholarship_level(2.5, 65, False) == "KHÁ"
    assert grading.scholarship_level(3.0, 70, False) == "KHÁ"
    assert grading.scholarship_level(2.5, 80, False) == "KHÁ"


def test_scholarship_khong_otherwise():
    assert grading.scholarship_level(2.4, 65, False) == "KHÔNG"
    assert grading.scholarship_level(2.5, 64, False) == "KHÔNG"
    assert grading.scholarship_level(3.0, 50, False) == "KHÔNG"
    assert grading.scholarship_level(3.6, 80, False) == "GIỎI"  # falls to GIỎI branch


def test_scholarship_boundaries():
    assert grading.scholarship_level(3.6, 89, False) == "GIỎI"
    assert grading.scholarship_level(3.19, 80, False) == "KHÁ"
    assert grading.scholarship_level(2.49, 65, False) == "KHÔNG"
    assert grading.scholarship_level(2.5, 64, False) == "KHÔNG"
