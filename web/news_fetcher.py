import requests
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Article, Source, Category, Interest
from .api_config import (
    NEWS_API_CONFIG, CURRENTS_API_CONFIG, GUARDIAN_API_CONFIG,
    MEDIASTACK_API_CONFIG, GNEWS_API_CONFIG, DEFAULT_PARAMS
)

class NewsFetcher:
    def __init__(self):
        self.sources = {
            'newsapi': self._fetch_newsapi,
            'currents': self._fetch_currents,
            'guardian': self._fetch_guardian,
            'mediastack': self._fetch_mediastack,
            'gnews': self._fetch_gnews
        }

    def fetch_all_news(self):
        """Fetch news from all configured sources"""
        for source_type, fetch_func in self.sources.items():
            try:
                fetch_func()
            except Exception as e:
                print(f"Error fetching from {source_type}: {e}")

    def _fetch_newsapi(self):
        """Fetch news from NewsAPI"""
        config = NEWS_API_CONFIG
        params = DEFAULT_PARAMS['newsapi'].copy()
        params['apiKey'] = config['key']
        
        response = requests.get(
            f"{config['base_url']}{config['endpoints']['everything']}",
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            source, _ = Source.objects.get_or_create(
                name='NewsAPI',
                defaults={'link': 'https://newsapi.org', 'source_type': 'newsapi'}
            )
            
            for article in data.get('articles', []):
                self._create_article(
                    title=article.get('title'),
                    content=article.get('description', ''),
                    url=article.get('url'),
                    published_at=article.get('publishedAt'),
                    source=source,
                    category_name=article.get('source', {}).get('name')
                )

    def _fetch_currents(self):
        """Fetch news from Currents API"""
        config = CURRENTS_API_CONFIG
        params = DEFAULT_PARAMS['currents'].copy()
        params['apiKey'] = config['key']
        
        response = requests.get(
            f"{config['base_url']}{config['endpoints']['latest_news']}",
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            source, _ = Source.objects.get_or_create(
                name='Currents API',
                defaults={'link': 'https://currentsapi.services', 'source_type': 'currents'}
            )
            
            for article in data.get('news', []):
                self._create_article(
                    title=article.get('title'),
                    content=article.get('description', ''),
                    url=article.get('url'),
                    published_at=article.get('published'),
                    source=source,
                    category_name=article.get('category', [None])[0]
                )

    def _fetch_guardian(self):
        """Fetch news from The Guardian API"""
        config = GUARDIAN_API_CONFIG
        params = DEFAULT_PARAMS['guardian'].copy()
        params['api-key'] = config['key']
        
        response = requests.get(
            f"{config['base_url']}{config['endpoints']['search']}",
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            source, _ = Source.objects.get_or_create(
                name='The Guardian',
                defaults={'link': 'https://www.theguardian.com', 'source_type': 'guardian'}
            )
            
            for article in data.get('response', {}).get('results', []):
                self._create_article(
                    title=article.get('webTitle'),
                    content=article.get('fields', {}).get('bodyText', ''),
                    url=article.get('webUrl'),
                    published_at=article.get('webPublicationDate'),
                    source=source,
                    category_name=article.get('sectionName')
                )

    def _fetch_mediastack(self):
        """Fetch news from Mediastack API"""
        config = MEDIASTACK_API_CONFIG
        params = DEFAULT_PARAMS['mediastack'].copy()
        params['access_key'] = config['key']
        
        response = requests.get(
            f"{config['base_url']}{config['endpoints']['news']}",
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            source, _ = Source.objects.get_or_create(
                name='Mediastack',
                defaults={'link': 'https://mediastack.com', 'source_type': 'mediastack'}
            )
            
            for article in data.get('data', []):
                self._create_article(
                    title=article.get('title'),
                    content=article.get('description', ''),
                    url=article.get('url'),
                    published_at=article.get('published_at'),
                    source=source,
                    category_name=article.get('category')
                )

    def _fetch_gnews(self):
        """Fetch news from GNews API"""
        config = GNEWS_API_CONFIG
        params = DEFAULT_PARAMS['gnews'].copy()
        params['apikey'] = config['key']
        
        response = requests.get(
            f"{config['base_url']}{config['endpoints']['top_headlines']}",
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            source, _ = Source.objects.get_or_create(
                name='GNews',
                defaults={'link': 'https://gnews.io', 'source_type': 'gnews'}
            )
            
            for article in data.get('articles', []):
                self._create_article(
                    title=article.get('title'),
                    content=article.get('description', ''),
                    url=article.get('url'),
                    published_at=article.get('publishedAt'),
                    source=source,
                    category_name=article.get('source', {}).get('name')
                )

    def _create_article(self, title, content, url, published_at, source, category_name=None):
        """Create an article in the database"""
        if not all([title, content, url, published_at, source]):
            return

        # Convert published_at to datetime if it's a string
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except ValueError:
                return

        # Get or create category
        category = None
        if category_name:
            category, _ = Category.objects.get_or_create(name=category_name)

        # Create or update article
        article, created = Article.objects.update_or_create(
            url=url,
            defaults={
                'title': title,
                'content': content,
                'published_at': published_at,
                'source': source,
                'category': category
            }
        )

        # Update source's last_parsed timestamp
        source.last_parsed = timezone.now()
        source.save()

        return article 