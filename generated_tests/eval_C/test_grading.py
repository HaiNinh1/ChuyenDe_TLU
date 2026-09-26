import grading
import pytest


def test_letter_grade_A():
    assert grading.letter_grade(90) == "A"
    assert grading.letter_grade(95) == "A"
    assert grading.letter_grade(100) == "A"


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: Docstring defines 80 <= score < 90 as 'B', but code returns 'C' for score=80 due to using >80 instead of >=80.")
def test_letter_grade_B():
    assert grading.letter_grade(80) == "B"      # lower bound inclusive
    assert grading.letter_grade(85) == "B"
    assert grading.letter_grade(89) == "B"      # just below 90


def test_letter_grade_C():
    assert grading.letter_grade(65) == "C"      # lower bound inclusive
    assert grading.letter_grade(70) == "C"
    assert grading.letter_grade(79) == "C"      # just below 80


def test_letter_grade_D():
    assert grading.letter_grade(50) == "D"      # lower bound inclusive
    assert grading.letter_grade(55) == "D"
    assert grading.letter_grade(64) == "D"      # just below 65


def test_letter_grade_F():
    assert grading.letter_grade(0) == "F"       # lower bound inclusive
    assert grading.letter_grade(25) == "F"
    assert grading.letter_grade(49) == "F"      # just below 50


def test_letter_grade_out_of_range():
    with pytest.raises(ValueError):
        grading.letter_grade(-1)
    with pytest.raises(ValueError):
        grading.letter_grade(101)


def test_final_score_normal():
    # 30% midterm + 50% final + 20% homework + bonus
    assert grading.final_score(80, 90, 70, 5) == 88.0
    assert grading.final_score(0, 0, 0, 0) == 0.0
    assert grading.final_score(100, 100, 100, 0) == 100.0  # capped later


def test_final_score_boundaries():
    # component values at 0 and 100, bonus at 0 and 10
    assert grading.final_score(0, 0, 0, 10) == 10.0
    assert grading.final_score(100, 0, 0, 0) == 30.0
    assert grading.final_score(0, 100, 0, 0) == 50.0
    assert grading.final_score(0, 0, 100, 0) == 20.0
    assert grading.final_score(100, 100, 100, 10) == 100.0  # exceeds 100 -> capped


def test_final_score_rounding():
    # result should be rounded to one decimal place
    assert grading.final_score(33.33, 66.66, 99.99, 0) == 63.3
    assert grading.final_score(55.55, 44.44, 33.33, 2.5) == 48.1


def test_final_score_invalid_component():
    for bad in (-0.1, 100.1):
        with pytest.raises(ValueError):
            grading.final_score(bad, 50, 50)
        with pytest.raises(ValueError):
            grading.final_score(50, bad, 50)
        with pytest.raises(ValueError):
            grading.final_score(50, 50, bad)


def test_final_score_invalid_bonus():
    for bad in (-1, 10.1):
        with pytest.raises(ValueError):
            grading.final_score(50, 50, 50, bad)


def test_pass_status_attendance_below_70():
    # attendance_rate < 0.7 => CẤM THI regardless of score
    assert grading.pass_status(100, 0.69) == "CẤM THI"
    assert grading.pass_status(0, 0.0) == "CẤM THI"
    assert grading.pass_status(49, 0.699) == "CẤM THI"


def test_pass_status_score_above_50():
    assert grading.pass_status(50, 0.7) == "ĐẬU"
    assert grading.pass_status(75, 0.8) == "ĐẬU"
    assert grading.pass_status(100, 0.9) == "ĐẬU"


def test_pass_status_score_between_40_and_50():
    assert grading.pass_status(40, 0.7) == "THI LẠI"
    assert grading.pass_status(45, 0.8) == "THI LẠI"
    assert grading.pass_status(49.9, 0.9) == "THI LẠI"


def test_pass_status_score_below_40():
    assert grading.pass_status(39, 0.7) == "RỚT"
    assert grading.pass_status(0, 0.8) == "RỚT"
    assert grading.pass_status(30, 0.9) == "RỚT"


def test_scholarship_level_failed_course():
    assert grading.scholarship_level(4.0, 100, True) == "KHÔNG"
    assert grading.scholarship_level(2.0, 50, True) == "KHÔNG"


def test_scholarship_level_xuat_sac():
    assert grading.scholarship_level(3.6, 90, False) == "XUẤT SẮC"
    assert grading.scholarship_level(4.0, 95, False) == "XUẤT SẮC"
    # just below thresholds should not match this branch
    assert grading.scholarship_level(3.59, 90, False) != "XUẤT SẮC"
    assert grading.scholarship_level(3.6, 89, False) != "XUẤT SẮC"


def test_scholarship_level_gioi():
    assert grading.scholarship_level(3.2, 80, False) == "GIỎI"
    assert grading.scholarship_level(3.5, 85, False) == "GIỎI"
    # edge cases: GPA just below 3.2 but conduct high enough -> should fall to KHÁ or KHÔNG
    assert grading.scholarship_level(3.19, 80, False) == "KHÁ"
    # conduct just below 80 but GPA high enough -> should fall to KHÁ or KHÔNG
    assert grading.scholarship_level(3.6, 79, False) == "KHÁ"


def test_scholarship_level_kha():
    assert grading.scholarship_level(2.5, 65, False) == "KHÁ"
    assert grading.scholarship_level(3.0, 70, False) == "KHÁ"
    # just below thresholds -> KHÔNG
    assert grading.scholarship_level(2.49, 65, False) == "KHÔNG"
    assert grading.scholarship_level(2.5, 64, False) == "KHÔNG"


def test_scholarship_level_khong_default():
    assert grading.scholarship_level(2.0, 50, False) == "KHÔNG"
    assert grading.scholarship_level(3.0, 60, False) == "KHÔNG"  # conduct <65
    assert grading.scholarship_level(2.0, 80, False) == "KHÔNG"  # GPA <2.5
