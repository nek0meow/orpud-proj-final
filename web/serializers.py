from rest_framework import serializers
from .models import Interest, UserProfile, Article, Source

class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['id', 'name', 'description']

class UserProfileSerializer(serializers.ModelSerializer):
    interests = InterestSerializer(many=True, read_only=True)
    interests_ids = serializers.PrimaryKeyRelatedField(
        queryset=Interest.objects.all(), many=True, write_only=True, source='interests'
    )
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'interests', 'interests_ids', 'custom_tags']
        read_only_fields = ['user', 'interests']

class ArticleSerializer(serializers.ModelSerializer):
    source = serializers.StringRelatedField()
    interests = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['title', 'content', 'source', 'published_at', 'url', 'interests']

    def get_interests(self, obj):
        # Пока возвращаем пустой список, позже будет заполняться ML моделью
        return [] 