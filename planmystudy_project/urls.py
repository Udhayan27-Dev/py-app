from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

import core.views as core_views
import planner.views as planner_views
import faq.views as faq_views
import tickets.views as tickets_views
import chat.views as chat_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Core Pages
    path('', core_views.home_view, name='home'),
    path('tips/', core_views.study_tips_view, name='study_tips'),
    path('about/', core_views.contact_about_view, name='contact_about'),
    path('health/', core_views.health_check_view, name='health_check'),

    # Study Planner Pages
    path('generate/', planner_views.plan_generator_view, name='plan_generator'),
    path('my-plans/', planner_views.my_plans_view, name='my_plans'),
    path('plans/<int:pk>/', planner_views.plan_detail_view, name='plan_detail'),
    path('plans/<int:pk>/delete/', planner_views.delete_plan_view, name='delete_plan'),

    # FAQ Page
    path('faq/', faq_views.faq_view, name='faq'),

    # Staff Dashboard
    path('staff/tickets/', tickets_views.staff_tickets_dashboard, name='staff_tickets'),
    path('staff/tickets/<int:pk>/update/', tickets_views.update_ticket_status, name='update_ticket_status'),

    # Authentication
    path('register/', core_views.register_view, name='register'),
    path('login/', core_views.login_view, name='login'),
    path('logout/', core_views.logout_view, name='logout'),

    # AI Support Assistant API Endpoints
    path('api/chat/', chat_views.chat_api_view, name='api_chat'),
    path('api/feedback/', chat_views.feedback_api_view, name='api_feedback'),

    # Debug Error Demonstration Route
    path('debug/error/<str:code>/', core_views.debug_error_view, name='debug_error'),
]

# Custom Error Handlers
handler400 = 'core.views.custom_400_view'
handler403 = 'core.views.custom_403_view'
handler404 = 'core.views.custom_404_view'
handler500 = 'core.views.custom_500_view'

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
