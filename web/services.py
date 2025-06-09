import requests
from datetime import datetime
from django.conf import settings
from .models import Article, Source

class NewsAPIService:
    BASE_URL = 'https://newsapi.org/v2'
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'X-Api-Key': api_key
        }

    def get_top_headlines(self, country='ru', category=None, page_size=100):
        """Получает топ новостей"""
        params = {
            'country': country,
            'pageSize': page_size
        }
        if category:
            params['category'] = category

        response = requests.get(
            f'{self.BASE_URL}/top-headlines',
            headers=self.headers,
            params=params
        )
        return response.json()

    def search_news(self, query, from_date=None, language='ru', page_size=100):
        """Поиск новостей"""
        params = {
            'q': query,
            'language': language,
            'pageSize': page_size
        }
        if from_date:
            params['from'] = from_date

        response = requests.get(
            f'{self.BASE_URL}/everything',
            headers=self.headers,
            params=params
        )
        return response.json()

    def save_articles(self, articles_data):
        """Сохраняет статьи в базу"""
        saved_articles = []
        for article in articles_data:
            # Получаем или создаем источник
            source, _ = Source.objects.get_or_create(
                name=article['source']['name'],
                defaults={'link': article['url']}
            )

            # Создаем статью
            article_obj, created = Article.objects.get_or_create(
                url=article['url'],
                defaults={
                    'title': article['title'],
                    'content': article.get('description', ''),
                    'published_at': datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')),
                    'source': source
                }
            )
            if created:
                saved_articles.append(article_obj)

        return saved_articles 