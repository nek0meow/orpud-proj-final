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
        # Простой алгоритм определения тегов на основе ключевых слов
        tags = []
        keywords = {
            'technology': ['tech', 'technology', 'software', 'hardware', 'ai', 'artificial intelligence', 'machine learning', 'computer', 'digital', 'internet', 'cyber', 'data', 'app', 'mobile', 'startup', 'gadget', 'device', 'programming', 'code', 'developer', 'innovation'],
            'science': ['science', 'research', 'study', 'discovery', 'scientific', 'experiment', 'scientist', 'lab', 'university', 'academic', 'theory', 'physics', 'chemistry', 'biology', 'medicine', 'medical', 'health', 'disease', 'treatment', 'covid', 'vaccine', 'virus', 'genetic', 'dna', 'space', 'astronomy', 'climate', 'environment'],
            'business': ['business', 'economy', 'market', 'stock', 'finance', 'trading', 'company', 'corporate', 'investment', 'bank', 'money', 'dollar', 'euro', 'profit', 'revenue', 'industry', 'commerce', 'trade', 'economic', 'financial', 'business', 'enterprise', 'startup', 'venture', 'funding'],
            'sports': ['sport', 'football', 'basketball', 'tennis', 'olympics', 'game', 'match', 'player', 'team', 'league', 'championship', 'tournament', 'coach', 'score', 'win', 'loss', 'athlete', 'competition', 'soccer', 'baseball', 'hockey', 'golf', 'racing', 'fitness', 'training'],
            'entertainment': ['movie', 'film', 'music', 'celebrity', 'entertainment', 'actor', 'actress', 'director', 'show', 'concert', 'theater', 'performance', 'artist', 'album', 'song', 'tv', 'television', 'series', 'drama', 'comedy', 'entertainment', 'media', 'celebrity', 'star', 'famous'],
            'health': ['health', 'medical', 'disease', 'treatment', 'covid', 'doctor', 'hospital', 'patient', 'medicine', 'drug', 'vaccine', 'symptom', 'diagnosis', 'therapy', 'wellness', 'fitness', 'nutrition', 'diet', 'exercise', 'mental health', 'psychology', 'counseling', 'therapy'],
            'politics': ['politics', 'government', 'election', 'president', 'congress', 'democrat', 'republican', 'policy', 'law', 'bill', 'vote', 'campaign', 'party', 'minister', 'political', 'administration', 'policy', 'legislation', 'diplomacy', 'international', 'foreign', 'domestic']
        }
        
        text = f"{title} {content}".lower()
        word_count = len(text.split())
        
        # Считаем количество совпадений для каждого тега
        tag_scores = {}
        for tag, words in keywords.items():
            matches = sum(1 for word in words if word in text)
            if matches > 0:
                # Нормализуем по длине текста и количеству ключевых слов
                score = matches / (word_count * len(words))
                tag_scores[tag] = score
        
        # Берем теги с наибольшим скором
        if tag_scores:
            max_score = max(tag_scores.values())
            # Снизим порог для включения тега
            tags = [tag for tag, score in tag_scores.items() if score >= max_score * 0.3]
        
        return {
            "title": title,
            "content": content,
            "source": source_name,
            "published_at": published_at.isoformat(),
            "url": url,
            "tags": tags
        }

class NewsAPIParser(BaseParser):
    def parse(self):
        url = 'https://newsapi.org/v2/top-headlines'
        params = {
            'country': 'us',
            'apiKey': settings.NEWS_API_KEY  # Берем ключ из settings
        }
        response = requests.get(url, params=params)
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
                article_obj, created = Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
                if created:
                    # Set interests after creation
                    article_obj.interests.set(Interest.objects.filter(name__in=formatted['tags']))
            return {"articles": articles}

class GNewsParser(BaseParser):
    def parse(self):
        url = 'https://gnews.io/api/v4/top-headlines'
        params = {
            'country': 'us',
            'token': self.api_key,
            'lang': 'en'
        }
        response = requests.get(url, params=params)
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
                article_obj, created = Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
                if created:
                    # Set interests after creation
                    article_obj.interests.set(Interest.objects.filter(name__in=formatted['tags']))
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
                article_obj, created = Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
                if created:
                    # Set interests after creation
                    article_obj.interests.set(Interest.objects.filter(name__in=formatted['tags']))
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
                article_obj, created = Article.objects.get_or_create(
                    url=article['webUrl'],
                    defaults={
                        'title': article['webTitle'],
                        'content': article.get('fields', {}).get('bodyText', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
                if created:
                    # Set interests after creation
                    article_obj.interests.set(Interest.objects.filter(name__in=formatted['tags']))
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
                article_obj, created = Article.objects.get_or_create(
                    url=article['url'],
                    defaults={
                        'title': article['title'],
                        'content': article.get('description', ''),
                        'published_at': published_at,
                        'source': self.source
                    }
                )
                if created:
                    # Set interests after creation
                    article_obj.interests.set(Interest.objects.filter(name__in=formatted['tags']))
            return {"articles": articles}

PARSERS = {
    'newsapi': NewsAPIParser,
    'gnews': GNewsParser,
    'mediastack': MediastackParser,
    'guardian': GuardianParser,
    'currents': CurrentsParser
} 