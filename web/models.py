from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import asyncio
from telegram import Bot
import os

# Create your models here.
User = get_user_model()

class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    interests = models.ManyToManyField(Interest, blank=True)
    custom_tags = models.JSONField(default=list, blank=True)  # Для пользовательских тегов
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    notifications_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Source(models.Model):
    name = models.CharField(max_length=128)
    link = models.URLField(max_length=1024)
    is_active = models.BooleanField(default=True)
    last_parsed = models.DateTimeField(null=True, blank=True)
    api_key = models.CharField(max_length=256, blank=True, null=True)
    source_type = models.CharField(max_length=50, default='newsapi')  # newsapi, gnews, mediastack, guardian, currents

    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=500)
    content = models.TextField()
    url = models.URLField(max_length=500)
    published_at = models.DateTimeField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    interests = models.ManyToManyField(Interest)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

async def send_notifications(article):
    """Отправляет уведомления о новой статье"""
    token = os.getenv('TELEGRAM_BOT_TOKEN', '8153321610:AAEQAJ7hp3S0-qzbT4COGAVPrMy19LskWoA')
    bot = Bot(token=token)
    
    # Получаем пользователей с включенными уведомлениями
    users = UserProfile.objects.filter(notifications_enabled=True)
    
    # Получаем теги статьи
    article_tags = set(article.interests.all())
    
    # Формируем сообщение
    message = (
        f"📰 *Новая статья по вашим интересам!*\n\n"
        f"*{article.title}*\n\n"
        f"{article.content[:200]}...\n\n"
        f"🏷 Теги: {', '.join([i.name for i in article_tags])}\n"
        f"🔗 [Читать статью]({article.url})"
    )
    
    # Отправляем уведомления только тем пользователям, у которых есть общие интересы со статьей
    for user_profile in users:
        if user_profile.telegram_id:
            # Получаем интересы пользователя
            user_interests = set(user_profile.interests.all())
            # Проверяем, есть ли общие интересы
            if user_interests & article_tags:  # Пересечение множеств
                try:
                    await bot.send_message(
                        chat_id=user_profile.telegram_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"Failed to send notification to user {user_profile.telegram_id}: {e}")

@receiver(post_save, sender=Article)
def notify_about_new_article(sender, instance, created, **kwargs):
    """Отправляет уведомления при создании новой статьи"""
    if created:
        asyncio.run(send_notifications(instance))

# избранное??
class SavedArticle(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.user.username} - {self.article.title}"