import uuid
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from reading.models import ReadingExercise
from receptive.models import Exercise, Question, Option, Attempt, ExerciseProgress


class ReadingFullWorkflowTests(TestCase):
    def setUp(self):
        self.group, _ = Group.objects.get_or_create(name="HOC_VIEN")
        self.student = User.objects.create_user(username="student_reading", password="password123")
        self.student.groups.add(self.group)

        self.other_student = User.objects.create_user(username="other_student", password="password123")
        self.other_student.groups.add(self.group)

        self.exercise = ReadingExercise.objects.create(
            title="Reading Workflow Test",
            skill=Exercise.Skill.READING,
            level=Exercise.Level.INTERMEDIATE,
            topic="Cognitive Science",
            passage="Passage content for testing workflow.",
            status=Exercise.Status.PUBLISHED,
            time_limit_minutes=20,
        )
        self.q1 = Question.objects.create(
            exercise=self.exercise,
            order_no=1,
            question_type=Question.Type.MCQ,
            question_text="Sample MCQ question?",
            correct_answers=["B"],
            status=Question.Status.PUBLISHED,
        )
        Option.objects.create(question=self.q1, option_key="A", option_text="Option A", order_no=1)
        Option.objects.create(question=self.q1, option_key="B", option_text="Option B", order_no=2)

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(reverse("reading:exercise_list"))
        self.assertEqual(resp.status_code, 302)

    def test_student_can_view_list_and_filter(self):
        self.client.force_login(self.student)
        resp = self.client.get(reverse("reading:exercise_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reading Workflow Test")

        # Test filter level
        resp_filter = self.client.get(reverse("reading:exercise_list") + "?level=INTERMEDIATE")
        self.assertEqual(resp_filter.status_code, 200)
        self.assertContains(resp_filter, "Reading Workflow Test")

        # Test filter mismatch
        resp_mismatch = self.client.get(reverse("reading:exercise_list") + "?level=BEGINNER")
        self.assertEqual(resp_mismatch.status_code, 200)
        self.assertNotContains(resp_mismatch, "Reading Workflow Test")

    def test_student_can_view_detail(self):
        self.client.force_login(self.student)
        resp = self.client.get(reverse("reading:exercise_detail", kwargs={"pk": self.exercise.id}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reading Passage")
        self.assertContains(resp, "Sample MCQ question?")
        # Dap an dung khong duoc lo trong HTML truoc khi nop
        self.assertNotContains(resp, '"correct_answers"')

    def test_autosave_ajax_endpoint(self):
        self.client.force_login(self.student)
        autosave_url = reverse("reading:exercise_autosave", kwargs={"pk": self.exercise.id})
        payload = {
            "answers": {str(self.q1.id): "B"},
            "review_flags": [str(self.q1.id)],
            "highlights": [{"id": "hl_1", "text": "Passage content", "note": "Test note"}],
            "font_size": 18,
            "time_spent_seconds": 45,
            "time_left_seconds": 1155,
        }
        resp = self.client.post(autosave_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["answered_count"], 1)

        # Kiem tra trong DB
        prog = ExerciseProgress.objects.get(user=self.student, exercise=self.exercise)
        self.assertEqual(prog.answers.get(str(self.q1.id)), "B")
        self.assertEqual(prog.font_size, 18)
        self.assertEqual(prog.time_spent_seconds, 45)

    def test_submission_and_attempt_result(self):
        self.client.force_login(self.student)
        submit_url = reverse("reading:exercise_submit", kwargs={"pk": self.exercise.id})
        sub_key = str(uuid.uuid4())
        payload = {
            "answers": {str(self.q1.id): "B"},
            "submission_key": sub_key,
            "mode": "EXAM",
            "time_spent_seconds": 60,
        }
        resp = self.client.post(submit_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])

        # Kiem tra Attempt da tao
        attempt = Attempt.objects.get(submission_key=sub_key)
        self.assertEqual(attempt.correct_answers, 1)
        self.assertEqual(attempt.mode, "EXAM")

        # Xem ket qua boi chinh hoc vien
        result_url = reverse("reading:attempt_result", kwargs={"submission_key": sub_key})
        result_resp = self.client.get(result_url)
        self.assertEqual(result_resp.status_code, 200)
        self.assertContains(result_resp, "1/1")

        # Hoc vien khac truy cap attempt nay se bi 403 Forbidden
        self.client.force_login(self.other_student)
        forbidden_resp = self.client.get(result_url)
        self.assertEqual(forbidden_resp.status_code, 403)
