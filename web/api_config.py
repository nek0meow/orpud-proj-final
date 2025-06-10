import os
from django.conf import settings

def get_api_key(key_name, default=None):
    """Get API key from environment or settings with validation"""
    key = os.getenv(key_name) or getattr(settings, key_name, default)
    if not key:
        print(f"Warning: {key_name} is not configured")
    return key

# API configurations
NEWS_API_CONFIG = {
    'key': get_api_key('NEWS_API_KEY', '23495ad2015c408c9b6fc7a4eaf1e172'),
    'base_url': 'https://newsapi.org/v2',
    'endpoints': {
        'top_headlines': '/top-headlines',
        'everything': '/everything'
    },
    'rate_limit': {
        'requests_per_day': 100,
        'requests_per_hour': 10
    }
}

CURRENTS_API_CONFIG = {
    'key': get_api_key('CURRENTS_API_KEY', '9eGtKHLM56kSvdvr69ZmgTRC5MHP3BMs_ZYNmYDodzFdCfdU'),
    'base_url': 'https://api.currentsapi.services/v1',
    'endpoints': {
        'latest_news': '/latest-news',
        'search': '/search'
    },
    'rate_limit': {
        'requests_per_day': 50,
        'requests_per_hour': 5
    }
}

GUARDIAN_API_CONFIG = {
    'key': get_api_key('GUARDIAN_API_KEY', '1e4b2f50-778c-4980-a7df-e7079b6daecf'),
    'base_url': 'https://content.guardianapis.com',
    'endpoints': {
        'search': '/search'
    },
    'rate_limit': {
        'requests_per_day': 200,
        'requests_per_hour': 20
    }
}

MEDIASTACK_API_CONFIG = {
    'key': get_api_key('MEDIASTACK_API_KEY', '4fddead40fc954dcf00636774e916a05'),
    'base_url': 'http://api.mediastack.com/v1',
    'endpoints': {
        'news': '/news'
    },
    'rate_limit': {
        'requests_per_day': 500,
        'requests_per_hour': 50
    }
}

GNEWS_API_CONFIG = {
    'key': get_api_key('GNEWS_API_KEY', '393168a7489a0a2a2a352d86558d7976'),
    'base_url': 'https://gnews.io/api/v4',
    'endpoints': {
        'top_headlines': '/top-headlines',
        'search': '/search'
    },
    'rate_limit': {
        'requests_per_day': 100,
        'requests_per_hour': 10
    }
}

# Default parameters for each API
DEFAULT_PARAMS = {
    'newsapi': {
        'language': 'ru',
        'pageSize': 50,
        'sortBy': 'publishedAt'
    },
    'currents': {
        'language': 'ru',
        'limit': 50
    },
    'guardian': {
        'show-fields': 'bodyText,thumbnail',
        'page-size': 50,
        'lang': 'ru'
    },
    'mediastack': {
        'languages': 'ru',
        'limit': 50
    },
    'gnews': {
        'lang': 'ru',
        'max': 50
    }
} 