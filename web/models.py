from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    title = models.CharField(max_length=512)
    content = models.TextField()
    url = models.URLField(max_length=512)
    published_at = models.DateTimeField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    interests = models.ManyToManyField(Interest, blank=True)
    tags = models.JSONField(default=list, blank=True)  # Теги, определенные ML моделью
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

# избранное??
class SavedArticle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} - {self.article.title}"