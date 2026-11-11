from django.test import SimpleTestCase, TestCase
from django.contrib.auth.models import User, Group
from receptive.models import Exercise, Question, Option, Attempt, Answer, ExerciseProgress
from receptive.services.grading import is_answer_correct, normalize_answer_string, calculate_ielts_band
from receptive.services.submission import submit_receptive_exercise


class ReceptiveGradingTests(SimpleTestCase):
    def test_normalize_answer_string(self):
        self.assertEqual(normalize_answer_string("  Hello   World  "), "hello world")
        self.assertEqual(normalize_answer_string("linguistic determinism."), "linguistic determinism")
        self.assertEqual(normalize_answer_string(""), "")
        self.assertEqual(normalize_answer_string(None), "")

    def test_grading_mcq(self):
        self.assertTrue(is_answer_correct("MCQ", "A", ["A"]))
        self.assertTrue(is_answer_correct("MCQ", "b", ["B"]))
        self.assertFalse(is_answer_correct("MCQ", "C", ["A", "B"]))

    def test_grading_tfng_ynng(self):
        self.assertTrue(is_answer_correct("TFNG", "true", ["True"]))
        self.assertTrue(is_answer_correct("TFNG", "t", ["True"]))
        self.assertTrue(is_answer_correct("TFNG", "F", ["False"]))
        self.assertTrue(is_answer_correct("TFNG", "NOT GIVEN", ["Not Given"]))
        self.assertTrue(is_answer_correct("TFNG", "ng", ["Not Given"]))
        self.assertTrue(is_answer_correct("YNNG", "yes", ["Yes"]))
        self.assertTrue(is_answer_correct("YNNG", "y", ["Yes"]))
        self.assertFalse(is_answer_correct("TFNG", "False", ["True"]))

    def test_grading_short_text(self):
        accepted = ["an apple", "apple", "apples"]
        self.assertTrue(is_answer_correct("SHORT_TEXT", "apple", accepted))
        self.assertTrue(is_answer_correct("SHORT_TEXT", "An Apple.", accepted))
        self.assertFalse(is_answer_correct("SHORT_TEXT", "orange", accepted))

    def test_comma_separated_variants(self):
        accepted = ["90, 90%, ninety"]
        self.assertTrue(is_answer_correct("SHORT_TEXT", "90%", accepted))
        self.assertTrue(is_answer_correct("SHORT_TEXT", "ninety", accepted))
        self.assertTrue(is_answer_correct("SHORT_TEXT", "90", accepted))

    def test_ielts_band_calculation(self):
        # 40 cau Reading
        self.assertEqual(calculate_ielts_band(39, 40, "READING"), 9.0)
        self.assertEqual(calculate_ielts_band(30, 40, "READING"), 7.0)
        self.assertEqual(calculate_ielts_band(23, 40, "READING"), 6.0)
        # Bai duoi 40 cau khong tinh band
        self.assertIsNone(calculate_ielts_band(5, 5, "READING"))
        self.assertIsNone(calculate_ielts_band(3, 5, "LISTENING"))


class ReceptiveSubmissionTests(TestCase):
    def setUp(self):
        self.group, _ = Group.objects.get_or_create(name="HOC_VIEN")
        self.user = User.objects.create_user(username="test_student", password="password123")
        self.user.groups.add(self.group)

        self.exercise = Exercise.objects.create(
            title="Sample Test Exercise",
            skill=Exercise.Skill.READING,
            level=Exercise.Level.BEGINNER,
            passage="This is a test passage about reading comprehension.",
            status=Exercise.Status.PUBLISHED,
        )
        self.q1 = Question.objects.create(
            exercise=self.exercise,
            order_no=1,
            question_type=Question.Type.MCQ,
            question_text="What is this passage about?",
            correct_answers=["A"],
            status=Question.Status.PUBLISHED,
        )
        self.q2 = Question.objects.create(
            exercise=self.exercise,
            order_no=2,
            question_type=Question.Type.TFNG,
            question_text="Reading comprehension is tested.",
            correct_answers=["True"],
            status=Question.Status.PUBLISHED,
        )

    def test_successful_submission(self):
        answers = {str(self.q1.id): "A", str(self.q2.id): "True"}
        attempt, created = submit_receptive_exercise(
            user=self.user,
            exercise=self.exercise,
            answers_dict=answers,
            mode="PRACTICE",
            time_spent_seconds=120,
        )
        self.assertTrue(created)
        self.assertEqual(attempt.correct_answers, 2)
        self.assertEqual(attempt.total_questions, 2)
        self.assertEqual(attempt.time_spent_seconds, 120)

        # Kiem tra ExerciseProgress duoc cap nhat completed
        prog = ExerciseProgress.objects.get(user=self.user, exercise=self.exercise)
        self.assertTrue(prog.is_completed)
        self.assertEqual(prog.last_attempt, attempt)
