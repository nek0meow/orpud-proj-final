from django.contrib import admin
from .models import UserProfile, Interest, Source, Article, SavedArticle, UserInteraction, Category

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_interests', 'get_custom_tags')
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('interests',)
    readonly_fields = ('user',)

    def get_interests(self, obj):
        return ", ".join([interest.name for interest in obj.interests.all()])
    get_interests.short_description = 'Interests'

    def get_custom_tags(self, obj):
        return ", ".join(obj.custom_tags) if obj.custom_tags else "-"
    get_custom_tags.short_description = 'Custom Tags'

@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'link', 'source_type', 'last_parsed')
    list_filter = ('source_type',)
    search_fields = ('name', 'link')
    readonly_fields = ('last_parsed',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'category', 'published_at', 'get_interests', 'created_at', 'updated_at')
    list_filter = ('source', 'category', 'published_at', 'created_at')
    search_fields = ('title', 'content', 'url')
    filter_horizontal = ('interests',)
    date_hierarchy = 'published_at'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'content', 'url', 'source', 'category')
        }),
        ('Метаданные', {
            'fields': ('published_at', 'interests', 'tags')
        }),
        ('Системные поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_interests(self, obj):
        return ", ".join([interest.name for interest in obj.interests.all()])
    get_interests.short_description = 'Interests'

@admin.register(SavedArticle)
class SavedArticleAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__username', 'article__title')
    readonly_fields = ('saved_at',)

@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'interaction_type', 'interaction_time', 'duration', 'score')
    list_filter = ('interaction_type', 'interaction_time')
    search_fields = ('user__username', 'article__title')
    readonly_fields = ('interaction_time',)
