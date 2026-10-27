from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from faq.models import ErrorCode, FAQ
from core.quotes import get_motivation_quote, FALLBACK_QUOTES

class CoreViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
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

    def test_home_page_renders_with_quote_and_chat_widget(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PlanMyStudy')
        self.assertContains(response, 'chat-widget-container')
        self.assertContains(response, 'chat-toggle-btn')

    def test_study_tips_page(self):
        response = self.client.get(reverse('study_tips'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pomodoro')
        self.assertContains(response, 'Active Recall')
        self.assertContains(response, 'chat-widget-container')

    def test_contact_about_page(self):
        response = self.client.get(reverse('contact_about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open Support Chat Widget')
        self.assertContains(response, 'chat-widget-container')

    def test_health_check_html_and_json(self):
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Web Service')
        self.assertContains(response, 'PostgreSQL')

        # Test ?format=json
        json_resp = self.client.get(reverse('health_check') + '?format=json')
        self.assertEqual(json_resp.status_code, 200)
        data = json_resp.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('django', data['services'])
        self.assertIn('database_postgres', data['services'])
        self.assertIn('mongodb', data['services'])
        self.assertIn('quotes_api', data['services'])

    def test_quote_fallback(self):
        quote = get_motivation_quote()
        self.assertIn('quote', quote)
        self.assertIn('author', quote)
        self.assertTrue(len(quote['quote']) > 0)

    def test_debug_error_route(self):
        response = self.client.get('/debug/error/404/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Ask the Assistant', status_code=404)
        self.assertContains(response, 'chat-widget-container', status_code=404)

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
