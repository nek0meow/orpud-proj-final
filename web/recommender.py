from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Article, UserProfile, UserInteraction

class NewsRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )

    def _get_user_interests(self, user):
        """Get user interests from profile and interactions"""
        interests = []
        
        # Get explicit interests from profile
        if hasattr(user, 'profile'):
            profile = user.profile
            interests.extend(profile.interests.values_list('name', flat=True))
            interests.extend(profile.custom_tags)
        
        # Get implicit interests from interactions
        interactions = UserInteraction.objects.filter(user=user)
        for interaction in interactions:
            if interaction.score > 0.5:  # Only consider positive interactions
                interests.extend(interaction.article.tags)
        
        return list(set(interests))  # Remove duplicates

    def _get_article_features(self, articles):
        """Extract features from articles for similarity comparison"""
        texts = []
        for article in articles:
            # Combine title, content, and tags for better feature extraction
            article_tags = ' '.join(article.interests.values_list('name', flat=True))
            text = f"{article.title} {article.content} {article_tags}"
            texts.append(text)
        
        # Fit and transform the vectorizer on all articles
        return self.vectorizer.fit_transform(texts)

    def get_recommendations(self, user, limit=10):
        """Get personalized news recommendations for a user"""
        # Get user interests
        user_interests = self._get_user_interests(user)
        
        # Get all articles
        articles = list(Article.objects.all())  # Convert QuerySet to list
        
        if not articles:
            return []
        
        # Get article features
        article_features = self._get_article_features(articles)
        
        # If user has interests, calculate similarity
        if user_interests:
            # Create a document from user interests
            user_doc = ' '.join(user_interests)
            # Transform user interests using the same vectorizer
            user_features = self.vectorizer.transform([user_doc])
            
            # Calculate similarity scores
            similarity_scores = cosine_similarity(user_features, article_features).flatten()
            
            # Normalize similarity scores to 0-1 range
            if similarity_scores.max() > 0:
                similarity_scores = similarity_scores / similarity_scores.max()
        else:
            # If no interests, use recency as the main factor
            similarity_scores = np.zeros(len(articles))
        
        # Add recency factor
        now = timezone.now()
        for i, article in enumerate(articles):
            # Ensure article.published_at is timezone-aware
            if timezone.is_naive(article.published_at):
                article.published_at = timezone.make_aware(article.published_at)
            
            # Calculate recency score (higher for newer articles)
            days_old = (now - article.published_at).days
            recency_score = 1.0 / (1.0 + days_old)
            
            # Calculate interest match score
            article_interests = set(article.interests.values_list('name', flat=True))
            user_interest_set = set(user_interests)
            interest_match = len(article_interests.intersection(user_interest_set)) / max(len(user_interest_set), 1)
            
            # Combine all factors
            if user_interests:
                # 50% content similarity, 30% interest match, 20% recency
                similarity_scores[i] = 0.5 * similarity_scores[i] + 0.3 * interest_match + 0.2 * recency_score
            else:
                similarity_scores[i] = recency_score
        
        # Get top recommendations
        top_indices = similarity_scores.argsort()[-limit:][::-1]
        recommendations = []
        
        for idx in top_indices:
            article = articles[int(idx)]  # Convert numpy.int64 to Python int
            recommendations.append({
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'url': article.url,
                'source': article.source.name,
                'published_at': article.published_at,
                'score': float(similarity_scores[idx])
            })
        
        return recommendations 