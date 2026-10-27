from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from tickets.models import SupportTicket

class TicketsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.regular_user = User.objects.create_user(username='regular', password='Password123#')
        self.staff_user = User.objects.create_user(username='staffmember', password='Password123#', is_staff=True)
        self.ticket = SupportTicket.objects.create(
            user=self.regular_user,
            question="How do I change my exam date?",
            status="open"
        )

    def test_staff_dashboard_forbidden_for_anonymous_and_regular_users(self):
        # Anonymous user -> 403
        resp = self.client.get(reverse('staff_tickets'))
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, 'Forbidden', status_code=403)

        # Regular user -> 403
        self.client.login(username='regular', password='Password123#')
        resp2 = self.client.get(reverse('staff_tickets'))
        self.assertEqual(resp2.status_code, 403)
        self.assertContains(resp2, 'Forbidden', status_code=403)

    def test_staff_dashboard_accessible_by_staff_user(self):
        self.client.login(username='staffmember', password='Password123#')
        resp = self.client.get(reverse('staff_tickets'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Support Tickets Dashboard')
        self.assertContains(resp, self.ticket.question)

    def test_staff_can_update_ticket_status(self):
        self.client.login(username='staffmember', password='Password123#')
        resp = self.client.post(reverse('update_ticket_status', args=[self.ticket.id]), {
            'status': 'in_progress'
        })
        self.assertEqual(resp.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'in_progress')
