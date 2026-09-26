import pytest
import grading


# ------------------- letter_grade -------------------
def test_letter_grade_A():
    """90 <= score <= 100 -> 'A'"""
    assert grading.letter_grade(90) == "A"
    assert grading.letter_grade(95) == "A"
    assert grading.letter_grade(100) == "A"


@pytest.mark.xfail(strict=False, reason="SUSPECTED_BUG: Docstring says 80 <= score < 90 -> 'B', but code returns 'C' for score=80.")
def test_letter_grade_B():
    """80 <= score < 90 -> 'B'"""
    assert grading.letter_grade(80) == "B"
    assert grading.letter_grade(85) == "B"
    assert grading.letter_grade(89.999) == "B"


def test_letter_grade_C():
    """65 <= score < 80 -> 'C'"""
    assert grading.letter_grade(65) == "C"
    assert grading.letter_grade(70) == "C"
    assert grading.letter_grade(79.999) == "C"


def test_letter_grade_D():
    """50 <= score < 65 -> 'D'"""
    assert grading.letter_grade(50) == "D"
    assert grading.letter_grade(55) == "D"
    assert grading.letter_grade(64.999) == "D"


def test_letter_grade_F():
    """0 <= score < 50 -> 'F'"""
    assert grading.letter_grade(0) == "F"
    assert grading.letter_grade(25) == "F"
    assert grading.letter_grade(49.999) == "F"


def test_letter_grade_out_of_range_raises():
    """Score < 0 or > 100 raises ValueError"""
    with pytest.raises(ValueError):
        grading.letter_grade(-1)
    with pytest.raises(ValueError):
        grading.letter_grade(100.1)


# ------------------- final_score -------------------
def test_final_score_basic():
    """Normal calculation within bounds"""
    assert grading.final_score(midterm=0, final=0, homework=0, bonus=0) == 0.0
    assert grading.final_score(midterm=100, final=100, homework=100, bonus=0) == 100.0
    assert grading.final_score(midterm=50, final=60, homework=70, bonus=5) == pytest.approx(
        50*0.3 + 60*0.5 + 70*0.2 + 5, rel=1e-9
    )


def test_final_score_capped_at_100():
    """Total > 100 is capped to 100"""
    assert grading.final_score(midterm=100, final=100, homework=100, bonus=10) == 100.0
    with pytest.raises(ValueError):
        grading.final_score(midterm=80, final=90, homework=95, bonus=20)


def test_final_score_rounding():
    """Result rounded to one decimal place"""
    assert grading.final_score(midterm=33, final=33, homework=33, bonus=0.33) == 33.3
    assert grading.final_score(midterm=55, final=56, homework=57, bonus=0) == 55.9


def test_final_score_invalid_component():
    """Component outside [0,100] raises ValueError"""
    with pytest.raises(ValueError):
        grading.final_score(midterm=-1, final=50, homework=50)
    with pytest.raises(ValueError):
        grading.final_score(midterm=50, final=150, homework=50)
    with pytest.raises(ValueError):
        grading.final_score(midterm=50, final=50, homework=-0.5)


def test_final_score_invalid_bonus():
    """Bonus outside [0,10] raises ValueError"""
    with pytest.raises(ValueError):
        grading.final_score(midterm=50, final=50, homework=50, bonus=-1)
    with pytest.raises(ValueError):
        grading.final_score(midterm=50, final=50, homework=50, bonus=10.1)


# ------------------- pass_status -------------------
def test_pass_status_attendance_low():
    """attendance_rate < 0.7 -> 'CẤM THI' regardless of score"""
    assert grading.pass_status(score=100, attendance_rate=0.6) == "CẤM THI"
    assert grading.pass_status(score=0, attendance_rate=0.69) == "CẤM THI"


def test_pass_status_pass():
    """score >= 50 -> 'ĐẬU' when attendance sufficient"""
    assert grading.pass_status(score=50, attendance_rate=0.7) == "ĐẬU"
    assert grading.pass_status(score=75, attendance_rate=0.8) == "ĐẬU"


def test_pass_status_retake():
    """40 <= score < 50 -> 'THI LẠI' when attendance sufficient"""
    assert grading.pass_status(score=40, attendance_rate=0.7) == "THI LẠI"
    assert grading.pass_status(score=49.9, attendance_rate=0.9) == "THI LẠI"


def test_pass_status_fail():
    """score < 40 -> 'RỚT' when attendance sufficient"""
    assert grading.pass_status(score=0, attendance_rate=0.7) == "RỚT"
    assert grading.pass_status(score=39, attendance_rate=1.0) == "RỚT"


# ------------------- scholarship_level -------------------
def test_scholarship_failed_course():
    """has_failed_course=True -> 'KHÔNG'"""
    assert grading.scholarship_level(gpa=4.0, conduct_score=100, has_failed_course=True) == "KHÔNG"
    assert grading.scholarship_level(gpa=2.0, conduct_score=50, has_failed_course=True) == "KHÔNG"


def test_scholarship_xuat_sac():
    """gpa >= 3.6 and conduct_score >= 90 -> 'XUẤT SẮC'"""
    assert grading.scholarship_level(gpa=3.6, conduct_score=90, has_failed_course=False) == "XUẤT SẮC"
    assert grading.scholarship_level(gpa=4.0, conduct_score=95, has_failed_course=False) == "XUẤT SẮC"


def test_scholarship_gioi():
    """gpa >= 3.2 and conduct_score >= 80 -> 'GIỎI' (but not XUẤT SẮC)"""
    assert grading.scholarship_level(gpa=3.2, conduct_score=80, has_failed_course=False) == "GIỎI"
    assert grading.scholarship_level(gpa=3.5, conduct_score=85, has_failed_course=False) == "GIỎI"
    # edge just below XUẤT SẮC threshold for conduct
    assert grading.scholarship_level(gpa=3.6, conduct_score=89, has_failed_course=False) == "GIỎI"


def test_scholarship_kha():
    """gpa >= 2.5 and conduct_score >= 65 -> 'KHÁ' (but not higher tiers)"""
    assert grading.scholarship_level(gpa=2.5, conduct_score=65, has_failed_course=False) == "KHÁ"
    assert grading.scholarship_level(gpa=3.0, conduct_score=70, has_failed_course=False) == "KHÁ"
    # edge just below GIỎI threshold for gpa
    assert grading.scholarship_level(gpa=3.19, conduct_score=85, has_failed_course=False) == "KHÁ"


def test_scholarship_khong_otherwise():
    """All other cases -> 'KHÔNG'"""
    assert grading.scholarship_level(gpa=2.4, conduct_score=70, has_failed_course=False) == "KHÔNG"
    assert grading.scholarship_level(gpa=2.5, conduct_score=64, has_failed_course=False) == "KHÔNG"
    assert grading.scholarship_level(gpa=3.0, conduct_score=60, has_failed_course=False) == "KHÔNG"
    assert grading.scholarship_level(gpa=3.5, conduct_score=70, has_failed_course=False) == "KHÁ"
