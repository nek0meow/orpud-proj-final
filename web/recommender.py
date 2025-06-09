from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Article, UserProfile, SavedArticle

class NewsRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )

    def _get_user_interests(self, user_profile):
        """Get user interests from profile and saved articles"""
        interests = []
        
        # Get explicit interests from profile
        interests.extend(user_profile.interests.values_list('name', flat=True))
        
        # Get implicit interests from saved articles
        saved_articles = SavedArticle.objects.filter(user=user_profile)
        for saved in saved_articles:
            interests.extend(saved.article.interests.values_list('name', flat=True))
        
        return list(set(interests))  # Remove duplicates

    def _get_article_features(self, articles):
        """Extract features from articles for similarity comparison"""
        texts = []
        for article in articles:
            # Combine title, content and tags for better feature extraction
            text = f"{article.title} {article.content}"
            tags = ' '.join(article.interests.values_list('name', flat=True))
            text = f"{text} {tags}"
            texts.append(text)
        
        return self.vectorizer.fit_transform(texts)

    def get_recommendations(self, user_profile, limit=10):
        """Get personalized news recommendations for a user"""
        # Get user interests
        user_interests = self._get_user_interests(user_profile)
        
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
            user_features = self.vectorizer.transform([user_doc])
            
            # Calculate similarity scores
            similarity_scores = cosine_similarity(user_features, article_features).flatten()
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
            
            # Combine similarity and recency scores
            similarity_scores[i] = 0.7 * similarity_scores[i] + 0.3 * recency_score
        
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
                'score': float(similarity_scores[idx]),
                'tags': list(article.interests.values_list('name', flat=True))
            })
        
        return recommendations 

    def get_article_score(self, user_profile, article):
        """Get relevance score for a single article"""
        # Get user interests
        user_interests = self._get_user_interests(user_profile)
        
        if not user_interests:
            return 0.0
        
        # Create a document from user interests
        user_doc = ' '.join(user_interests)
        user_features = self.vectorizer.transform([user_doc])
        
        # Create a document from article
        article_text = f"{article.title} {article.content}"
        article_tags = ' '.join(article.interests.values_list('name', flat=True))
        article_text = f"{article_text} {article_tags}"
        article_features = self.vectorizer.transform([article_text])
        
        # Calculate similarity score
        similarity_score = cosine_similarity(user_features, article_features)[0][0]
        
        # Add recency factor
        now = timezone.now()
        if timezone.is_naive(article.published_at):
            article.published_at = timezone.make_aware(article.published_at)
        
        days_old = (now - article.published_at).days
        recency_score = 1.0 / (1.0 + days_old)
        
        # Combine scores
        final_score = 0.7 * similarity_score + 0.3 * recency_score
        
        return float(final_score) 