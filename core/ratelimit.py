import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')

def is_rate_limited(ip: str, action: str, max_requests: int, window_seconds: int = 60) -> bool:
    """
    Sliding window rate limiter using Django cache.
    Returns True if rate limit is exceeded, False otherwise.
    """
    now = time.time()
    cache_key = f"ratelimit:{action}:{ip}"
    history = cache.get(cache_key, [])
    # Keep only timestamps within the current window
    history = [t for t in history if now - t < window_seconds]

    if len(history) >= max_requests:
        return True

    history.append(now)
    cache.set(cache_key, history, timeout=window_seconds)
    return False

def ratelimit(action: str, max_requests: int, window_seconds: int = 60, response_type: str = 'html'):
    """
    Decorator for views to enforce rate limiting.
    response_type: 'json' returns JsonResponse 429, 'html' renders 429.html
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            ip = get_client_ip(request)
            if is_rate_limited(ip, action, max_requests, window_seconds):
                if response_type == 'json' or request.path.startswith('/api/'):
                    return JsonResponse({
                        'error': 'Too many requests. Please try again later.',
                        'code': 429
                    }, status=429)
                return render(request, 'errors/429.html', {
                    'error_code': '429',
                    'error_title': 'Too Many Requests',
                    'error_message': f'You have exceeded the maximum allowed requests ({max_requests} per minute). Please wait a moment and try again.'
                }, status=429)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
