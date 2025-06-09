import os
import django
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Bot
from web.models import Article, UserProfile, Source
import requests
import json

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aggregator_super.settings')
django.setup()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def send_notification(bot, user_profile, article):
    """Отправляет уведомление пользователю о новой статье"""
    try:
        # Получаем теги статьи
        article_tags = list(article.interests.all())
        # Получаем теги пользователя
        user_tags = list(user_profile.interests.all())
        
        # Проверяем, есть ли общие теги
        common_tags = set(article_tags) & set(user_tags)
        if not common_tags:
            return
        
        message = (
            f"📰 *Новая статья по вашим интересам!*\n\n"
            f"*{article.title}*\n\n"
            f"{article.content[:200]}...\n\n"
            f"🏷 Теги: {', '.join([i.name for i in article_tags])}\n"
            f"🔗 [Читать статью]({article.url})"
        )
        
        await bot.send_message(
            chat_id=user_profile.telegram_id,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_profile.telegram_id}: {e}")

async def check_newsapi(source):
    """Проверяет новые статьи через NewsAPI"""
    try:
        url = 'https://newsapi.org/v2/top-headlines'
        params = {
            'apiKey': source.api_key,
            'language': 'ru',
            'pageSize': 10
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] != 'ok':
            logger.error(f"NewsAPI error: {data}")
            return
        
        for article_data in data['articles']:
            # Проверяем, есть ли уже такая статья
            if Article.objects.filter(url=article_data['url']).exists():
                continue
            
            # Создаем новую статью
            article = Article.objects.create(
                title=article_data['title'],
                content=article_data['description'] or article_data['title'],
                url=article_data['url'],
                published_at=datetime.fromisoformat(article_data['publishedAt'].replace('Z', '+00:00')),
                source=source
            )
            
            # TODO: Добавить определение тегов через ML модель
            
            logger.info(f"New article found: {article.title}")
            
            # Отправляем уведомления
            token = os.getenv('TELEGRAM_BOT_TOKEN', '8153321610:AAEQAJ7hp3S0-qzbT4COGAVPrMy19LskWoA')
            bot = Bot(token=token)
            
            # Получаем пользователей с включенными уведомлениями
            users = UserProfile.objects.filter(notifications_enabled=True)
            
            # Отправляем уведомления
            for user_profile in users:
                if user_profile.telegram_id:
                    await send_notification(bot, user_profile, article)
    
    except Exception as e:
        logger.error(f"Error checking NewsAPI: {e}")

async def check_gnews(source):
    """Проверяет новые статьи через GNews"""
    try:
        url = 'https://gnews.io/api/v4/top-headlines'
        params = {
            'token': source.api_key,
            'lang': 'ru',
            'max': 10
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        for article_data in data['articles']:
            # Проверяем, есть ли уже такая статья
            if Article.objects.filter(url=article_data['url']).exists():
                continue
            
            # Создаем новую статью
            article = Article.objects.create(
                title=article_data['title'],
                content=article_data['description'],
                url=article_data['url'],
                published_at=datetime.fromisoformat(article_data['publishedAt'].replace('Z', '+00:00')),
                source=source
            )
            
            # TODO: Добавить определение тегов через ML модель
            
            logger.info(f"New article found: {article.title}")
            
            # Отправляем уведомления
            token = os.getenv('TELEGRAM_BOT_TOKEN', '8153321610:AAEQAJ7hp3S0-qzbT4COGAVPrMy19LskWoA')
            bot = Bot(token=token)
            
            # Получаем пользователей с включенными уведомлениями
            users = UserProfile.objects.filter(notifications_enabled=True)
            
            # Отправляем уведомления
            for user_profile in users:
                if user_profile.telegram_id:
                    await send_notification(bot, user_profile, article)
    
    except Exception as e:
        logger.error(f"Error checking GNews: {e}")

async def check_mediastack(source):
    """Проверяет новые статьи через Mediastack"""
    try:
        url = 'http://api.mediastack.com/v1/news'
        params = {
            'access_key': source.api_key,
            'languages': 'ru',
            'limit': 10
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        for article_data in data['data']:
            # Проверяем, есть ли уже такая статья
            if Article.objects.filter(url=article_data['url']).exists():
                continue
            
            # Создаем новую статью
            article = Article.objects.create(
                title=article_data['title'],
                content=article_data['description'],
                url=article_data['url'],
                published_at=datetime.fromisoformat(article_data['published_at'].replace('Z', '+00:00')),
                source=source
            )
            
            # TODO: Добавить определение тегов через ML модель
            
            logger.info(f"New article found: {article.title}")
            
            # Отправляем уведомления
            token = os.getenv('TELEGRAM_BOT_TOKEN', '8153321610:AAEQAJ7hp3S0-qzbT4COGAVPrMy19LskWoA')
            bot = Bot(token=token)
            
            # Получаем пользователей с включенными уведомлениями
            users = UserProfile.objects.filter(notifications_enabled=True)
            
            # Отправляем уведомления
            for user_profile in users:
                if user_profile.telegram_id:
                    await send_notification(bot, user_profile, article)
    
    except Exception as e:
        logger.error(f"Error checking Mediastack: {e}")

async def check_new_articles():
    """Проверяет новые статьи из всех источников"""
    sources = Source.objects.filter(is_active=True)
    
    for source in sources:
        if source.source_type == 'newsapi':
            await check_newsapi(source)
        elif source.source_type == 'gnews':
            await check_gnews(source)
        elif source.source_type == 'mediastack':
            await check_mediastack(source)
        
        # Обновляем время последней проверки
        source.last_parsed = datetime.now()
        source.save()

async def main():
    """Основной цикл проверки"""
    while True:
        try:
            await check_new_articles()
            logger.info("Checked for new articles")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        
        # Ждем 10 минут
        await asyncio.sleep(600)

if __name__ == '__main__':
    asyncio.run(main()) 