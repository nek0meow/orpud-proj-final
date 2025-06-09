from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .models import Article, UserProfile, UserInteraction, Category

class NewsRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
    def _get_user_interests(self, user):
        """Get user's interests based on their profile and interactions"""
        # Get explicit preferences
        preferences = UserProfile.objects.get(user=user).preferences.all()
        preference_categories = [cat.name for cat in preferences]
        
        # Get implicit preferences from interactions
        interactions = UserInteraction.objects.filter(user=user)
        interaction_scores = {}
        
        for interaction in interactions:
            category = interaction.article.category.name
            if category not in interaction_scores:
                interaction_scores[category] = 0
            interaction_scores[category] += interaction.score
            
        # Combine explicit and implicit preferences
        interests = set(preference_categories)
        for category, score in interaction_scores.items():
            if score > 0.5:  # Threshold for considering implicit interest
                interests.add(category)
                
        return list(interests)
    
    def _get_article_features(self, articles):
        """Extract features from articles for similarity comparison"""
        texts = [f"{article.name} {article.category.name}" for article in articles]
        return self.vectorizer.fit_transform(texts)
    
    def get_recommendations(self, user, limit=10):
        """Get personalized news recommendations for a user"""
        # Get user interests
        user_interests = self._get_user_interests(user)
        
        # Get all articles
        articles = Article.objects.all()
        
        # Filter articles by user interests
        relevant_articles = [
            article for article in articles 
            if article.category.name in user_interests
        ]
        
        if not relevant_articles:
            return []
            
        # Get article features
        features = self._get_article_features(relevant_articles)
        
        # Calculate similarity scores
        similarity_matrix = cosine_similarity(features)
        
        # Get top recommendations
        article_scores = []
        for i, article in enumerate(relevant_articles):
            # Calculate average similarity with other articles
            avg_similarity = np.mean(similarity_matrix[i])
            article_scores.append((article, avg_similarity))
            
        # Sort by score and return top recommendations
        article_scores.sort(key=lambda x: x[1], reverse=True)
        recommendations = article_scores[:limit]
        
        # Format results
        return [{
            'header': article.name,
            'category': article.category.name,
            'link': article.link,
            'date': article.date.isoformat(),
            'score': float(score)
        } for article, score in recommendations] 