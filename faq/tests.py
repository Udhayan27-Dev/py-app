from django.test import TestCase, Client
from django.urls import reverse
from faq.models import FAQ

class FAQTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.faq1 = FAQ.objects.create(
            question="How is the study plan calculated?",
            answer="Hard subjects receive 3x weight.",
            category="planning",
            is_active=True
        )
        self.faq2 = FAQ.objects.create(
            question="What is the Pomodoro technique?",
            answer="25 min study followed by 5 min break.",
            category="techniques",
            is_active=True
        )

    def test_faq_list_view_and_grouping(self):
        resp = self.client.get(reverse('faq'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Frequently Asked Questions')
        self.assertContains(resp, 'Hard subjects receive 3x weight.')
        self.assertContains(resp, '25 min study followed by 5 min break.')
        self.assertContains(resp, 'chat-widget-container')

    def test_faq_search_filter(self):
        resp = self.client.get(reverse('faq') + '?q=Pomodoro')
        self.assertEqual(resp.status_code, 200)
        # Pomodoro answer should be present
        self.assertContains(resp, '25 min study followed by 5 min break.')
        # Planning answer should not be in the search results
        self.assertNotContains(resp, 'Hard subjects receive 3x weight.')

    def test_faq_category_filter(self):
        resp = self.client.get(reverse('faq') + '?category=planning')
        self.assertEqual(resp.status_code, 200)
        # Planning answer should be present
        self.assertContains(resp, 'Hard subjects receive 3x weight.')
        # Techniques answer should not be present
        self.assertNotContains(resp, '25 min study followed by 5 min break.')
