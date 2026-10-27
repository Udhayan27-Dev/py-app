import json
import time
import re
import uuid
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from faq.models import FAQ, ErrorCode
from tickets.models import SupportTicket
from core.ratelimit import get_client_ip, is_rate_limited
from chat.mongo import log_chat_message, save_feedback

logger = logging.getLogger(__name__)

def perform_keyword_match(user_message, faqs, error_codes):
    """
    Fallback keyword matcher when LLM call fails, times out, or API key is not configured.
    Checks ErrorCodes first, then FAQs. Returns (reply_text, source) or (None, None).
    """
    clean_msg = user_message.lower().strip()

    # 1. Check ErrorCodes
    for ec in error_codes:
        code_str = ec.code.lower()
        if code_str in clean_msg or f"error {code_str}" in clean_msg:
            reply = (
                f"**Error {ec.code}: {ec.title}**\n\n"
                f"{ec.explanation}\n\n"
                f"**Suggested Fix:** {ec.suggested_fix}"
            )
            return reply, "error_code"

    # 2. Check FAQs
    # Tokenize user message
    tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', clean_msg))
    best_faq = None
    best_score = 0

    for faq in faqs:
        faq_q_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', faq.question.lower()))
        faq_a_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', faq.answer.lower()))
        
        # Give higher weight to matches in question
        score = len(tokens & faq_q_tokens) * 3 + len(tokens & faq_a_tokens)
        if score > best_score:
            best_score = score
            best_faq = faq

    # Require minimum score of 3 for a confident match
    if best_faq and best_score >= 3:
        reply = f"**{best_faq.question}**\n\n{best_faq.answer}"
        return reply, "faq"

    return None, None


@require_POST
def chat_api_view(request):
    """
    POST /api/chat/
    Integrated AI support assistant answering FAQs and Error Codes.
    Rate limited to 20 requests/minute per IP.
    """
    start_time = time.perf_counter()
    client_ip = get_client_ip(request)

    # 1. Rate Limiting: 20 requests per minute per IP
    if is_rate_limited(client_ip, "chat_api", max_requests=20, window_seconds=60):
        return JsonResponse({
            'error': 'Rate limit exceeded. Maximum 20 requests per minute.',
            'code': 429
        }, status=429)

    # 2. Parse request JSON
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.', 'code': 400}, status=400)

    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', '').strip()
    if not session_id:
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key or str(uuid.uuid4())

    # Input validation and length check
    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.', 'code': 400}, status=400)

    if len(user_message) > 1000:
        return JsonResponse({
            'error': 'Message length exceeds the limit of 1000 characters.',
            'code': 400
        }, status=400)

    user_id = request.user.id if request.user.is_authenticated else None

    # 3. Fetch active FAQs and ErrorCodes from Postgres
    faqs = list(FAQ.objects.filter(is_active=True))
    error_codes = list(ErrorCode.objects.all())

    # Check for direct error code matches first
    lower_msg = user_message.lower().strip()
    direct_error = None
    for ec in error_codes:
        if ec.code.lower() == lower_msg or f"error {ec.code.lower()}" == lower_msg or f"explain {ec.code.lower()}" in lower_msg:
            direct_error = ec
            break

    if direct_error:
        reply_text = (
            f"**Error {direct_error.code}: {direct_error.title}**\n\n"
            f"{direct_error.explanation}\n\n"
            f"**Suggested Fix:** {direct_error.suggested_fix}"
        )
        source = 'error_code'
        message_id = str(uuid.uuid4())
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_chat_message(session_id, user_message, reply_text, source, duration_ms, user_id)
        return JsonResponse({
            'message_id': message_id,
            'reply': reply_text,
            'source': source,
            'session_id': session_id,
            'duration_ms': round(duration_ms, 2)
        })

    # Prepare LLM Knowledge Base
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '').strip()
    assistant_reply = None
    source = 'llm'

    if api_key and api_key != 'your-anthropic-api-key-here':
        # Build Knowledge base text
        faq_context_lines = []
        for f in faqs:
            faq_context_lines.append(f"Q: {f.question}\nA: {f.answer}")
        faq_text = "\n\n".join(faq_context_lines)

        error_context_lines = []
        for e in error_codes:
            error_context_lines.append(f"Code: {e.code}\nTitle: {e.title}\nExplanation: {e.explanation}\nSuggested Fix: {e.suggested_fix}")
        error_text = "\n\n".join(error_context_lines)

        system_prompt = (
            "You are the PlanMyStudy AI Support Assistant. "
            "You help students with questions about study planning, timetables, study techniques, "
            "account security, and website error codes.\n\n"
            "STRICT RULES:\n"
            "1. You MUST use ONLY the knowledge provided below in the KNOWLEDGE BASE.\n"
            "2. If the user asks about an error code or HTTP status, explain it clearly using the Error Codes data.\n"
            "3. If the user's question CANNOT be answered from the provided FAQs or Error Codes, "
            "you MUST output EXACTLY: [CANNOT_ANSWER]\n"
            "Do NOT invent or guess any facts outside the knowledge base.\n"
            "4. Be friendly, encouraging, and clear.\n\n"
            "=== KNOWLEDGE BASE ===\n"
            "--- FAQS ---\n"
            f"{faq_text}\n\n"
            "--- ERROR CODES ---\n"
            f"{error_text}\n"
            "=== END KNOWLEDGE BASE ==="
        )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=10.0)
            llm_response = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=600,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            raw_text = llm_response.content[0].text.strip()
            if "[CANNOT_ANSWER]" in raw_text or "cannot answer" in raw_text.lower():
                assistant_reply = None  # Will trigger ticket creation
            else:
                assistant_reply = raw_text
                source = 'llm'
        except Exception as e:
            logger.warning(f"Anthropic API call failed or timed out: {e}. Falling back to keyword search.")
            assistant_reply = None

    # Fallback to keyword matching if LLM was unavailable, timed out, or not configured
    if assistant_reply is None and (not api_key or api_key == 'your-anthropic-api-key-here' or True):
        matched_reply, matched_source = perform_keyword_match(user_message, faqs, error_codes)
        if matched_reply:
            assistant_reply = matched_reply
            source = matched_source

    # If still no answer found, automatically create a SupportTicket in Postgres
    if assistant_reply is None:
        user_email = request.user.email if (request.user.is_authenticated and request.user.email) else None
        ticket = SupportTicket.objects.create(
            user=request.user if request.user.is_authenticated else None,
            user_email=user_email,
            question=user_message,
            status='open',
            chat_session_id=session_id
        )
        assistant_reply = (
            f"I'm sorry, I couldn't find an answer to your question in our knowledge base or error documentation. "
            f"I have automatically created Support Ticket **#{ticket.id}** for you! "
            f"Our support team has been alerted and will investigate."
        )
        source = 'ticket_created'

    message_id = str(uuid.uuid4())
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Log exchange to MongoDB chat_logs
    log_chat_message(
        session_id=session_id,
        user_message=user_message,
        assistant_reply=assistant_reply,
        source=source,
        response_time_ms=duration_ms,
        user_id=user_id
    )

    return JsonResponse({
        'message_id': message_id,
        'reply': assistant_reply,
        'source': source,
        'session_id': session_id,
        'duration_ms': round(duration_ms, 2)
    })


@require_POST
def feedback_api_view(request):
    """
    POST /api/feedback/
    Saves thumbs up/down rating and comment to MongoDB feedback collection.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.', 'code': 400}, status=400)

    session_id = data.get('session_id', '').strip()
    message_id = data.get('message_id', '').strip()
    rating = data.get('rating', '').strip()
    comment = data.get('comment', '').strip()

    if rating not in ('thumbs_up', 'thumbs_down', 'up', 'down'):
        return JsonResponse({'error': 'Invalid rating value.', 'code': 400}, status=400)

    standardized_rating = 'thumbs_up' if 'up' in rating else 'thumbs_down'
    user_id = request.user.id if request.user.is_authenticated else None

    save_feedback(
        session_id=session_id,
        message_id=message_id,
        rating=standardized_rating,
        comment=comment,
        user_id=user_id
    )

    return JsonResponse({
        'status': 'success',
        'message': 'Thank you for your feedback!'
    })
