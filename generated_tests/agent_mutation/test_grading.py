import pytest
import grading


# ------------------- letter_grade -------------------
def test_letter_grade_A():
    assert grading.letter_grade(90) == "A"
    assert grading.letter_grade(95) == "A"
    assert grading.letter_grade(100) == "A"


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: Docstring specifies 80 <= score < 90 => B, but code returns C for score == 80 due to using > 80 instead of >= 80.")
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
    assert grading.final_score(80, 80, 80, 5) == 85.0
    # rounding test
    assert grading.final_score(50, 50, 50, 1.25) == 51.2
    # cap at 100
    assert grading.final_score(100, 100, 100, 10) == 100.0
    assert grading.final_score(95, 95, 95, 10) == 100.0


def test_final_score_invalid_component():
    with pytest.raises(ValueError):
        grading.final_score(-1, 50, 50)
    with pytest.raises(ValueError):
        grading.final_score(50, 101, 50)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, -0.5)


def test_final_score_invalid_bonus():
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 50, -1)
    with pytest.raises(ValueError):
        grading.final_score(50, 50, 50, 10.1)


# ------------------- pass_status -------------------
def test_pass_status_attendance_low():
    assert grading.pass_status(100, 0.6) == "CẤM THI"
    assert grading.pass_status(0, 0.6) == "CẤM THI"
    assert grading.pass_status(30, 0.69) == "CẤM THI"


def test_pass_status_attendance_ok():
    assert grading.pass_status(50, 0.7) == "ĐẬU"
    assert grading.pass_status(55, 0.8) == "ĐẬU"
    assert grading.pass_status(49, 0.7) == "THI LẠI"
    assert grading.pass_status(40, 0.7) == "THI LẠI"
    assert grading.pass_status(39, 0.7) == "RỚT"
    assert grading.pass_status(0, 0.7) == "RỚT"


def test_pass_status_boundaries():
    assert grading.pass_status(50, 0.7) == "ĐẬU"
    assert grading.pass_status(49.999, 0.7) == "THI LẠI"
    assert grading.pass_status(40, 0.7) == "THI LẠI"
    assert grading.pass_status(39.999, 0.7) == "RỚT"
    # attendance_rate exactly 0.7 is NOT < 0.7, so falls through to score checks
    assert grading.pass_status(0.7, 0.7) == "RỚT"


# ------------------- scholarship_level -------------------
def test_scholarship_has_failed():
    assert grading.scholarship_level(4.0, 100, True) == "KHÔNG"
    assert grading.scholarship_level(0, 0, True) == "KHÔNG"


def test_scholarship_xuat_sac():
    assert grading.scholarship_level(3.6, 90, False) == "XUẤT SẮC"
    assert grading.scholarship_level(4.0, 100, False) == "XUẤT SẮC"
    assert grading.scholarship_level(3.6, 95, False) == "XUẤT SẮC"


def test_scholarship_gioi():
    # gpa >=3.2 and conduct >=80 but not meeting xuat sac
    assert grading.scholarship_level(3.6, 85, False) == "GIỎI"   # xuat sac fails on conduct<90
    assert grading.scholarship_level(3.3, 90, False) == "GIỎI"   # xuat sac fails on gpa<3.6
    assert grading.scholarship_level(3.2, 80, False) == "GIỎI"   # edge


def test_scholarship_kha():
    assert grading.scholarship_level(2.5, 65, False) == "KHÁ"
    assert grading.scholarship_level(2.6, 70, False) == "KHÁ"
    assert grading.scholarship_level(3.0, 65, False) == "KHÁ"
    assert grading.scholarship_level(3.19, 65, False) == "KHÁ"


def test_scholarship_khong():
    # has_failed_course=False but none of the tiers satisfied
    assert grading.scholarship_level(2.4, 70, False) == "KHÔNG"   # gpa<2.5
    assert grading.scholarship_level(3.0, 60, False) == "KHÔNG"   # conduct<65
    assert grading.scholarship_level(3.5, 70, False) == "KHÁ"     # actually KHA, included to show boundary
    # additional KHÔNG cases
    assert grading.scholarship_level(2.0, 80, False) == "KHÔNG"
    assert grading.scholarship_level(3.0, 50, False) == "KHÔNG"
