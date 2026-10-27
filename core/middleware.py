import time
import logging
from datetime import datetime, timezone
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger('request_logger')

class RequestLoggingMiddleware:
    """
    Middleware that logs every incoming HTTP request:
    method, path, status code, duration in ms, IP address, and timestamp.
    Outputs to console and rotating log file.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine client IP (considering reverse proxies like Render / Cloudflare)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')

        log_message = (
            f"[{timestamp}] IP={ip} "
            f"METHOD={request.method} PATH={request.get_full_path()} "
            f"STATUS={response.status_code} DURATION={duration_ms:.2f}ms"
        )
        logger.info(log_message)

        return response


class EnforceLoginMiddleware:
    """
    Middleware that ensures users must be logged in before using the application.
    Unauthenticated users are redirected to /login/?next=...
    Unauthenticated requests to /api/ routes receive an HTTP 401 JSON error.
    Public routes: /login/, /register/, /health/, /admin/, /static/
    """
    EXEMPT_PREFIXES = (
        '/login/',
        '/register/',
        '/health/',
        '/admin/',
        '/static/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Allow access if user is authenticated or path is exempt
        if not request.user.is_authenticated:
            is_exempt = any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES)
            if not is_exempt:
                if path.startswith('/api/'):
                    return JsonResponse({
                        'error': 'Authentication required. Please log in to use the assistant and APIs.',
                        'code': 401
                    }, status=401)

                login_url = getattr(settings, 'LOGIN_URL', '/login/')
                return redirect(f"{login_url}?next={request.get_full_path()}")

        return self.get_response(request)
