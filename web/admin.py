from django.contrib import admin
from .models import UserProfile, Interest, Source, Article, SavedArticle

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_interests')
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('interests',)

    def get_interests(self, obj):
        return ", ".join([interest.name for interest in obj.interests.all()])
    get_interests.short_description = 'Interests'

@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'link', 'is_active', 'last_parsed')
    list_filter = ('is_active',)
    search_fields = ('name', 'link')

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_at', 'get_interests')
    list_filter = ('source', 'published_at')
    search_fields = ('title', 'content')
    filter_horizontal = ('interests',)
    date_hierarchy = 'published_at'

    def get_interests(self, obj):
        return ", ".join([interest.name for interest in obj.interests.all()])
    get_interests.short_description = 'Interests'

@admin.register(SavedArticle)
class SavedArticleAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__username', 'article__title')
