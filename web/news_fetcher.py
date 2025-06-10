import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from .models import Article, Source, Category, Interest
from .api_config import (
    NEWS_API_CONFIG, CURRENTS_API_CONFIG, GUARDIAN_API_CONFIG,
    MEDIASTACK_API_CONFIG, GNEWS_API_CONFIG, DEFAULT_PARAMS
)
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)

class NewsFetcher:
    def __init__(self):
        self.sources = {
            'newsapi': self._fetch_newsapi,
            'currents': self._fetch_currents,
            'guardian': self._fetch_guardian,
            'mediastack': self._fetch_mediastack,
            'gnews': self._fetch_gnews
        }
        
        # Настройка сессии с повторными попытками
        self.session = requests.Session()
        retries = Retry(
            total=3,  # количество попыток
            backoff_factor=1,  # увеличиваем время ожидания между попытками
            status_forcelist=[429, 500, 502, 503, 504]  # добавляем 429 в список кодов для повторных попыток
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def fetch_all_news(self):
        """Fetch news from all configured sources"""
        for source_type, fetch_func in self.sources.items():
            try:
                # Проверяем кэш перед запросом
                cache_key = f'news_fetch_{source_type}'
                last_fetch = cache.get(cache_key)
                
                if last_fetch and (timezone.now() - last_fetch) < timedelta(minutes=15):
                    logger.info(f"Skipping {source_type} - cached data is still valid")
                    continue
                
                logger.info(f"Fetching news from {source_type}")
                fetch_func()
                # Сохраняем время последнего успешного запроса
                cache.set(cache_key, timezone.now())
                logger.info(f"Successfully fetched news from {source_type}")
            except requests.exceptions.Timeout:
                logger.error(f"Timeout while fetching from {source_type}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching from {source_type}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error while fetching from {source_type}: {str(e)}")

    def _make_request(self, url, params=None, headers=None, timeout=30):  # Увеличиваем таймаут до 30 секунд
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out: {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url}, error: {str(e)}")
            raise

    def _fetch_newsapi(self):
        """Fetch news from NewsAPI"""
        try:
            cache_key = 'newsapi_articles'
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data

            api_key = NEWS_API_CONFIG['key']
            if not api_key:
                print("NewsAPI key not configured")
                return []

            # Add required parameters for NewsAPI
            params = {
                'apiKey': api_key,
                'language': 'ru',
                'pageSize': 50,
                'sortBy': 'publishedAt',
                'q': 'news',  # Required parameter
                'from': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')  # Required parameter
            }

            response = self.session.get(
                f"{NEWS_API_CONFIG['base_url']}{NEWS_API_CONFIG['endpoints']['everything']}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                print(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []

            articles = []
            for article in data.get('articles', []):
                try:
                    articles.append({
                        'title': article.get('title', ''),
                        'content': article.get('description', ''),
                        'url': article.get('url', ''),
                        'published_at': article.get('publishedAt', ''),
                        'source': article.get('source', {}).get('name', ''),
                        'image_url': article.get('urlToImage', '')
                    })
                except Exception as e:
                    print(f"Error processing NewsAPI article: {str(e)}")
                    continue

            cache.set(cache_key, articles, 900)  # Cache for 15 minutes
            return articles

        except requests.exceptions.RequestException as e:
            print(f"Error fetching from newsapi: {str(e)}")
            return []

    def _fetch_currents(self):
        """Fetch news from Currents API"""
        try:
            cache_key = 'currents_articles'
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data

            api_key = CURRENTS_API_CONFIG['key']
            if not api_key:
                print("Currents API key not configured")
                return []

            # Get rate limit info from cache
            rate_limit_key = 'currents_rate_limit'
            rate_limit_info = cache.get(rate_limit_key, {
                'requests_this_hour': 0,
                'last_request_time': None,
                'backoff_until': None
            })

            current_time = datetime.now()

            # Check if we're in backoff period
            if rate_limit_info['backoff_until'] and current_time < rate_limit_info['backoff_until']:
                print(f"Rate limit backoff in effect until {rate_limit_info['backoff_until']}")
                return []

            # Check hourly rate limit
            if rate_limit_info['last_request_time']:
                time_since_last = (current_time - rate_limit_info['last_request_time']).total_seconds()
                if time_since_last < 3600:  # Within the same hour
                    if rate_limit_info['requests_this_hour'] >= 5:  # Max 5 requests per hour
                        print("Hourly rate limit reached for Currents API")
                        return []
                else:
                    # Reset counter for new hour
                    rate_limit_info['requests_this_hour'] = 0

            # Ensure minimum delay between requests
            if rate_limit_info['last_request_time']:
                time_since_last = (current_time - rate_limit_info['last_request_time']).total_seconds()
                if time_since_last < 2:  # Minimum 2 seconds between requests
                    time.sleep(2 - time_since_last)

            params = {
                'apiKey': api_key,
                'language': 'ru',
                'limit': 50,
                'type': 'news'
            }

            try:
                response = self.session.get(
                    f"{CURRENTS_API_CONFIG['base_url']}{CURRENTS_API_CONFIG['endpoints']['latest_news']}",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                # Update rate limit info on successful request
                rate_limit_info['requests_this_hour'] += 1
                rate_limit_info['last_request_time'] = current_time
                rate_limit_info['backoff_until'] = None
                cache.set(rate_limit_key, rate_limit_info, 3600)  # Cache for 1 hour

                if not data.get('news'):
                    print("No news found in Currents API response")
                    return []

                articles = []
                for article in data.get('news', []):
                    try:
                        articles.append({
                            'title': article.get('title', ''),
                            'content': article.get('description', ''),
                            'url': article.get('url', ''),
                            'published_at': article.get('published', ''),
                            'source': article.get('author', ''),
                            'image_url': article.get('image', '')
                        })
                    except Exception as e:
                        print(f"Error processing Currents API article: {str(e)}")
                        continue

                cache.set(cache_key, articles, 900)  # Cache articles for 15 minutes
                return articles

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Implement exponential backoff
                    backoff_time = min(300, 2 ** rate_limit_info.get('backoff_count', 0))  # Max 5 minutes
                    rate_limit_info['backoff_until'] = current_time + timedelta(seconds=backoff_time)
                    rate_limit_info['backoff_count'] = rate_limit_info.get('backoff_count', 0) + 1
                    cache.set(rate_limit_key, rate_limit_info, 3600)
                    print(f"Rate limit hit, backing off for {backoff_time} seconds")
                raise

        except requests.exceptions.RequestException as e:
            print(f"Error fetching from currents: {str(e)}")
            return []

    def _fetch_guardian(self):
        """Fetch news from The Guardian API"""
        config = GUARDIAN_API_CONFIG
        if not config['key']:
            logger.warning("Guardian API key is not configured")
            return

        params = DEFAULT_PARAMS['guardian'].copy()
        params['api-key'] = config['key']
        
        try:
            data = self._make_request(
                f"{config['base_url']}{config['endpoints']['search']}",
                params=params
            )
            
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
        except Exception as e:
            logger.error(f"Error processing Guardian API response: {str(e)}")
            raise

    def _fetch_mediastack(self):
        """Fetch news from Mediastack API"""
        config = MEDIASTACK_API_CONFIG
        if not config['key']:
            logger.warning("Mediastack API key is not configured")
            return

        params = DEFAULT_PARAMS['mediastack'].copy()
        params['access_key'] = config['key']
        
        try:
            data = self._make_request(
                f"{config['base_url']}{config['endpoints']['news']}",
                params=params
            )
            
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
        except Exception as e:
            logger.error(f"Error processing Mediastack API response: {str(e)}")
            raise

    def _fetch_gnews(self):
        """Fetch news from GNews API"""
        config = GNEWS_API_CONFIG
        if not config['key']:
            logger.warning("GNews API key is not configured")
            return

        params = DEFAULT_PARAMS['gnews'].copy()
        params['apikey'] = config['key']
        
        try:
            data = self._make_request(
                f"{config['base_url']}{config['endpoints']['top_headlines']}",
                params=params
            )
            
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
        except Exception as e:
            logger.error(f"Error processing GNews API response: {str(e)}")
            raise

    def _create_article(self, title, content, url, published_at, source, category_name=None):
        """Create an article in the database"""
        if not all([title, content, url, published_at, source]):
            return

        # Convert published_at to datetime if it's a string
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid date format: {published_at}")
                return

        # Get or create category
        category = None
        if category_name:
            category, _ = Category.objects.get_or_create(name=category_name)

        try:
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
        except Exception as e:
            logger.error(f"Error creating/updating article: {str(e)}")
            return None 