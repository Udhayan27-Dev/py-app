import logging
from datetime import datetime, timezone
from django.conf import settings
import pymongo

logger = logging.getLogger(__name__)

_mongo_client = None

# In-memory storage fallback for local testing when Atlas connection string is not provided
_fallback_chat_logs = []
_fallback_feedback = []

def get_mongo_client():
    global _mongo_client
    uri = getattr(settings, 'MONGO_URI', '').strip()
    if not uri:
        return None

    if _mongo_client is None:
        try:
            _mongo_client = pymongo.MongoClient(
                uri,
                serverSelectionTimeoutMS=2500,
                connectTimeoutMS=2500,
                socketTimeoutMS=2500
            )
        except Exception as e:
            logger.warning(f"Could not initialize MongoClient: {e}")
            return None
    return _mongo_client

def get_mongo_db():
    client = get_mongo_client()
    if client is not None:
        try:
            db_name = getattr(settings, 'MONGO_DB_NAME', 'planmystudy_db')
            return client[db_name]
        except Exception as e:
            logger.warning(f"Could not access MongoDB database: {e}")
            return None
    return None

def log_chat_message(session_id: str, user_message: str, assistant_reply: str, source: str, response_time_ms: float, user_id=None):
    """
    Log chat exchange into MongoDB chat_logs collection.
    Document structure:
    session_id, timestamp, user_message, assistant_reply, source, response_time_ms, user_id
    """
    doc = {
        'session_id': session_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'user_message': user_message,
        'assistant_reply': assistant_reply,
        'source': source,  # 'faq', 'error_code', 'llm', 'ticket_created'
        'response_time_ms': round(response_time_ms, 2),
        'user_id': user_id
    }

    db = get_mongo_db()
    if db is not None:
        try:
            db.chat_logs.insert_one(doc)
            return True
        except Exception as e:
            logger.warning(f"Failed to insert chat_log into MongoDB: {e}")

    # Fallback storage
    _fallback_chat_logs.append(doc)
    return True

def save_feedback(session_id: str, message_id: str, rating: str, comment: str = "", user_id=None):
    """
    Log thumbs up/down feedback into MongoDB feedback collection.
    Document structure:
    session_id, message_id, rating, comment, timestamp, user_id
    """
    doc = {
        'session_id': session_id,
        'message_id': message_id,
        'rating': rating,  # 'thumbs_up' or 'thumbs_down'
        'comment': comment,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'user_id': user_id
    }

    db = get_mongo_db()
    if db is not None:
        try:
            db.feedback.insert_one(doc)
            return True
        except Exception as e:
            logger.warning(f"Failed to insert feedback into MongoDB: {e}")

    # Fallback storage
    _fallback_feedback.append(doc)
    return True

def check_mongo_connection():
    """
    Check MongoDB connectivity for /health/ page.
    Returns (status: bool, message: str)
    """
    uri = getattr(settings, 'MONGO_URI', '').strip()
    if not uri:
        return True, "Mock / In-Memory Fallback Active (MONGO_URI not configured)"

    client = get_mongo_client()
    if client is None:
        return False, "Failed to initialize MongoDB client"

    try:
        # Ping the server
        client.admin.command('ping')
        return True, "Connected to MongoDB Atlas"
    except Exception as e:
        return False, f"Connection error: {str(e)}"
