from django.db import models
from django.conf import settings

class StudyPlan(models.Model):
    """
    Generated day-by-day study timetable.
    Can belong to an authenticated user or a guest session.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='study_plans'
    )
    subjects = models.JSONField(default=list)
    exam_date = models.DateField()
    hours_per_day = models.PositiveIntegerField(default=4)
    generated_plan = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Study Plan'
        verbose_name_plural = 'Study Plans'

    def __str__(self):
        owner = self.user.username if self.user else f"Guest ({self.session_id[:8]}...)"
        return f"Study Plan for {self.exam_date} by {owner} ({len(self.subjects)} subjects)"
