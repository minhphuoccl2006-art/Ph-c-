import uuid
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from listening.models import ListeningExercise
from receptive.models import Exercise, Question, Option, Attempt, ExerciseProgress


class ListeningFullWorkflowTests(TestCase):
    def setUp(self):
        self.group, _ = Group.objects.get_or_create(name="HOC_VIEN")
        self.student = User.objects.create_user(username="student_listening", password="password123")
        self.student.groups.add(self.group)

        self.other_student = User.objects.create_user(username="other_listening_student", password="password123")
        self.other_student.groups.add(self.group)

        self.exercise = ListeningExercise.objects.create(
            title="Listening Workflow Test",
            skill=Exercise.Skill.LISTENING,
            level=Exercise.Level.BEGINNER,
            topic="Campus Orientation",
            status=Exercise.Status.PUBLISHED,
            time_limit_minutes=20,
            transcript="Full narrator conversation transcript text.",
        )
        self.q1 = Question.objects.create(
            exercise=self.exercise,
            order_no=1,
            question_type=Question.Type.SHORT_TEXT,
            question_text="What time does the library open?",
            correct_answers=["6:00 AM", "6 AM", "6:00"],
            status=Question.Status.PUBLISHED,
        )

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(reverse("listening:exercise_list"))
        self.assertEqual(resp.status_code, 302)

    def test_student_can_view_list_and_detail(self):
        self.client.force_login(self.student)
        resp = self.client.get(reverse("listening:exercise_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Listening Workflow Test")

        detail_resp = self.client.get(reverse("listening:exercise_detail", kwargs={"pk": self.exercise.id}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "What time does the library open?")

    def test_listening_autosave_and_submit(self):
        self.client.force_login(self.student)

        # Autosave
        autosave_url = reverse("listening:exercise_autosave", kwargs={"pk": self.exercise.id})
        payload = {
            "answers": {str(self.q1.id): "6:00 AM"},
            "review_flags": [],
            "time_spent_seconds": 30,
        }
        res = self.client.post(autosave_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)

        # Submit
        submit_url = reverse("listening:exercise_submit", kwargs={"pk": self.exercise.id})
        sub_key = str(uuid.uuid4())
        submit_payload = {
            "answers": {str(self.q1.id): "6:00 AM"},
            "submission_key": sub_key,
            "mode": "PRACTICE",
            "time_spent_seconds": 30,
        }
        submit_res = self.client.post(submit_url, data=json.dumps(submit_payload), content_type="application/json")
        self.assertEqual(submit_res.status_code, 200)

        # Result page
        result_url = reverse("listening:attempt_result", kwargs={"submission_key": sub_key})
        result_resp = self.client.get(result_url)
        self.assertEqual(result_resp.status_code, 200)
        self.assertContains(result_resp, "1/1")
        # Transcript hiển thị sau khi nộp
        self.assertContains(result_resp, "Full narrator conversation transcript text.")

        # Học viên khác bị 403 Forbidden
        self.client.force_login(self.other_student)
        forbidden_resp = self.client.get(result_url)
        self.assertEqual(forbidden_resp.status_code, 403)
