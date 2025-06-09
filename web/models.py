from django.contrib.auth import get_user_model
from django.db import models

# Create your models here.
User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=128)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferences = models.ManyToManyField(Category)

class Source(models.Model):
    name = models.CharField(max_length=128)
    link = models.CharField(max_length=256)

class Article(models.Model):
    name = models.CharField(max_length=512)
    date = models.DateField()
    link = models.CharField(512)
    source = models.ForeignKey(
        Source, on_delete= models.CASCADE
    )
    category = models.ForeignKey(
        Category, on_delete= models.CASCADE
    )

# избранное??
class SavedArticle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

class UserInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=50)  # 'view', 'read', 'click', etc.
    interaction_time = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField(default=0)  # Time spent in seconds
    score = models.FloatField(default=0.0)  # Calculated interest score