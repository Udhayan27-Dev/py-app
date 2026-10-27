from django.contrib import admin
from .models import StudyPlan

@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'exam_date', 'hours_per_day', 'created_at', 'session_id')
    list_filter = ('exam_date', 'created_at')
    search_fields = ('user__username', 'session_id')
