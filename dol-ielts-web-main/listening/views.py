import json
import os
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from core.decorators import hoc_vien_required
from listening.models import ListeningExercise
from receptive.models import Exercise, Attempt, Question, ExerciseProgress, Answer
from receptive.services.submission import submit_receptive_exercise
from receptive.services.grading import calculate_ielts_band, calculate_score_10, get_band_evaluation


@hoc_vien_required
def exercise_list(request):
    """UC-LIS-01 Nâng cấp: Xem danh sách bài luyện Listening.
    Hỗ trợ:
    - Tìm kiếm theo từ khóa (tiêu đề, chủ đề).
    - Lọc theo trình độ (Beginner, Intermediate, Advanced).
    - Lọc theo dạng câu hỏi (MCQ, Completion, Matching...).
    - Lọc theo trạng thái làm bài (Tất cả, Chưa làm, Đang làm dở, Đã hoàn thành).
    - Sắp xếp (Mới nhất, Cũ nhất, Nhiều câu hỏi nhất).
    - Hiển thị nút Tiếp tục cho bài đang làm dở, chế độ Luyện tập và Thi thử.
    """
    queryset = ListeningExercise.objects.filter(status=Exercise.Status.PUBLISHED)

    # 1. Tìm kiếm từ khóa
    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(title__icontains=query) | queryset.filter(topic__icontains=query)

    # 2. Lọc theo trình độ
    level_filter = request.GET.get("level", "").strip()
    if level_filter in [Exercise.Level.BEGINNER, Exercise.Level.INTERMEDIATE, Exercise.Level.ADVANCED]:
        queryset = queryset.filter(level=level_filter)

    # 3. Lọc theo dạng câu hỏi
    qtype_filter = request.GET.get("qtype", "").strip()
    if qtype_filter:
        queryset = queryset.filter(questions__question_type=qtype_filter, questions__status=Question.Status.PUBLISHED).distinct()

    # Lấy thông tin lượt luyện và tiến độ dở dang của học viên cho các bài
    user_attempts = (
        Attempt.objects.filter(user=request.user, exercise__skill=Exercise.Skill.LISTENING)
        .order_by("exercise_id", "-submitted_at")
    )
    attempt_map = {}
    for att in user_attempts:
        if att.exercise_id not in attempt_map:
            attempt_map[att.exercise_id] = att

    user_progresses = ExerciseProgress.objects.filter(user=request.user, exercise__skill=Exercise.Skill.LISTENING)
    progress_map = {prog.exercise_id: prog for prog in user_progresses}

    # 4. Lọc theo trạng thái học viên
    status_filter = request.GET.get("status", "").strip()
    filtered_exercise_ids = []
    if status_filter:
        for ex in queryset:
            prog = progress_map.get(ex.id)
            att = attempt_map.get(ex.id)
            has_completed = bool(att or (prog and prog.is_completed))
            is_in_progress = bool(prog and not prog.is_completed and (prog.answers or prog.time_spent_seconds > 0))

            if status_filter == "COMPLETED" and has_completed:
                filtered_exercise_ids.append(ex.id)
            elif status_filter == "IN_PROGRESS" and is_in_progress:
                filtered_exercise_ids.append(ex.id)
            elif status_filter == "NOT_STARTED" and not has_completed and not is_in_progress:
                filtered_exercise_ids.append(ex.id)
        queryset = queryset.filter(id__in=filtered_exercise_ids)

    # 5. Sắp xếp
    sort_option = request.GET.get("sort", "newest").strip()
    if sort_option == "oldest":
        queryset = queryset.order_by("created_at")
    elif sort_option == "most_questions":
        queryset = queryset.order_by("-questions__count", "-created_at")
    else:
        queryset = queryset.order_by("-created_at")

    # Phân trang: 6 bài mỗi trang
    paginator = Paginator(queryset, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Bổ sung dữ liệu chi tiết cho từng card bài tập
    exercises_data = []
    type_names = {
        "MCQ": "Multiple Choice",
        "SHORT_TEXT": "Completion",
        "MATCHING": "Matching",
        "TFNG": "True/False/Not Given",
        "YNNG": "Yes/No/Not Given",
    }

    for ex in page_obj:
        q_count = ex.questions.filter(status=Question.Status.PUBLISHED).count()
        types = list(ex.questions.filter(status=Question.Status.PUBLISHED).values_list("question_type", flat=True).distinct())
        types_display = ", ".join([type_names.get(t, t) for t in types[:3]])

        att = attempt_map.get(ex.id)
        prog = progress_map.get(ex.id)

        has_completed = bool(att or (prog and prog.is_completed))
        is_in_progress = bool(prog and not prog.is_completed and (prog.answers or prog.time_spent_seconds > 0))

        if has_completed:
            user_status = "COMPLETED"
        elif is_in_progress:
            user_status = "IN_PROGRESS"
        else:
            user_status = "NOT_STARTED"

        latest_percentage = 0
        latest_band = 0.0
        if att and att.total_questions > 0:
            latest_percentage = round((att.correct_answers / att.total_questions) * 100)
            latest_band = float(att.band_score) if (att.band_score and att.band_score > 0) else calculate_ielts_band(att.correct_answers, att.total_questions, skill="LISTENING")

        exercises_data.append({
            "exercise": ex,
            "question_count": q_count,
            "types_display": types_display,
            "latest_attempt": att,
            "latest_percentage": latest_percentage,
            "latest_band": latest_band,
            "progress": prog,
            "user_status": user_status,
            "time_limit": ex.time_limit_minutes or 20,
            "has_audio": bool(ex.audio_file),
        })

    context = {
        "active_nav": "listening",
        "page_obj": page_obj,
        "exercises_data": exercises_data,
        "query": query,
        "level_filter": level_filter,
        "qtype_filter": qtype_filter,
        "status_filter": status_filter,
        "sort_option": sort_option,
        "total_count": paginator.count,
    }
    return render(request, "listening/exercise_list.html", context)


@hoc_vien_required
def exercise_detail(request, pk):
    """UC-LIS-02 Nâng cấp: Phòng thi IELTS Listening trên máy tính.
    - Audio Player nổi bật, cố định ở đầu khu vực làm bài.
    - Practice Mode: Play/Pause, Seekbar, -10s, +10s, chỉnh tốc độ 0.75x/1x/1.25x.
    - Exam Mode: Phát 1 lần, khóa tua ngược/tua tới, khóa chỉnh tốc độ, nút Bắt đầu nghe rõ ràng.
    - Xử lý thiếu file âm thanh với thông báo minh bạch.
    - Autosave câu trả lời qua AJAX, khôi phục khi refresh.
    - Điều hướng số câu hỏi và cờ Review.
    """
    exercise = get_object_or_404(ListeningExercise, pk=pk, status=Exercise.Status.PUBLISHED)
    questions = exercise.questions.filter(status=Question.Status.PUBLISHED).prefetch_related("options").order_by("order_no", "id")

    req_mode = request.GET.get("mode", "").upper()
    mode = ExerciseProgress.Mode.EXAM if req_mode == "EXAM" else ExerciseProgress.Mode.PRACTICE

    progress, created = ExerciseProgress.objects.get_or_create(
        user=request.user,
        exercise=exercise,
        defaults={"mode": mode, "started_at": timezone.now()},
    )

    if request.GET.get("reset") == "1":
        progress.answers = {}
        progress.review_flags = []
        progress.highlights = []
        progress.is_completed = False
        progress.time_spent_seconds = 0
        progress.time_left_seconds = (exercise.time_limit_minutes or 20) * 60
        progress.started_at = timezone.now()
        progress.mode = mode
        progress.save()
    elif not created and req_mode and progress.mode != mode:
        progress.mode = mode
        progress.save(update_fields=["mode"])

    time_limit_seconds = (exercise.time_limit_minutes or 20) * 60
    if progress.time_left_seconds is not None and progress.time_left_seconds > 0:
        time_left_seconds = progress.time_left_seconds
    else:
        time_left_seconds = time_limit_seconds

    # Kiểm tra file audio có tồn tại thực tế trên hệ thống không
    has_audio_file = False
    audio_url = ""
    if exercise.audio_file:
        try:
            if hasattr(exercise.audio_file, "path") and os.path.exists(exercise.audio_file.path):
                has_audio_file = True
                audio_url = exercise.audio_file.url
            elif exercise.audio_file.url:
                has_audio_file = True
                audio_url = exercise.audio_file.url
        except Exception:
            has_audio_file = False

    submission_key = uuid.uuid4()
    started_at = progress.started_at.isoformat() if progress.started_at else timezone.now().isoformat()

    draft_data = {
        "answers": progress.answers or {},
        "review_flags": progress.review_flags or [],
        "font_size": progress.font_size or 16,
        "time_spent_seconds": progress.time_spent_seconds or 0,
        "time_left_seconds": time_left_seconds,
        "mode": progress.mode,
    }

    retry_submission_key = request.GET.get("retry_wrong")
    wrong_q_ids = []
    if retry_submission_key:
        past_att = Attempt.objects.filter(submission_key=retry_submission_key, user=request.user).first()
        if past_att:
            wrong_q_ids = list(past_att.answers.filter(is_correct=False).values_list("question_id", flat=True))

    context = {
        "active_nav": "listening",
        "exercise": exercise,
        "questions": questions,
        "submission_key": submission_key,
        "started_at": started_at,
        "total_questions": questions.count(),
        "mode": progress.mode,
        "has_audio_file": has_audio_file,
        "audio_url": audio_url,
        "time_limit_seconds": time_limit_seconds,
        "draft_data_json": json.dumps(draft_data),
        "wrong_q_ids_json": json.dumps(wrong_q_ids),
        "is_retry_wrong": bool(wrong_q_ids),
    }
    return render(request, "listening/exercise_detail.html", context)


@hoc_vien_required
def exercise_autosave(request, pk):
    """API Autosave cho Listening qua AJAX fetch."""
    if request.method != "POST":
        return HttpResponseBadRequest("Phương thức không được hỗ trợ.")

    exercise = get_object_or_404(ListeningExercise, pk=pk, status=Exercise.Status.PUBLISHED)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Dữ liệu JSON không hợp lệ"}, status=400)

    answers = data.get("answers", {})
    review_flags = data.get("review_flags", [])
    font_size = data.get("font_size", 16)
    time_spent_seconds = data.get("time_spent_seconds", 0)
    time_left_seconds = data.get("time_left_seconds")

    progress, _ = ExerciseProgress.objects.get_or_create(
        user=request.user,
        exercise=exercise,
        defaults={"started_at": timezone.now()},
    )

    if not progress.is_completed:
        progress.answers = answers
        progress.review_flags = review_flags
        progress.font_size = max(12, min(24, int(font_size or 16)))
        progress.time_spent_seconds = max(0, int(time_spent_seconds or 0))
        if time_left_seconds is not None:
            progress.time_left_seconds = max(0, int(time_left_seconds))
        progress.save()

    return JsonResponse({
        "success": True,
        "saved_at": timezone.now().strftime("%H:%M:%S"),
        "answered_count": len([v for v in answers.values() if str(v).strip()]),
    })


@hoc_vien_required
def exercise_submit(request, pk):
    """UC-LIS-03 & UC-LIS-04: Nộp bài Listening & Tự động chấm điểm."""
    if request.method != "POST":
        return HttpResponseBadRequest("Phương thức không được hỗ trợ.")

    exercise = get_object_or_404(ListeningExercise, pk=pk, status=Exercise.Status.PUBLISHED)

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Dữ liệu JSON không hợp lệ"}, status=400)
        answers_dict = data.get("answers", {})
        submission_key = data.get("submission_key")
        started_at_str = data.get("started_at")
        mode = data.get("mode", "PRACTICE")
        time_spent_seconds = data.get("time_spent_seconds", 0)
    else:
        answers_dict = {}
        for key, val in request.POST.items():
            if key.startswith("answer_"):
                q_id = key.replace("answer_", "")
                answers_dict[q_id] = val
        submission_key = request.POST.get("submission_key")
        started_at_str = request.POST.get("started_at")
        mode = request.POST.get("mode", "PRACTICE")
        time_spent_seconds = request.POST.get("time_spent_seconds", 0)

    started_at = None
    if started_at_str:
        try:
            started_at = timezone.datetime.fromisoformat(started_at_str)
        except Exception:
            started_at = timezone.now()

    try:
        attempt, created = submit_receptive_exercise(
            user=request.user,
            exercise=exercise,
            answers_dict=answers_dict,
            started_at=started_at,
            submission_key=submission_key,
            mode=mode,
            time_spent_seconds=time_spent_seconds,
        )
    except Exception as e:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json":
            return JsonResponse({"error": str(e)}, status=400)
        return render(request, "listening/error.html", {"error_message": str(e)})

    result_url = reverse("listening:attempt_result", kwargs={"submission_key": attempt.submission_key})

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json":
        return JsonResponse({"success": True, "result_url": result_url, "created": created})

    return redirect(result_url)


@hoc_vien_required
def attempt_result(request, submission_key):
    """UC-LIS-05 Nâng cấp: Xem kết quả bài làm Listening.
    - Điểm số chính xác, tỷ lệ %, phân loại Đúng / Sai / Bỏ trống.
    - Audio player recap để nghe lại bài sau khi thi.
    - Transcript bài nghe đầy đủ (chỉ hiển thị sau khi nộp bài).
    - Phân tích chi tiết theo dạng câu hỏi (Breakdown by question type).
    - Lịch sử các lần làm trước của học viên cho bài nghe này.
    - Nút Làm lại bài, Luyện lại câu sai, Quay về danh sách.
    """
    attempt = get_object_or_404(Attempt, submission_key=submission_key)

    if attempt.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Bạn không có quyền xem kết quả của lượt luyện này.")

    answers = attempt.answers.select_related("question").order_by("question__order_no", "id")

    correct_count = attempt.correct_answers
    total_count = attempt.total_questions
    wrong_count = 0
    unanswered_count = 0

    type_stats = {}
    type_name_map = {
        "MCQ": "Multiple Choice",
        "SHORT_TEXT": "Completion",
        "MATCHING": "Matching",
        "TFNG": "True / False / Not Given",
        "YNNG": "Yes / No / Not Given",
    }

    answers_display = []
    for ans in answers:
        q_snap = ans.question_snapshot or {}
        q_type = q_snap.get("question_type", ans.question.question_type if ans.question else "MCQ")
        q_type_name = type_name_map.get(q_type, q_type)

        if q_type_name not in type_stats:
            type_stats[q_type_name] = {"total": 0, "correct": 0}
        type_stats[q_type_name]["total"] += 1

        correct_list = q_snap.get("correct_answers", [])
        correct_display = ", ".join([str(c) for c in correct_list]) if correct_list else ""
        user_ans = ans.user_answer.strip() if ans.user_answer else ""

        if not user_ans:
            status = "unanswered"
            unanswered_count += 1
        elif ans.is_correct:
            status = "correct"
            type_stats[q_type_name]["correct"] += 1
        else:
            status = "wrong"
            wrong_count += 1

        answers_display.append({
            "question_id": ans.question_id,
            "order_no": q_snap.get("order_no", ans.question.order_no if ans.question else 1),
            "question_type": q_type_name,
            "question_text": q_snap.get("question_text", ans.question.question_text if ans.question else ""),
            "user_answer": user_ans if user_ans else "Chưa trả lời",
            "correct_answer": correct_display,
            "explanation": q_snap.get("explanation", ans.question.explanation if ans.question else ""),
            "evidence_quote": q_snap.get("evidence_quote", getattr(ans.question, "evidence_quote", "")),
            "status": status,
        })

    type_breakdown = []
    for t_name, data in type_stats.items():
        pct = round((data["correct"] / data["total"] * 100)) if data["total"] > 0 else 0
        type_breakdown.append({
            "name": t_name,
            "total": data["total"],
            "correct": data["correct"],
            "percent": pct,
        })

    percentage = round((correct_count / total_count * 100), 1) if total_count > 0 else 0

    # Tính điểm IELTS Band và Điểm thang 10
    band_score = float(attempt.band_score) if (attempt.band_score and attempt.band_score > 0) else calculate_ielts_band(correct_count, total_count, skill="LISTENING")
    score_10 = float(attempt.score_10) if (attempt.score_10 and attempt.score_10 > 0) else calculate_score_10(correct_count, total_count)
    evaluation = get_band_evaluation(band_score)

    if not attempt.band_score or attempt.band_score == 0:
        Attempt.objects.filter(id=attempt.id).update(band_score=band_score, score_10=score_10)

    time_spent = attempt.time_spent_seconds
    if not time_spent and attempt.started_at and attempt.submitted_at:
        time_spent = int((attempt.submitted_at - attempt.started_at).total_seconds())
    time_spent = max(0, time_spent)
    minutes = time_spent // 60
    seconds = time_spent % 60
    time_spent_display = f"{minutes} phút {seconds} giây" if minutes > 0 else f"{seconds} giây"

    # Lấy thông tin file audio và transcript từ snapshot hoặc model
    ex_snap = attempt.exercise_snapshot or {}
    audio_url = ex_snap.get("audio_file") or (attempt.exercise.audio_file.url if attempt.exercise.audio_file else "")
    transcript = ex_snap.get("transcript") or attempt.exercise.transcript or ""

    history_attempts = (
        Attempt.objects.filter(user=request.user, exercise=attempt.exercise)
        .order_by("-submitted_at")[:8]
    )

    context = {
        "active_nav": "listening",
        "attempt": attempt,
        "exercise": attempt.exercise,
        "correct_count": correct_count,
        "total_count": total_count,
        "wrong_count": wrong_count,
        "unanswered_count": unanswered_count,
        "percentage": percentage,
        "ielts_band": band_score,
        "band_score": band_score,
        "score_10": score_10,
        "evaluation": evaluation,
        "time_spent_display": time_spent_display,
        "type_breakdown": type_breakdown,
        "answers_display": answers_display,
        "audio_url": audio_url,
        "transcript": transcript,
        "history_attempts": history_attempts,
        "has_wrong_questions": wrong_count > 0,
    }
    return render(request, "listening/attempt_result.html", context)
