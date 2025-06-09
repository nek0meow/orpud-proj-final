import requests
from datetime import datetime
from .models import Article, Source, Interest
from django.conf import settings

class BaseParser:
    def __init__(self, source):
        self.source = source
        self.api_key = source.api_key

    def parse(self):
        raise NotImplementedError

    def format_article(self, title, content, url, published_at, source_name):
        return {
            "title": title,
            "content": content,
            "source": source_name,
            "published_at": published_at.isoformat(),
            "url": url,
            "interests": []  # Будет заполняться ML моделью позже
        }

class NewsAPIParser(BaseParser):
    def parse(self):
        url = 'https://newsapi.org/v2/top-headlines'
        params = {
            'country': 'us',
            'apiKey': settings.NEWS_API_KEY  # Берем ключ из settings
        }
        print(f"NewsAPI request URL: {url}")
        print(f"NewsAPI params: {params}")
        response = requests.get(url, params=params)
        print(f"NewsAPI response status: {response.status_code}")
        print(f"NewsAPI response: {response.text[:500]}")  # Первые 500 символов ответа
        if response.status_code == 200:
            data = response.json()
            articles = []
            for article in data.get('articles', []):
                published_at = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                formatted = self.format_article(
                    title=article['title'],
                    content=article.get('description', ''),
                    url=article['url'],
                    published_at=published_at,
                    source_name=self.source.name
                )
                articles.append(formatted)
                Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
            return {"articles": articles}

class GNewsParser(BaseParser):
    def parse(self):
        url = 'https://gnews.io/api/v4/top-headlines'
        params = {
            'country': 'us',
            'token': self.api_key,
            'lang': 'en'
        }
        print(f"GNews request URL: {url}")
        print(f"GNews params: {params}")
        response = requests.get(url, params=params)
        print(f"GNews response status: {response.status_code}")
        print(f"GNews response: {response.text[:500]}")  # Первые 500 символов ответа
        if response.status_code == 200:
            data = response.json()
            articles = []
            for article in data.get('articles', []):
                published_at = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                formatted = self.format_article(
                    title=article['title'],
                    content=article.get('description', ''),
                    url=article['url'],
                    published_at=published_at,
                    source_name=self.source.name
                )
                articles.append(formatted)
                Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
            return {"articles": articles}

class MediastackParser(BaseParser):
    def parse(self):
        url = 'http://api.mediastack.com/v1/news'
        params = {
            'access_key': self.api_key,
            'countries': 'us',
            'languages': 'en'
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            articles = []
            for article in data.get('data', []):
                published_at = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                formatted = self.format_article(
                    title=article['title'],
                    content=article.get('description', ''),
                    url=article['url'],
                    published_at=published_at,
                    source_name=self.source.name
                )
                articles.append(formatted)
                Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
            return {"articles": articles}

class GuardianParser(BaseParser):
    def parse(self):
        url = 'https://content.guardianapis.com/search'
        params = {
            'api-key': self.api_key,
            'section': 'world',
            'show-fields': 'bodyText'
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            articles = []
            for article in data.get('response', {}).get('results', []):
                published_at = datetime.fromisoformat(article['webPublicationDate'].replace('Z', '+00:00'))
                formatted = self.format_article(
                    title=article['webTitle'],
                    content=article.get('fields', {}).get('bodyText', ''),
                    url=article['webUrl'],
                    published_at=published_at,
                    source_name=self.source.name
                )
                articles.append(formatted)
                Article.objects.get_or_create(
                    url=article['webUrl'],
                    defaults={
                        'title': article['webTitle'],
                        'content': article.get('fields', {}).get('bodyText', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
            return {"articles": articles}

class CurrentsParser(BaseParser):
    def parse(self):
        url = 'https://api.currentsapi.services/v1/latest-news'
        params = {
            'apiKey': self.api_key,
            'language': 'en',
            'country': 'US'
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            articles = []
            for article in data.get('news', []):
                published_at = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
                formatted = self.format_article(
                    title=article['title'],
                    content=article.get('description', ''),
                    url=article['url'],
                    published_at=published_at,
                    source_name=self.source.name
                )
                articles.append(formatted)
                Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
            return {"articles": articles}

PARSERS = {
    'newsapi': NewsAPIParser,
    'gnews': GNewsParser,
    'mediastack': MediastackParser,
    'guardian': GuardianParser,
    'currents': CurrentsParser
} 