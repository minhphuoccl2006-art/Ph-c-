"""
Grading Engine dùng chung cho cả Reading và Listening theo UC-REA-04 và UC-LIS-04.
Chấm điểm theo đáp án hệ thống (correct_answers trong Question).
Không lộ Answer Key ra giao diện client trước khi nộp.
"""

import re


def normalize_answer_string(text: str) -> str:
    """Chuẩn hóa chuỗi trả lời: loại bỏ khoảng trắng thừa, dấu câu kết thúc, đưa về chữ thường."""
    if text is None:
        return ""
    cleaned = str(text).strip().lower()
    cleaned = re.sub(r"[.,;!?\"']+$", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def is_answer_correct(question_type: str, user_answer: str, correct_answers: list) -> bool:
    """Đối chiếu một câu trả lời của học viên với danh sách đáp án đúng.
    
    Hỗ trợ:
    - MCQ / MATCHING: đối chiếu option key hoặc chuỗi chuẩn hóa.
    - TFNG: True/False/Not Given (chấp nhận cả T/F/NG và viết đầy đủ).
    - YNNG: Yes/No/Not Given (chấp nhận cả Y/N/NG và viết đầy đủ).
    - SHORT_TEXT: chấp nhận nhiều biến thể hợp lệ (số từ, số dạng chữ, %...).
    """
    if not user_answer or not str(user_answer).strip():
        return False

    if not correct_answers or not isinstance(correct_answers, list):
        return False

    norm_user = normalize_answer_string(user_answer)
    if not norm_user:
        return False

    expanded_correct = []
    for ans in correct_answers:
        if ans is None:
            continue
        ans_str = str(ans)
        parts = [p.strip() for p in ans_str.split(",") if p.strip()]
        expanded_correct.extend(parts)

    norm_correct = set(normalize_answer_string(a) for a in expanded_correct if a)

    if question_type == "TFNG":
        tfng_map = {
            "true": {"true", "t"},
            "false": {"false", "f"},
            "not given": {"not given", "notgiven", "ng"},
        }
        for correct_item in norm_correct:
            valid_set = tfng_map.get(correct_item, {correct_item})
            if norm_user in valid_set:
                return True
        return norm_user in norm_correct

    elif question_type == "YNNG":
        ynng_map = {
            "yes": {"yes", "y"},
            "no": {"no", "n"},
            "not given": {"not given", "notgiven", "ng"},
        }
        for correct_item in norm_correct:
            valid_set = ynng_map.get(correct_item, {correct_item})
            if norm_user in valid_set:
                return True
        return norm_user in norm_correct

    return norm_user in norm_correct


def calculate_ielts_band(score: int, total: int, skill: str = "READING") -> float | None:
    """Chỉ tính IELTS band estimate cho bài full test có đủ 40 câu theo chuẩn IELTS Academic."""
    if total != 40:
        return None

    if skill.upper() == "READING":
        if score >= 39: return 9.0
        elif score >= 37: return 8.5
        elif score >= 35: return 8.0
        elif score >= 33: return 7.5
        elif score >= 30: return 7.0
        elif score >= 27: return 6.5
        elif score >= 23: return 6.0
        elif score >= 19: return 5.5
        elif score >= 15: return 5.0
        elif score >= 13: return 4.5
        elif score >= 10: return 4.0
        elif score >= 8: return 3.5
        elif score >= 6: return 3.0
        elif score >= 4: return 2.5
        else: return 2.0
    else:  # LISTENING
        if score >= 39: return 9.0
        elif score >= 37: return 8.5
        elif score >= 35: return 8.0
        elif score >= 32: return 7.5
        elif score >= 30: return 7.0
        elif score >= 26: return 6.5
        elif score >= 23: return 6.0
        elif score >= 18: return 5.5
        elif score >= 16: return 5.0
        elif score >= 13: return 4.5
        elif score >= 10: return 4.0
        elif score >= 8: return 3.5
        elif score >= 6: return 3.0
        elif score >= 4: return 2.5
        else: return 2.0


def grade_exercise_submission(exercise, answers_dict: dict) -> dict:
    """Chấm điểm toàn bộ bài làm của một Exercise.
    
    Args:
        exercise: Đối tượng Exercise
        answers_dict: dict mapping str(question_id) -> user_answer (str)
        
    Returns:
        dict chứa:
            - total_questions: tổng số câu hỏi được công bố của bài
            - correct_count: số câu đúng
            - results: dict mapping question_id -> {'is_correct': bool, 'user_answer': str, 'question': Question}
    """
    questions = exercise.questions.filter(status="PUBLISHED").order_by("order_no", "id")
    total_questions = questions.count()

    correct_count = 0
    results = {}

    for question in questions:
        q_id_str = str(question.id)
        user_ans = answers_dict.get(q_id_str, "").strip() if answers_dict else ""
        correct = is_answer_correct(question.question_type, user_ans, question.correct_answers)

        if correct:
            correct_count += 1

        results[question.id] = {
            "question": question,
            "user_answer": user_ans,
            "is_correct": correct,
        }

    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "results": results,
    }
