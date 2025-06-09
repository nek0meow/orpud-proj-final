import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aggregator_super.settings')
django.setup()

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from django.conf import settings
from web.models import Article, Interest, UserProfile, SavedArticle
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
def get_or_create_user_profile(user_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
        return user_profile
    except UserProfile.DoesNotExist:
        username = f"telegram_{user_id}"
        try:
            user = User.objects.get(username=username)
            # Проверяем, нет ли уже профиля с этим пользователем
            try:
                user_profile = UserProfile.objects.get(user=user)
                # Если есть, обновляем telegram_id
                user_profile.telegram_id = user_id
                user_profile.save()
                return user_profile
            except UserProfile.DoesNotExist:
                pass
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=None)
        user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
        return user_profile

@sync_to_async
def add_favorite(user_id, article_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
    except UserProfile.DoesNotExist:
        username = f"telegram_{user_id}"
        try:
            user = User.objects.get(username=username)
            try:
                user_profile = UserProfile.objects.get(user=user)
                user_profile.telegram_id = user_id
                user_profile.save()
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=None)
            user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
    article = Article.objects.get(id=article_id)
    SavedArticle.objects.get_or_create(user=user_profile, article=article)

@sync_to_async
def remove_favorite(user_id, article_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
    except UserProfile.DoesNotExist:
        username = f"telegram_{user_id}"
        try:
            user = User.objects.get(username=username)
            try:
                user_profile = UserProfile.objects.get(user=user)
                user_profile.telegram_id = user_id
                user_profile.save()
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=None)
            user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
    SavedArticle.objects.filter(user=user_profile, article_id=article_id).delete()

@sync_to_async
def get_user_favorites_with_tags(user_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
    except UserProfile.DoesNotExist:
        username = f"telegram_{user_id}"
        try:
            user = User.objects.get(username=username)
            try:
                user_profile = UserProfile.objects.get(user=user)
                user_profile.telegram_id = user_id
                user_profile.save()
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=None)
            user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
    saved = SavedArticle.objects.filter(user=user_profile).order_by('-saved_at')[:5]
    result = []
    for s in saved:
        article = s.article
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

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("📰 Последние новости", callback_data='latest_news')],
        [InlineKeyboardButton("🏷 Теги", callback_data='tags')],
        [InlineKeyboardButton("⭐ Избранное", callback_data='favorites')],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Я бот для чтения новостей.\n\n"
        "Что я умею:\n"
        "• Показывать последние новости\n"
        "• Фильтровать по тегам\n"
        "• Сохранять избранные статьи\n"
        "• Настраивать уведомления\n\n"
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
            [InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f'favorite_{article["id"]}')],
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
            [InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f'favorite_{article["id"]}')],
            [InlineKeyboardButton("🔗 Открыть статью", url=article["url"])]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"📰 *{article['title']}*\n\n"
        text += f"{article['content'][:200]}...\n\n"
        text += f"🏷 Теги: {', '.join(article['tags'])}\n"
        text += f"📅 {article['published_at'].strftime('%d.%m.%Y %H:%M')}"
        
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает избранные статьи пользователя"""
    query = update.callback_query
    await query.answer()
    
    saved_articles = await get_user_favorites_with_tags(query.from_user.id)
    
    if not saved_articles:
        await query.message.reply_text("😕 У вас пока нет избранных статей.")
        return
    
    for article in saved_articles:
        keyboard = [
            [InlineKeyboardButton("❌ Удалить из избранного", callback_data=f'unfavorite_{article["id"]}')],
            [InlineKeyboardButton("🔗 Открыть статью", url=article["url"])]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"📰 *{article['title']}*\n\n"
        text += f"{article['content'][:200]}...\n\n"
        text += f"🏷 Теги: {', '.join(article['tags'])}\n"
        text += f"📅 {article['published_at'].strftime('%d.%m.%Y %H:%M')}"
        
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает настройки пользователя"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔔 Уведомления", callback_data='notifications')],
        [InlineKeyboardButton("🏷 Мои теги", callback_data='my_tags')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "⚙️ Настройки:\n\n"
        "• Настройте уведомления\n"
        "• Выберите интересующие теги\n"
        "• Управляйте подписками",
        reply_markup=reply_markup
    )

async def add_to_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет статью в избранное"""
    query = update.callback_query
    await query.answer()
    
    article_id = query.data.split('_')[1]
    await add_favorite(query.from_user.id, article_id)
    
    await query.message.reply_text("✅ Статья добавлена в избранное!")

async def remove_from_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет статью из избранного"""
    query = update.callback_query
    await query.answer()
    
    article_id = query.data.split('_')[1]
    await remove_favorite(query.from_user.id, article_id)
    
    await query.message.reply_text("✅ Статья удалена из избранного!")

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📰 Последние новости", callback_data='latest_news')],
        [InlineKeyboardButton("🏷 Теги", callback_data='tags')],
        [InlineKeyboardButton("⭐ Избранное", callback_data='favorites')],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )

def main():
    """Запуск бота"""
    # Создаем приложение
    token = os.getenv('TELEGRAM_BOT_TOKEN', '8153321610:AAEQAJ7hp3S0-qzbT4COGAVPrMy19LskWoA')
    application = Application.builder().token(token).build()
    
    # Добавляем обработчики
    logger.info("Registering handlers...")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(latest_news, pattern='^latest_news$'))
    application.add_handler(CallbackQueryHandler(show_tags, pattern='^tags$'))
    application.add_handler(CallbackQueryHandler(show_tag_news, pattern='^tag_'))
    application.add_handler(CallbackQueryHandler(favorites, pattern='^favorites$'))
    application.add_handler(CallbackQueryHandler(settings, pattern='^settings$'))
    application.add_handler(CallbackQueryHandler(add_to_favorites, pattern='^favorite_'))
    application.add_handler(CallbackQueryHandler(remove_from_favorites, pattern='^unfavorite_'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    logger.info("Handlers registered successfully")
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main() 