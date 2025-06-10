NEWS_API_CONFIG = {
    'key': '23495ad2015c408c9b6fc7a4eaf1e172',
    'base_url': 'https://newsapi.org/v2',
    'endpoints': {
        'top_headlines': '/top-headlines',
        'everything': '/everything'
    }
}

CURRENTS_API_CONFIG = {
    'key': '9eGtKHLM56kSvdvr69ZmgTRC5MHP3BMs_ZYNmYDodzFdCfdU',
    'base_url': 'https://api.currentsapi.services/v1',
    'endpoints': {
        'latest_news': '/latest-news',
        'search': '/search'
    }
}

GUARDIAN_API_CONFIG = {
    'key': '1e4b2f50-778c-4980-a7df-e7079b6daecf',
    'base_url': 'https://content.guardianapis.com',
    'endpoints': {
        'search': '/search'
    }
}

MEDIASTACK_API_CONFIG = {
    'key': '4fddead40fc954dcf00636774e916a05',
    'base_url': 'http://api.mediastack.com/v1',
    'endpoints': {
        'news': '/news'
    }
}

GNEWS_API_CONFIG = {
    'key': '393168a7489a0a2a2a352d86558d7976',
    'base_url': 'https://gnews.io/api/v4',
    'endpoints': {
        'top_headlines': '/top-headlines',
        'search': '/search'
    }
}

# Default parameters for each API
DEFAULT_PARAMS = {
    'newsapi': {
        'language': 'en',
        'pageSize': 100
    },
    'currents': {
        'language': 'en',
        'limit': 100
    },
    'guardian': {
        'show-fields': 'bodyText,thumbnail',
        'page-size': 100
    },
    'mediastack': {
        'languages': 'en',
        'limit': 100
    },
    'gnews': {
        'lang': 'en',
        'max': 100
    }
} 