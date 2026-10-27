from django.db import models

class FAQ(models.Model):
    """
    Frequently Asked Questions loaded into the system knowledge base.
    """
    CATEGORY_CHOICES = [
        ('planning', 'Study Planning & Timetable'),
        ('techniques', 'Study Techniques & Tips'),
        ('account', 'Account & Security'),
        ('general', 'General & Platform'),
    ]

    question = models.CharField(max_length=255, db_index=True)
    answer = models.TextField()
    category = models.CharField(max_length=100, default='General', choices=CATEGORY_CHOICES)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'id']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    """
    HTTP and application-specific error codes documented for users and AI assistant.
    """
    code = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    explanation = models.TextField()
    suggested_fix = models.TextField()

    class Meta:
        ordering = ['code']
        verbose_name = 'Error Code'
        verbose_name_plural = 'Error Codes'

    def __str__(self):
        return f"{self.code} - {self.title}"
