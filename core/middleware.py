import time
import logging
from datetime import datetime, timezone

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
