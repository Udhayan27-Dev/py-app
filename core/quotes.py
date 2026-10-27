import random
import logging
import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

FALLBACK_QUOTES = [
    {
        "q": "The secret of getting ahead is getting started. The secret of getting started is breaking your complex overwhelming tasks into small manageable tasks, and then starting on the first one.",
        "a": "Mark Twain"
    },
    {
        "q": "It does not matter how slowly you go as long as you do not stop.",
        "a": "Confucius"
    },
    {
        "q": "Success is the sum of small efforts, repeated day in and day out.",
        "a": "Robert Collier"
    },
    {
        "q": "Believe you can and you're halfway there.",
        "a": "Theodore Roosevelt"
    },
    {
        "q": "Action is the foundational key to all success.",
        "a": "Pablo Picasso"
    },
    {
        "q": "You don't have to be great to start, but you have to start to be great.",
        "a": "Zig Ziglar"
    },
    {
        "q": "Focus on being productive instead of busy.",
        "a": "Tim Ferriss"
    },
    {
        "q": "Discipline is the bridge between goals and accomplishment.",
        "a": "Jim Rohn"
    },
    {
        "q": "Small daily improvements over time lead to stunning results.",
        "a": "Robin Sharma"
    },
    {
        "q": "The expert in anything was once a beginner.",
        "a": "Helen Hayes"
    }
]

def get_motivation_quote():
    """
    Fetch quote of the day from ZenQuotes API with 3-second timeout and 1-hour cache.
    Falls back to a curated random quote if the API times out or fails.
    Returns dict with keys: 'quote', 'author', 'source'
    """
    cache_key = "zenquotes_motivation_of_the_day"
    cached = cache.get(cache_key)
    if cached:
        return cached

    url = "https://zenquotes.io/api/today"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0 and 'q' in data[0]:
                quote_data = {
                    'quote': data[0].get('q'),
                    'author': data[0].get('a', 'Unknown'),
                    'source': 'ZenQuotes API'
                }
                # Cache for 1 hour (3600 seconds)
                cache.set(cache_key, quote_data, timeout=3600)
                return quote_data
    except Exception as e:
        logger.warning(f"Failed to fetch quote from ZenQuotes: {e}. Using fallback quote.")

    # Fallback to random built-in quote
    selected = random.choice(FALLBACK_QUOTES)
    fallback_data = {
        'quote': selected['q'],
        'author': selected['a'],
        'source': 'PlanMyStudy Inspiration'
    }
    return fallback_data
