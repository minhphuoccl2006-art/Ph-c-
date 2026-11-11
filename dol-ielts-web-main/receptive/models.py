"""Model dùng chung của Reading và Listening theo ERD Nhóm 6, bảng B4-B8."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Exercise(models.Model):
    class Skill(models.TextChoices):
        READING = "READING", "Reading"
        LISTENING = "LISTENING", "Listening"

    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    class Status(models.TextChoices):
        PUBLISHED = "PUBLISHED", "Published"
        HIDDEN = "HIDDEN", "Hidden"

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    topic = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=Level.choices)
    skill = models.CharField(max_length=20, choices=Skill.choices)
    passage = models.TextField(null=True, blank=True)
    # Django FileField lưu đường dẫn dưới dạng VARCHAR(500) trong PostgreSQL.
    audio_file = models.FileField(upload_to="listening/", max_length=500, null=True, blank=True)
    time_limit_minutes = models.PositiveIntegerField(default=20, help_text="Thời gian làm bài gợi ý (phút)")
    transcript = models.TextField(null=True, blank=True, help_text="Nội dung lời thoại audio (Listening)")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.HIDDEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.status == self.Status.PUBLISHED:
            if self.skill == self.Skill.READING and not (self.passage or "").strip():
                raise ValidationError({"passage": "Reading phải có passage trước khi công bố."})
            if self.skill == self.Skill.LISTENING and not self.audio_file:
                raise ValidationError({"audio_file": "Listening phải có audio trước khi công bố."})

    def __str__(self):
        return f"{self.skill} - {self.title}"

    class Meta:
        db_table = "reading_listening_exercise"


class Question(models.Model):
    class Type(models.TextChoices):
        MCQ = "MCQ", "Multiple choice"
        SHORT_TEXT = "SHORT_TEXT", "Short text"
        MATCHING = "MATCHING", "Matching"
        TFNG = "TFNG", "True/False/Not Given"
        YNNG = "YNNG", "Yes/No/Not Given"

    class Status(models.TextChoices):
        PUBLISHED = "PUBLISHED", "Published"
        HIDDEN = "HIDDEN", "Hidden"

    id = models.BigAutoField(primary_key=True)
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=30, choices=Type.choices)
    correct_answers = models.JSONField(default=list)  # PostgreSQL: JSONB
    explanation = models.TextField(blank=True)
    evidence_quote = models.TextField(blank=True, default="", help_text="Đoạn văn trích dẫn làm bằng chứng đáp án")
    order_no = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.HIDDEN)

    def clean(self):
        super().clean()
        if not isinstance(self.correct_answers, list):
            raise ValidationError({"correct_answers": "Đáp án phải là một danh sách JSON."})

    def __str__(self):
        return f"{self.exercise_id} / Câu {self.order_no}"

    class Meta:
        db_table = "reading_listening_question"
        ordering = ["order_no", "id"]


class Option(models.Model):
    id = models.BigAutoField(primary_key=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    option_key = models.CharField(max_length=20)
    option_text = models.TextField()
    order_no = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.question_id} - {self.option_key}"

    class Meta:
        db_table = "reading_listening_option"
        ordering = ["order_no", "id"]


class Attempt(models.Model):
    class Mode(models.TextChoices):
        PRACTICE = "PRACTICE", "Luyện tập"
        EXAM = "EXAM", "Thi thử"

    id = models.BigAutoField(primary_key=True)
    submission_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="receptive_attempts")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="attempts")
    exercise_snapshot = models.JSONField(default=dict)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.PRACTICE)
    total_questions = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    correct_answers = models.PositiveIntegerField()
    band_score = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, help_text="Điểm IELTS Band ước tính từ 1.0 đến 9.0")
    score_10 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, help_text="Điểm quy đổi thang điểm 10")
    time_spent_seconds = models.PositiveIntegerField(default=0, help_text="Thời gian làm bài thực tế tính bằng giây")
    started_at = models.DateTimeField()
    # Lượt Attempt chỉ được tạo khi nộp bài; không tạo ở bước bắt đầu.
    submitted_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        super().clean()
        errors = {}
        if self.total_questions is not None and self.total_questions < 1:
            errors["total_questions"] = "Tổng số câu phải lớn hơn 0."
        if (self.correct_answers is not None and self.total_questions is not None
                and self.correct_answers > self.total_questions):
            errors["correct_answers"] = "Số câu đúng không được lớn hơn tổng số câu."
        if self.started_at and self.submitted_at and self.started_at > self.submitted_at:
            errors["started_at"] = "Thời điểm bắt đầu không được sau thời điểm nộp."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Attempt #{self.pk} - User {self.user_id}"

    class Meta:
        db_table = "reading_listening_attempt"


class Answer(models.Model):
    id = models.BigAutoField(primary_key=True)
    attempt = models.ForeignKey(Attempt, on_delete=models.PROTECT, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="submitted_answers")
    question_snapshot = models.JSONField(default=dict)
    user_answer = models.TextField(blank=True)
    is_correct = models.BooleanField()

    def clean(self):
        super().clean()
        if self.attempt_id and self.question_id:
            if self.attempt.exercise_id != self.question.exercise_id:
                raise ValidationError({"question": "Câu hỏi không thuộc bài của lượt luyện này."})

    def __str__(self):
        return f"Answer #{self.pk} - Attempt {self.attempt_id}"

    class Meta:
        db_table = "reading_listening_answer"


class ExerciseProgress(models.Model):
    """Lưu tiến độ làm bài dở dang, autosave, highlights, notes và review flags của học viên."""
    class Mode(models.TextChoices):
        PRACTICE = "PRACTICE", "Luyện tập"
        EXAM = "EXAM", "Thi thử"

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="receptive_progresses")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="progresses")
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.PRACTICE)
    answers = models.JSONField(default=dict, blank=True)
    review_flags = models.JSONField(default=list, blank=True)
    highlights = models.JSONField(default=list, blank=True)
    font_size = models.PositiveIntegerField(default=16)
    time_left_seconds = models.IntegerField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)
    band_score = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, null=True, blank=True)
    last_attempt = models.ForeignKey(Attempt, on_delete=models.SET_NULL, null=True, blank=True, related_name="progress_record")

    def __str__(self):
        return f"Progress User {self.user_id} - Exercise {self.exercise_id} ({self.mode})"

    class Meta:
        db_table = "reading_listening_progress"
        unique_together = [("user", "exercise")]

