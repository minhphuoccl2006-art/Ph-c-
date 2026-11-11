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


def calculate_ielts_band(score: int, total: int, skill: str = "READING") -> float:
    """Tính IELTS band score chuẩn hóa từ 1.0 đến 9.0 dựa theo số câu đúng và tổng số câu.
    - Với bài 40 câu: Áp dụng bảng quy đổi Academic chính xác.
    - Với bài ngắn (5, 10, 13, 14, 20 câu): Quy đổi theo tỷ lệ chuẩn năng lực IELTS.
    """
    if not total or total <= 0:
        return 0.0

    if total == 40:
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

    # Quy đổi chuẩn cho các bài luyện ngắn (tính theo tỷ lệ % câu đúng)
    pct = (score / total) * 100
    if pct >= 95: return 9.0
    elif pct >= 88: return 8.5
    elif pct >= 80: return 8.0
    elif pct >= 73: return 7.5
    elif pct >= 65: return 7.0
    elif pct >= 58: return 6.5
    elif pct >= 50: return 6.0
    elif pct >= 42: return 5.5
    elif pct >= 35: return 5.0
    elif pct >= 28: return 4.5
    elif pct >= 20: return 4.0
    elif pct >= 15: return 3.5
    elif pct >= 10: return 3.0
    else: return 2.5


def calculate_score_10(score: int, total: int) -> float:
    """Quy đổi sang thang điểm 10."""
    if not total or total <= 0:
        return 0.0
    return round((score / total) * 10, 1)


def get_band_evaluation(band: float) -> dict:
    """Trả về đánh giá năng lực, cấp độ CEFR và lời khuyên theo Band điểm."""
    if band >= 8.5:
        return {
            "cefr": "C2",
            "level_name": "Thông thạo xuất sắc (Expert / Mastery)",
            "color": "#16a34a",
            "message": "Năng lực ngôn ngữ hoàn hảo, khả năng hiểu các chi tiết phức tạp và hàm ý tinh tế."
        }
    elif band >= 7.0:
        return {
            "cefr": "C1",
            "level_name": "Nâng cao (Advanced / Good User)",
            "color": "#2563eb",
            "message": "Nắm vững ngôn ngữ, xử lý tốt các cấu trúc lập luận học thuật và từ vựng chuyên sâu."
        }
    elif band >= 6.0:
        return {
            "cefr": "B2",
            "level_name": "Khá (Competent User)",
            "color": "#0d9488",
            "message": "Hiểu tốt ý chính và thông tin cụ thể, cần rèn luyện thêm ở các câu hỏi bẫy và từ vựng hiếm."
        }
    elif band >= 5.0:
        return {
            "cefr": "B1",
            "level_name": "Trung bình (Modest User)",
            "color": "#d97706",
            "message": "Nắm được ý tổng quát, cần củng cố thêm kỹ năng Skimming/Scanning và vốn từ vựng nền tảng."
        }
    else:
        return {
            "cefr": "A2",
            "level_name": "Cần cải thiện (Limited User)",
            "color": "#dc2626",
            "message": "Nên tập trung luyện các bài cấp độ Beginner và ôn lại ngữ pháp, từ vựng cốt lõi."
        }



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
