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
from .recommender import NewsRecommender
import asyncio

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
            try:
                user_profile = UserProfile.objects.get(user=user)
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

@sync_to_async
def enable_notifications_for_user(user_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
    except UserProfile.DoesNotExist:
        username = f"telegram_{user_id}"
        try:
            user = User.objects.get(username=username)
            try:
                user_profile = UserProfile.objects.get(user=user)
                user_profile.telegram_id = user_id
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=None)
            user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
    user_profile.notifications_enabled = True
    user_profile.save()
    return user_profile

@sync_to_async
def disable_notifications_for_user(user_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
    except UserProfile.DoesNotExist:
        username = f"telegram_{user_id}"
        try:
            user = User.objects.get(username=username)
            try:
                user_profile = UserProfile.objects.get(user=user)
                user_profile.telegram_id = user_id
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=None)
            user_profile = UserProfile.objects.create(user=user, telegram_id=user_id)
    user_profile.notifications_enabled = False
    user_profile.save()
    return user_profile

@sync_to_async
def get_users_with_notifications():
    return UserProfile.objects.filter(notifications_enabled=True)

async def send_notification_to_user(bot, user_profile, message):
    """Отправляет уведомление пользователю"""
    try:
        await bot.send_message(
            chat_id=user_profile.telegram_id,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_profile.telegram_id}: {e}")

async def notify_users_about_new_article(bot, article):
    """Отправляет уведомление всем пользователям с включенными уведомлениями о новой статье"""
    users = await get_users_with_notifications()
    message = (
        f"📰 *Новая статья!*\n\n"
        f"*{article.title}*\n\n"
        f"{article.content[:200]}...\n\n"
        f"🏷 Теги: {', '.join([i.name for i in article.interests.all()])}\n"
        f"🔗 [Читать статью]({article.url})"
    )
    for user_profile in users:
        await send_notification_to_user(bot, user_profile, message)

@sync_to_async
def get_user_interests(user_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
        return list(user_profile.interests.all())
    except UserProfile.DoesNotExist:
        return []

@sync_to_async
def get_all_interests():
    return list(Interest.objects.all())

@sync_to_async
def add_interest_to_user(user_id, interest_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
        interest = Interest.objects.get(id=interest_id)
        user_profile.interests.add(interest)
        return True
    except (UserProfile.DoesNotExist, Interest.DoesNotExist):
        return False

@sync_to_async
def remove_interest_from_user(user_id, interest_id):
    try:
        user_profile = UserProfile.objects.get(telegram_id=user_id)
        interest = Interest.objects.get(id=interest_id)
        user_profile.interests.remove(interest)
        return True
    except (UserProfile.DoesNotExist, Interest.DoesNotExist):
        return False

async def my_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает теги пользователя и позволяет их редактировать"""
    query = update.callback_query
    await query.answer()
    
    # Получаем все доступные теги
    all_interests = await get_all_interests()
    # Получаем теги пользователя
    user_interests = await get_user_interests(query.from_user.id)
    user_interest_ids = {i.id for i in user_interests}
    
    # Создаем кнопки для каждого тега
    keyboard = []
    for interest in all_interests:
        if interest.id in user_interest_ids:
            # Если тег уже выбран, добавляем кнопку для удаления
            keyboard.append([InlineKeyboardButton(f"❌ {interest.name}", callback_data=f'remove_interest_{interest.id}')])
        else:
            # Если тег не выбран, добавляем кнопку для добавления
            keyboard.append([InlineKeyboardButton(f"➕ {interest.name}", callback_data=f'add_interest_{interest.id}')])
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='settings')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🏷 Ваши интересы:\n\n"
        "Выберите теги, которые вас интересуют.\n"
        "Вы будете получать уведомления только о статьях с этими тегами.",
        reply_markup=reply_markup
    )

async def add_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет тег в интересы пользователя"""
    query = update.callback_query
    await query.answer()
    
    interest_id = query.data.split('_')[2]
    success = await add_interest_to_user(query.from_user.id, interest_id)
    
    if success:
        await my_tags(update, context)  # Обновляем список тегов
    else:
        await query.message.reply_text("❌ Не удалось добавить тег. Попробуйте позже.")

async def remove_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет тег из интересов пользователя"""
    query = update.callback_query
    await query.answer()
    
    interest_id = query.data.split('_')[2]
    success = await remove_interest_from_user(query.from_user.id, interest_id)
    
    if success:
        await my_tags(update, context)  # Обновляем список тегов
    else:
        await query.message.reply_text("❌ Не удалось удалить тег. Попробуйте позже.")

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

async def notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает настройки уведомлений"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔔 Включить уведомления", callback_data='enable_notifications')],
        [InlineKeyboardButton("🔕 Отключить уведомления", callback_data='disable_notifications')],
        [InlineKeyboardButton("◀️ Назад", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🔔 Настройки уведомлений:\n\n"
        "• Получать уведомления о новых статьях\n"
        "• Получать уведомления о важных новостях\n"
        "• Получать уведомления о сохраненных статьях",
        reply_markup=reply_markup
    )

async def enable_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включает уведомления"""
    query = update.callback_query
    await query.answer()
    
    user_profile = await enable_notifications_for_user(query.from_user.id)
    
    await query.message.edit_text(
        "✅ Уведомления включены!\n\n"
        "Вы будете получать уведомления о:\n"
        "• Новых статьях\n"
        "• Важных новостях\n"
        "• Сохраненных статьях"
    )

async def disable_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключает уведомления"""
    query = update.callback_query
    await query.answer()
    
    user_profile = await disable_notifications_for_user(query.from_user.id)
    
    await query.message.edit_text(
        "✅ Уведомления отключены!\n\n"
        "Вы больше не будете получать уведомления."
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

async def get_recommendations(update, context):
    """Получает рекомендации статей для пользователя"""
    try:
        # Получаем профиль пользователя
        user_profile = UserProfile.objects.get(telegram_id=update.effective_user.id)
        
        # Получаем рекомендации
        recommender = NewsRecommender()
        recommendations = recommender.get_recommendations(user_profile)
        
        if not recommendations:
            await update.message.reply_text("К сожалению, не удалось найти статьи по вашим интересам 😔")
            return
        
        # Отправляем рекомендации
        for article in recommendations:
            message = (
                f"📰 *{article['title']}*\n\n"
                f"{article['content'][:200]}...\n\n"
                f"🏷 Теги: {', '.join(article['tags'])}\n"
                f"📅 Опубликовано: {article['published_at'].strftime('%d.%m.%Y %H:%M')}\n"
                f"🔗 [Читать статью]({article['url']})"
            )
            
            await update.message.reply_text(
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Небольшая задержка между сообщениями
            await asyncio.sleep(1)
    
    except UserProfile.DoesNotExist:
        await update.message.reply_text("Пожалуйста, сначала выберите свои интересы в настройках.")
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        await update.message.reply_text("Произошла ошибка при получении рекомендаций 😔")

def main():
    """Запускает бота"""
    # Создаем приложение
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN', '8153321610:AAEQAJ7hp3S0-qzbT4COGAVPrMy19LskWoA')).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("my_tags", my_tags))
    application.add_handler(CommandHandler("add_interest", add_interest))
    application.add_handler(CommandHandler("remove_interest", remove_interest))
    application.add_handler(CommandHandler("recommend", get_recommendations))
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main() 