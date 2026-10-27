import time
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.db import connection
from django.conf import settings

from .quotes import get_motivation_quote
from .ratelimit import is_rate_limited, get_client_ip
from chat.mongo import check_mongo_connection
from faq.models import ErrorCode
from planner.models import StudyPlan

def home_view(request):
    """
    1. Home: hero section, how-it-works steps, motivation-of-the-day banner
    """
    quote = get_motivation_quote()
    return render(request, 'core/home.html', {
        'quote': quote
    })


def study_tips_view(request):
    """
    3. Study Tips: 6+ static tip cards (Pomodoro, active recall, spaced repetition, etc.)
    """
    tips = [
        {
            'name': 'The Pomodoro Technique',
            'icon': '⏱️',
            'tag': 'Time Management',
            'summary': 'Structure your study time into focused 25-minute intervals separated by short 5-minute pauses.',
            'steps': [
                'Choose a single high-priority study topic.',
                'Set a timer for 25 minutes and work with zero distractions.',
                'When the timer rings, take a 5-minute physical break (stretch, drink water).',
                'After 4 pomodoros, take a longer restorative 15-30 minute break.'
            ],
            'why_it_works': 'Prevents cognitive fatigue and trains sustained mental discipline without feeling overwhelmed.'
        },
        {
            'name': 'Active Recall',
            'icon': '🧠',
            'tag': 'Retention',
            'summary': 'Test your memory proactively instead of rereading or passively highlighting textbook notes.',
            'steps': [
                'Close your textbook or notes after reading a chapter.',
                'Write down or explain aloud everything you can remember.',
                'Check back against your notes to identify knowledge gaps.',
                'Focus your next review session specifically on what you forgot.'
            ],
            'why_it_works': 'Forces your brain to retrieve information, strengthening neural pathways and long-term memory.'
        },
        {
            'name': 'Spaced Repetition',
            'icon': '📅',
            'tag': 'Long-term Memory',
            'summary': 'Review concepts at systematically increasing time intervals right as you are about to forget them.',
            'steps': [
                'Learn initial material on Day 1.',
                'Review core definitions on Day 2.',
                'Conduct self-testing on Day 5 and Day 12.',
                'Perform a quick refresher right before exam week.'
            ],
            'why_it_works': 'Flattens the Ebbinghaus forgetting curve, converting short-term memory into permanent storage.'
        },
        {
            'name': 'The Feynman Technique',
            'icon': '💡',
            'tag': 'Deep Understanding',
            'summary': 'Explain complex concepts in simple, jargon-free words as if teaching a 10-year-old child.',
            'steps': [
                'Write the title of the concept at the top of a blank sheet.',
                'Explain the concept in simple, conversational language.',
                'Whenever you get stuck or use complex jargon, return to your reference material.',
                'Simplify and create intuitive real-world analogies.'
            ],
            'why_it_works': 'Reveals illusions of competence and exposes precisely where your understanding is weak.'
        },
        {
            'name': 'Interleaved Practice',
            'icon': '🔀',
            'tag': 'Problem Solving',
            'summary': 'Mix up different subjects and problem types during a single study session rather than block practicing one topic.',
            'steps': [
                'Instead of doing 30 algebra questions in a row, rotate between algebra, geometry, and word problems.',
                'Switch subjects or topics every 45-60 minutes.',
                'Practice categorizing which formula or strategy applies before solving.'
            ],
            'why_it_works': 'Develops cognitive flexibility and helps your brain learn to select the right approach under exam conditions.'
        },
        {
            'name': 'Sleep & Memory Consolidation',
            'icon': '🌙',
            'tag': 'Neuroscience',
            'summary': 'Sleep is not downtime—it is when your brain physically solidifies and reorganizes the day\'s study material.',
            'steps': [
                'Maintain a consistent 7-9 hour sleep schedule leading up to exams.',
                'Avoid all-nighters before tests; sleep deprivation drastically impairs recall.',
                'Review key formulas or difficult flashcards 20 minutes before sleeping.'
            ],
            'why_it_works': 'During slow-wave and REM sleep, memories are replayed and transferred from the hippocampus to the neocortex.'
        }
    ]

    return render(request, 'core/study_tips.html', {
        'tips': tips
    })


def contact_about_view(request):
    """
    5. Contact/About: short info plus a link to open the chat widget
    """
    return render(request, 'core/contact_about.html')


def health_check_view(request):
    """
    6. /health/ page
    Reports Django, Postgres, MongoDB, and the quotes API status.
    Returns 200 if core services are OK and 503 if not.
    HTML table plus ?format=json.
    """
    # 1. Django Status
    django_ok = True
    django_msg = f"Operational (Django {settings.VERSION if hasattr(settings, 'VERSION') else '5.1+'})"

    # 2. Postgres Status
    postgres_ok = False
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            if row and row[0] == 1:
                postgres_ok = True
                db_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]
                postgres_msg = f"Operational (connected via {db_engine})"
            else:
                postgres_msg = "Database query returned unexpected result"
    except Exception as e:
        postgres_msg = f"Database error: {str(e)}"

    # 3. MongoDB Status
    mongo_ok, mongo_msg = check_mongo_connection()

    # 4. Quotes API Status
    quotes_ok = False
    try:
        res = requests.get("https://zenquotes.io/api/today", timeout=3)
        if res.status_code == 200:
            quotes_ok = True
            quotes_msg = "Operational (ZenQuotes API reachable)"
        else:
            quotes_msg = f"HTTP {res.status_code} from ZenQuotes (fallback active)"
    except Exception as e:
        quotes_msg = f"ZenQuotes timeout/unreachable: {str(e)[:50]} (fallback active)"

    # Core services are Django and Postgres
    all_core_ok = django_ok and postgres_ok
    status_code = 200 if all_core_ok else 503

    health_data = {
        'status': 'healthy' if all_core_ok else 'degraded',
        'overall_code': status_code,
        'services': {
            'django': {'ok': django_ok, 'message': django_msg, 'core': True},
            'database_postgres': {'ok': postgres_ok, 'message': postgres_msg, 'core': True},
            'mongodb': {'ok': mongo_ok, 'message': mongo_msg, 'core': False},
            'quotes_api': {'ok': quotes_ok, 'message': quotes_msg, 'core': False},
        }
    }

    # Format check: ?format=json or Accept: application/json
    if request.GET.get('format') == 'json' or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
        return JsonResponse(health_data, status=status_code)

    return render(request, 'core/health.html', {
        'health_data': health_data,
        'all_core_ok': all_core_ok,
    }, status=status_code)


def register_view(request):
    """
    User registration using Django's built-in auth and default password validators.
    """
    if request.user.is_authenticated:
        return redirect('my_plans')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # If email was provided in POST
            email = request.POST.get('email', '').strip()
            if email:
                user.email = email
                user.save()

            login(request, user)

            # Associate any guest study plans from current session to this user
            if request.session.session_key:
                StudyPlan.objects.filter(
                    session_id=request.session.session_key,
                    user__isnull=True
                ).update(user=user)

            messages.success(request, f"Welcome to PlanMyStudy, {user.username}! Your account has been created.")
            return redirect('my_plans')
    else:
        form = UserCreationForm()

    return render(request, 'core/register.html', {
        'form': form
    })


def login_view(request):
    """
    User login with Rate Limiting: 5 attempts per minute per IP.
    Returns 429 with custom error page if rate limit is exceeded.
    """
    if request.user.is_authenticated:
        return redirect('my_plans')

    client_ip = get_client_ip(request)

    if request.method == 'POST':
        # Rate limit check: 5 attempts per minute per IP
        if is_rate_limited(client_ip, "user_login", max_requests=5, window_seconds=60):
            err = ErrorCode.objects.filter(code='429').first()
            return render(request, 'errors/429.html', {
                'error_code': '429',
                'error_title': 'Too Many Login Attempts',
                'error_message': 'You have exceeded the rate limit of 5 login attempts per minute. For security reasons, please wait 60 seconds before trying again.',
                'suggested_fix': err.suggested_fix if err else 'Wait 60 seconds before trying again.'
            }, status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Associate guest session plans
            if request.session.session_key:
                StudyPlan.objects.filter(
                    session_id=request.session.session_key,
                    user__isnull=True
                ).update(user=user)

            next_url = request.GET.get('next') or request.POST.get('next') or 'my_plans'
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {
        'form': form,
        'next': request.GET.get('next', '')
    })


def logout_view(request):
    """
    User logout. Supports POST and GET.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


def debug_error_view(request, code):
    """
    Demonstration error trigger route: /debug/error/<code>/
    Enabled only when DEBUG_ROUTES=True.
    Triggers 400, 401, 403, 404, 429, 500, 503, SP-4221.
    """
    if not getattr(settings, 'DEBUG_ROUTES', False):
        return render(request, 'errors/404.html', {
            'error_code': '404',
            'error_title': 'Page Not Found',
            'error_message': 'Debug error routes are disabled in this environment.'
        }, status=404)

    err = ErrorCode.objects.filter(code=code).first()
    title = err.title if err else f"Error {code}"
    explanation = err.explanation if err else "Demonstration error triggered."
    suggested_fix = err.suggested_fix if err else "Check route parameters."

    code_int = 400
    if code == '400':
        code_int = 400
    elif code == '401':
        code_int = 401
    elif code == '403':
        code_int = 403
    elif code == '404':
        code_int = 404
    elif code == '429':
        code_int = 429
    elif code == '500':
        code_int = 500
    elif code == '503':
        code_int = 503
    elif code == 'SP-4221':
        code_int = 422
    else:
        code_int = 400

    template_name = 'errors/error_page.html'
    if code in ('403', '404', '429', '500'):
        template_name = f'errors/{code}.html'

    return render(request, template_name, {
        'error_code': code,
        'error_title': title,
        'error_message': explanation,
        'suggested_fix': suggested_fix,
        'is_debug_demo': True
    }, status=code_int)


# Custom error handlers for Django
def custom_400_view(request, exception=None):
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Bad Request', 'code': 400}, status=400)
    err = ErrorCode.objects.filter(code='400').first()
    return render(request, 'errors/error_page.html', {
        'error_code': '400',
        'error_title': err.title if err else 'Bad Request',
        'error_message': err.explanation if err else 'The server cannot process the request due to invalid syntax.',
        'suggested_fix': err.suggested_fix if err else 'Verify your input and try again.'
    }, status=400)

def custom_403_view(request, exception=None):
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Forbidden - Permission Denied', 'code': 403}, status=403)
    err = ErrorCode.objects.filter(code='403').first()
    return render(request, 'errors/403.html', {
        'error_code': '403',
        'error_title': err.title if err else 'Access Forbidden',
        'error_message': err.explanation if err else 'You do not have permission to view or modify this resource.',
        'suggested_fix': err.suggested_fix if err else 'Log in with an authorized account or contact an administrator.'
    }, status=403)

def custom_404_view(request, exception=None):
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Resource Not Found', 'code': 404}, status=404)
    err = ErrorCode.objects.filter(code='404').first()
    return render(request, 'errors/404.html', {
        'error_code': '404',
        'error_title': err.title if err else 'Page Not Found',
        'error_message': err.explanation if err else 'The page or resource you requested could not be found.',
        'suggested_fix': err.suggested_fix if err else 'Check the URL or return to the homepage.'
    }, status=404)

def custom_500_view(request):
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Internal Server Error', 'code': 500}, status=500)
    try:
        err = ErrorCode.objects.filter(code='500').first()
        explanation = err.explanation if err else 'An unexpected internal error occurred on our server.'
        suggested_fix = err.suggested_fix if err else 'Please try again in a few moments.'
    except Exception:
        explanation = 'An unexpected internal error occurred on our server.'
        suggested_fix = 'Please try again in a few moments.'
    return render(request, 'errors/500.html', {
        'error_code': '500',
        'error_title': 'Internal Server Error',
        'error_message': explanation,
        'suggested_fix': suggested_fix
    }, status=500)
