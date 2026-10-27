import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from faq.models import FAQ, ErrorCode
from tickets.models import SupportTicket
from chat.mongo import _fallback_chat_logs, _fallback_feedback

class ChatAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.faq = FAQ.objects.create(
            question="What is the Pomodoro technique?",
            answer="25 minutes of deep focus followed by a 5-minute break.",
            category="techniques",
            is_active=True
        )
        self.error_code = ErrorCode.objects.create(
            code="SP-4221",
            title="Not enough days to build a study plan",
            explanation="The exam date is too close.",
            suggested_fix="Pick a date at least 3 days in the future."
        )

    def test_direct_error_code_query(self):
        resp = self.client.post(
            reverse('api_chat'),
            data=json.dumps({'message': 'Explain error SP-4221', 'session_id': 'test-session-1'}),
            content_type='application/json',
            REMOTE_ADDR='198.51.100.1'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['source'], 'error_code')
        self.assertIn('SP-4221', data['reply'])
        self.assertIn('Not enough days', data['reply'])

    def test_faq_fallback_matching(self):
        resp = self.client.post(
            reverse('api_chat'),
            data=json.dumps({'message': 'What is Pomodoro technique break?', 'session_id': 'test-session-2'}),
            content_type='application/json',
            REMOTE_ADDR='198.51.100.2'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['source'], 'faq')
        self.assertIn('25 minutes', data['reply'])

    def test_unknown_question_creates_support_ticket(self):
        initial_ticket_count = SupportTicket.objects.count()
        resp = self.client.post(
            reverse('api_chat'),
            data=json.dumps({'message': 'Can I export my plan directly to an obscure astrophysics calculator?', 'session_id': 'test-session-3'}),
            content_type='application/json',
            REMOTE_ADDR='198.51.100.3'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['source'], 'ticket_created')
        self.assertIn('Support Ticket', data['reply'])
        self.assertEqual(SupportTicket.objects.count(), initial_ticket_count + 1)

    def test_chat_rate_limiting_20_requests_per_minute(self):
        ip = '198.51.100.99'
        for i in range(20):
            res = self.client.post(
                reverse('api_chat'),
                data=json.dumps({'message': 'Hello test', 'session_id': 'test-sess-rl'}),
                content_type='application/json',
                REMOTE_ADDR=ip
            )
            self.assertEqual(res.status_code, 200)

        # 21st request triggers 429 JSON
        blocked_res = self.client.post(
            reverse('api_chat'),
            data=json.dumps({'message': 'Hello test', 'session_id': 'test-sess-rl'}),
            content_type='application/json',
            REMOTE_ADDR=ip
        )
        self.assertEqual(blocked_res.status_code, 429)
        self.assertEqual(blocked_res.json()['code'], 429)
        self.assertIn('Rate limit exceeded', blocked_res.json()['error'])

    def test_feedback_api(self):
        resp = self.client.post(
            reverse('api_feedback'),
            data=json.dumps({
                'session_id': 'test-session-fb',
                'message_id': 'msg-1234',
                'rating': 'thumbs_up',
                'comment': 'Very helpful!'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')

    def test_chat_message_length_limit(self):
        long_message = "A" * 1005
        resp = self.client.post(
            reverse('api_chat'),
            data=json.dumps({'message': long_message, 'session_id': 'test-session-len'}),
            content_type='application/json',
            REMOTE_ADDR='198.51.100.5'
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('exceeds the limit', resp.json()['error'])
