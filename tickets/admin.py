from django.contrib import admin
from .models import SupportTicket

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'user', 'user_email', 'short_question', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('question', 'user_email', 'chat_session_id', 'user__username')
    list_editable = ('status',)

    def short_question(self, obj):
        return obj.question[:60] + ('...' if len(obj.question) > 60 else '')
    short_question.short_description = 'Question'
