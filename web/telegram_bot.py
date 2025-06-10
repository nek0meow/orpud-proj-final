import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aggregator_super.settings')
django.setup()

import logging
import signal
import sys
import msvcrt
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import Conflict, NetworkError
from django.conf import settings
from web.models import Article, Interest, UserProfile, SavedArticle
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.db import IntegrityError
import secrets
import string

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
application = None
lock_file = None

def acquire_lock():
    """Получение блокировки для предотвращения множественных экземпляров"""
    global lock_file
    lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot.lock')
    try:
        # Проверяем, существует ли файл блокировки
        if os.path.exists(lock_path):
            # Проверяем, не устарел ли файл блокировки (старше 5 минут)
            if time.time() - os.path.getmtime(lock_path) > 300:
                os.remove(lock_path)
            else:
                logger.error("Lock file exists and is not stale")
                return False

        lock_file = open(lock_path, 'w')
        # Пытаемся получить эксклюзивную блокировку
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        logger.info("Lock acquired successfully")
        return True
    except IOError:
        logger.error("Another instance is already running")
        if lock_file:
            lock_file.close()
        return False

def release_lock():
    """Освобождение блокировки"""
    global lock_file
    if lock_file:
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            lock_file.close()
            # Удаляем файл блокировки
            lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot.lock')
            if os.path.exists(lock_path):
                os.remove(lock_path)
            logger.info("Lock released")
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения работы"""
    logger.info("Получен сигнал завершения работы")
    if application:
        application.stop()
    release_lock()
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def cleanup_webhook(token):
    """Очистка вебхука перед запуском"""
    try:
        async with Application.builder().token(token).build() as temp_app:
            await temp_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up webhook: {e}")

@sync_to_async
def get_or_create_user_profile(telegram_id, username=None):
    """Получение или создание профиля пользователя"""
    try:
        user_profile = UserProfile.objects.get(telegram_id=telegram_id)
        if username and user_profile.user.username != username:
            user_profile.user.username = username
            user_profile.user.save()
        return user_profile
    except UserProfile.DoesNotExist:
        # Создаем пользователя с случайным паролем
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        if not username:
            username = f"telegram_{telegram_id}"
        
        user = User.objects.create_user(
            username=username,
            password=password,
            is_active=True
        )
        return UserProfile.objects.create(user=user, telegram_id=telegram_id)

@sync_to_async
def get_latest_articles_with_tags():
    articles = Article.objects.all().order_by('-published_at')[:5]
    result = []
    for article in articles:
        tags = [i.name for i in article.interests.all()]
        result.append({
            "title": article.title,
            "content": article.content,
            "url": article.url,
            "published_at": article.published_at,
            "tags": tags,
            "id": article.id,
        })
    return result

@sync_to_async
def get_all_tags_list():
    tags = Interest.objects.all()
    return [{"id": tag.id, "name": tag.name} for tag in tags]

@sync_to_async
def get_tag_articles_with_tags(tag_id):
    tag = Interest.objects.get(id=tag_id)
    articles = Article.objects.filter(interests=tag).order_by('-published_at')[:5]
    result = []
    for article in articles:
        tags = [i.name for i in article.interests.all()]
        result.append({
            "title": article.title,
            "content": article.content,
            "url": article.url,
            "published_at": article.published_at,
            "tags": tags,
            "id": article.id,
        })
    return result

@sync_to_async
def add_article_to_favorites(telegram_id, article_id):
    """Добавление статьи в избранное"""
    try:
        user_profile = UserProfile.objects.get(telegram_id=telegram_id)
        article = Article.objects.get(id=article_id)
        SavedArticle.objects.get_or_create(user=user_profile.user, article=article)
        return True
    except (UserProfile.DoesNotExist, Article.DoesNotExist):
        return False

async def add_to_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление статьи в избранное"""
    query = update.callback_query
    await query.answer()
    
    try:
        article_id = query.data.split('_')[1]
        success = await add_article_to_favorites(query.from_user.id, article_id)
        
        if success:
            keyboard = [
                [InlineKeyboardButton("❌ Удалить из избранного", callback_data=f'unfavorite_{article_id}')],
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ]
            await query.edit_message_text(
                "✅ Статья добавлена в избранное!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
            await query.edit_message_text(
                "❌ Не удалось добавить статью в избранное.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Error in add_to_favorites: {e}")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        await query.edit_message_text(
            "❌ Произошла ошибка при добавлении в избранное.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

@sync_to_async
def remove_article_from_favorites(telegram_id, article_id):
    """Удаление статьи из избранного"""
    try:
        user_profile = UserProfile.objects.get(telegram_id=telegram_id)
        article = Article.objects.get(id=article_id)
        SavedArticle.objects.filter(user=user_profile.user, article=article).delete()
        return True
    except (UserProfile.DoesNotExist, Article.DoesNotExist):
        return False

async def remove_from_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление статьи из избранного"""
    query = update.callback_query
    await query.answer()
    
    try:
        article_id = query.data.split('_')[1]
        success = await remove_article_from_favorites(query.from_user.id, article_id)
        
        if success:
            keyboard = [
                [InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f'favorite_{article_id}')],
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ]
            await query.edit_message_text(
                "✅ Статья удалена из избранного!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
            await query.edit_message_text(
                "❌ Не удалось удалить статью из избранного.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Error in remove_from_favorites: {e}")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        await query.edit_message_text(
            "❌ Произошла ошибка при удалении из избранного.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

@sync_to_async
def get_user_favorites_with_tags(telegram_id):
    """Получение избранных статей пользователя с тегами"""
    try:
        user_profile = UserProfile.objects.get(telegram_id=telegram_id)
        saved = SavedArticle.objects.filter(user=user_profile.user).order_by('-saved_at')[:5]
        return [(s.article, list(s.article.interests.all())) for s in saved]
    except UserProfile.DoesNotExist:
        return []

async def favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать избранные статьи"""
    query = update.callback_query
    await query.answer()
    
    try:
        saved_articles = await get_user_favorites_with_tags(query.from_user.id)
        
        if not saved_articles:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
            await query.edit_message_text(
                "У вас пока нет избранных статей.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        message = "📚 Ваши избранные статьи:\n\n"
        for article, tags in saved_articles:
            message += f"📌 {article.title}\n"
            message += f"🔗 {article.url}\n"
            if tags:
                message += f"🏷 Теги: {', '.join(tag.name for tag in tags)}\n"
            message += "\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in favorites: {e}")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        await query.edit_message_text(
            "Произошла ошибка при получении избранных статей.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await get_or_create_user_profile(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("📰 Последние новости", callback_data='latest_news')],
        [InlineKeyboardButton("🏷 Теги", callback_data='tags')],
        [InlineKeyboardButton("⭐ Избранное", callback_data='favorites')],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для отслеживания новостей. Вот что я умею:\n\n"
        "📰 Показывать последние новости\n"
        "🏷 Фильтровать новости по тегам\n"
        "⭐ Сохранять избранные статьи\n"
        "⚙️ Настраивать предпочтения\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def latest_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает последние новости"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Latest news requested by user {query.from_user.id}")
    
    articles = await get_latest_articles_with_tags()
    
    if not articles:
        await query.message.reply_text("😕 К сожалению, новостей пока нет.")
        return
    
    for article in articles:
        keyboard = [
            [InlineKeyboardButton("⭐️ Добавить в избранное", callback_data=f'favorite_{article["id"]}')],
            [InlineKeyboardButton("🔗 Открыть статью", url=article["url"])]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"📰 *{article['title']}*\n\n"
        text += f"{article['content'][:200]}...\n\n"
        text += f"🏷 Теги: {', '.join(article['tags'])}\n"
        text += f"📅 {article['published_at'].strftime('%d.%m.%Y %H:%M')}"
        
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список доступных тегов"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Tags requested by user {query.from_user.id}")
    
    tags = await get_all_tags_list()
    keyboard = []
    
    # Создаем кнопки для каждого тега
    for tag in tags:
        keyboard.append([InlineKeyboardButton(tag['name'], callback_data=f'tag_{tag["id"]}')])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🏷 Выберите тег для просмотра новостей:",
        reply_markup=reply_markup
    )

async def show_tag_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает новости по выбранному тегу"""
    query = update.callback_query
    await query.answer()
    
    tag_id = query.data.split('_')[1]
    articles = await get_tag_articles_with_tags(tag_id)
    
    if not articles:
        await query.message.reply_text(f"😕 Новостей с этим тегом пока нет.")
        return
    
    for article in articles:
        keyboard = [
            [InlineKeyboardButton("⭐️ Добавить в избранное", callback_data=f'favorite_{article["id"]}')],
            [InlineKeyboardButton("🔗 Открыть статью", url=article["url"])]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"📰 *{article['title']}*\n\n"
        text += f"{article['content'][:200]}...\n\n"
        text += f"🏷 Теги: {', '.join(article['tags'])}\n"
        text += f"📅 {article['published_at'].strftime('%d.%m.%Y %H:%M')}"
        
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

@sync_to_async
def get_user_tags(telegram_id):
    """Получение тегов пользователя"""
    try:
        user_profile = UserProfile.objects.get(telegram_id=telegram_id)
        return list(user_profile.interests.all())
    except UserProfile.DoesNotExist:
        return []

@sync_to_async
def get_all_tags():
    """Получение всех доступных тегов"""
    return list(Interest.objects.all())

@sync_to_async
def toggle_user_tag(telegram_id, tag_id):
    """Добавление/удаление тега у пользователя"""
    try:
        user_profile = UserProfile.objects.get(telegram_id=telegram_id)
        tag = Interest.objects.get(id=tag_id)
        
        if tag in user_profile.interests.all():
            user_profile.interests.remove(tag)
            return False  # тег удален
        else:
            user_profile.interests.add(tag)
            return True  # тег добавлен
    except (UserProfile.DoesNotExist, Interest.DoesNotExist):
        return None

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает настройки пользователя"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🏷 Мои теги", callback_data='my_tags')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        "⚙️ Настройки\n\n"
        "Выберите раздел настроек:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает теги пользователя"""
    query = update.callback_query
    await query.answer()
    
    try:
        user_tags = await get_user_tags(query.from_user.id)
        all_tags = await get_all_tags()
        
        message = "🏷 Мои теги:\n\n"
        if user_tags:
            message += "Выбранные теги:\n"
            for tag in user_tags:
                message += f"✅ {tag.name}\n"
        else:
            message += "У вас пока нет выбранных тегов.\n"
        
        message += "\nДоступные теги:\n"
        for tag in all_tags:
            if tag in user_tags:
                message += f"✅ {tag.name}\n"
            else:
                message += f"❌ {tag.name}\n"
        
        # Создаем клавиатуру с кнопками для каждого тега
        keyboard = []
        for tag in all_tags:
            if tag in user_tags:
                keyboard.append([InlineKeyboardButton(f"❌ {tag.name}", callback_data=f'toggle_tag_{tag.id}')])
            else:
                keyboard.append([InlineKeyboardButton(f"✅ {tag.name}", callback_data=f'toggle_tag_{tag.id}')])
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='settings')])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in my_tags: {e}")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='settings')]]
        await query.edit_message_text(
            "Произошла ошибка при получении тегов.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def toggle_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление/удаление тега"""
    query = update.callback_query
    await query.answer()
    
    try:
        tag_id = query.data.split('_')[2]
        result = await toggle_user_tag(query.from_user.id, tag_id)
        
        if result is not None:
            # Обновляем список тегов
            await my_tags(update, context)
        else:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='settings')]]
            await query.edit_message_text(
                "Произошла ошибка при изменении тега.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Error in toggle_tag: {e}")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='settings')]]
        await query.edit_message_text(
            "Произошла ошибка при изменении тега.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📰 Последние новости", callback_data='latest_news')],
        [InlineKeyboardButton("🏷 Теги", callback_data='tags')],
        [InlineKeyboardButton("⭐️ Избранное", callback_data='favorites')],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )

def main():
    """Запуск бота"""
    global application
    
    # Проверяем, не запущен ли уже экземпляр бота
    if not acquire_lock():
        logger.error("Cannot start bot: another instance is already running")
        sys.exit(1)
    
    try:
        # Создаем приложение
        token = os.getenv('TELEGRAM_BOT_TOKEN', '8153321610:AAEQAJ7hp3S0-qzbT4COGAVPrMy19LskWoA')
        
        # Создаем и настраиваем приложение
        application = Application.builder().token(token).build()
        
        # Добавляем обработчики
        logger.info("Registering handlers...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(latest_news, pattern='^latest_news$'))
        application.add_handler(CallbackQueryHandler(show_tags, pattern='^tags$'))
        application.add_handler(CallbackQueryHandler(show_tag_news, pattern='^tag_'))
        application.add_handler(CallbackQueryHandler(favorites, pattern='^favorites$'))
        application.add_handler(CallbackQueryHandler(settings, pattern='^settings$'))
        application.add_handler(CallbackQueryHandler(my_tags, pattern='^my_tags$'))
        application.add_handler(CallbackQueryHandler(toggle_tag, pattern='^toggle_tag_'))
        application.add_handler(CallbackQueryHandler(add_to_favorites, pattern='^favorite_'))
        application.add_handler(CallbackQueryHandler(remove_from_favorites, pattern='^unfavorite_'))
        application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
        logger.info("Handlers registered successfully")
        
        # Запускаем бота
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Conflict as e:
        logger.error(f"Telegram API conflict: {e}")
        release_lock()
        sys.exit(1)
    except NetworkError as e:
        logger.error(f"Network error: {e}")
        release_lock()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        release_lock()
        sys.exit(1)

if __name__ == '__main__':
    main() 