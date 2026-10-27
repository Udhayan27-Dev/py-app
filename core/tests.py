from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from faq.models import ErrorCode, FAQ
from core.quotes import get_motivation_quote, FALLBACK_QUOTES

class CoreViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='Password123#')
        ErrorCode.objects.create(
            code="404",
            title="Page Not Found",
            explanation="Resource missing.",
            suggested_fix="Check URL."
        )
        ErrorCode.objects.create(
            code="429",
            title="Too Many Requests",
            explanation="Rate limit exceeded.",
            suggested_fix="Wait 60s."
        )

    def test_unauthenticated_user_redirected_to_login(self):
        # Unauthenticated users cannot access app pages
        for path in ['/', '/tips/', '/about/', '/generate/']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    def test_health_check_remains_public(self):
        # Health check is public for load balancers
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)

        json_resp = self.client.get(reverse('health_check') + '?format=json')
        self.assertEqual(json_resp.status_code, 200)
        data = json_resp.json()
        self.assertEqual(data['status'], 'healthy')

    def test_authenticated_user_can_access_pages(self):
        self.client.force_login(self.user)
        # Home
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PlanMyStudy')
        self.assertContains(response, 'chat-widget-container')

        # Tips
        response = self.client.get(reverse('study_tips'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pomodoro')

        # About
        response = self.client.get(reverse('contact_about'))
        self.assertEqual(response.status_code, 200)

    def test_quote_fallback(self):
        quote = get_motivation_quote()
        self.assertIn('quote', quote)
        self.assertIn('author', quote)
        self.assertTrue(len(quote['quote']) > 0)

    def test_debug_error_route_when_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get('/debug/error/404/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Ask the Assistant', status_code=404)

    def test_login_rate_limiting(self):
        # 5 attempts allowed, 6th must return 429
        for i in range(5):
            res = self.client.post(reverse('login'), {
                'username': 'fakeuser',
                'password': 'badpassword'
            }, REMOTE_ADDR='198.51.100.55')
            self.assertEqual(res.status_code, 200)

        # 6th attempt from same IP triggers 429
        blocked_res = self.client.post(reverse('login'), {
            'username': 'fakeuser',
            'password': 'badpassword'
        }, REMOTE_ADDR='198.51.100.55')
        self.assertEqual(blocked_res.status_code, 429)
        self.assertContains(blocked_res, 'Too Many', status_code=429)
        self.assertContains(blocked_res, 'Ask the Assistant', status_code=429)
