from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from planner.models import StudyPlan
from planner.services import generate_timetable, PlanGenerationError
from faq.models import ErrorCode

class PlannerTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='alice', password='Password123#')
        self.user2 = User.objects.create_user(username='bob', password='Password123#')
        ErrorCode.objects.create(
            code="SP-4221",
            title="Not enough days to build a study plan",
            explanation="Exam date too close.",
            suggested_fix="Pick date 3+ days in future."
        )

    def test_generator_algorithm_success(self):
        today = date.today()
        exam_date = today + timedelta(days=10) # 10 days total = 8 study days + 2 revision days
        subjects = [
            {'name': 'Math', 'difficulty': 'hard'},
            {'name': 'History', 'difficulty': 'easy'},
            {'name': 'Chemistry', 'difficulty': 'medium'}
        ]
        result = generate_timetable(subjects, exam_date, hours_per_day=4, start_date=today)

        self.assertEqual(result['summary']['total_days'], 10)
        self.assertEqual(result['summary']['study_days'], 8)
        self.assertEqual(result['summary']['revision_days'], 2)
        # Total study hours: 8 * 4 = 32
        allocations = result['summary']['subject_allocations']
        # Hard (Math) should have more hours than Easy (History)
        self.assertGreater(allocations['Math'], allocations['History'])
        self.assertGreater(allocations['Chemistry'], allocations['History'])

        # Check that last 2 days are revision days
        days = result['days']
        self.assertEqual(len(days), 10)
        self.assertTrue(days[-1]['is_revision'])
        self.assertTrue(days[-2]['is_revision'])
        self.assertFalse(days[0]['is_revision'])

    def test_sp_4221_when_exam_date_in_past_or_too_close(self):
        today = date.today()
        # Exam tomorrow: only 1 day available
        tomorrow = today + timedelta(days=1)
        subjects = [{'name': 'Math', 'difficulty': 'hard'}]

        with self.assertRaises(PlanGenerationError) as ctx:
            generate_timetable(subjects, tomorrow, hours_per_day=4, start_date=today)
        self.assertEqual(ctx.exception.code, "SP-4221")

        # Test via POST to form
        resp = self.client.post(reverse('plan_generator'), {
            'exam_date': tomorrow.isoformat(),
            'hours_per_day': '4',
            'subject_name[]': ['Math'],
            'subject_difficulty[]': ['hard']
        })
        self.assertEqual(resp.status_code, 422)
        self.assertContains(resp, 'SP-4221', status_code=422)
        self.assertContains(resp, 'Ask the Assistant', status_code=422)

    def test_my_plans_requires_login(self):
        resp = self.client.get(reverse('my_plans'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_ownership_security_on_plan_detail(self):
        today = date.today()
        exam_date = today + timedelta(days=7)
        plan = StudyPlan.objects.create(
            user=self.user1,
            subjects=[{'name': 'Math', 'difficulty': 'hard'}],
            exam_date=exam_date,
            hours_per_day=4,
            generated_plan={'days': []}
        )

        # Owner Alice can view it
        self.client.login(username='alice', password='Password123#')
        resp = self.client.get(reverse('plan_detail', args=[plan.id]))
        self.assertEqual(resp.status_code, 200)

        # Bob cannot view Alice's plan -> custom 403 page
        self.client.login(username='bob', password='Password123#')
        forbidden_resp = self.client.get(reverse('plan_detail', args=[plan.id]))
        self.assertEqual(forbidden_resp.status_code, 403)
        self.assertContains(forbidden_resp, 'Forbidden', status_code=403)
        self.assertContains(forbidden_resp, 'Ask the Assistant', status_code=403)

    def test_ownership_security_on_plan_delete(self):
        plan = StudyPlan.objects.create(
            user=self.user1,
            subjects=[{'name': 'Math', 'difficulty': 'hard'}],
            exam_date=date.today() + timedelta(days=7),
            hours_per_day=4,
            generated_plan={'days': []}
        )

        # Bob tries to delete Alice's plan -> 403
        self.client.login(username='bob', password='Password123#')
        resp = self.client.post(reverse('delete_plan', args=[plan.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(StudyPlan.objects.filter(id=plan.id).exists())

        # Alice deletes own plan -> 302 to my_plans
        self.client.login(username='alice', password='Password123#')
        del_resp = self.client.post(reverse('delete_plan', args=[plan.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(StudyPlan.objects.filter(id=plan.id).exists())
