from django.db import models
from django.conf import settings

class SupportTicket(models.Model):
    """
    Support ticket created either automatically by the AI Assistant when a query
    is outside the FAQ/error scope, or manually.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets'
    )
    user_email = models.EmailField(blank=True, null=True)
    question = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    chat_session_id = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'

    def __str__(self):
        return f"Ticket #{self.id} - {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
