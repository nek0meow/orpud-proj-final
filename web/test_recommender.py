import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime

class NewsRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.articles = []
        self.user_interests = set()
        
    def load_articles(self, json_file):
        """Load articles from JSON file"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.articles = data['articles']
            
    def set_user_interests(self, interests):
        """Set user's interests"""
        self.user_interests = set(interests)
        
    def _extract_features(self, articles):
        """Extract features from articles for similarity comparison"""
        texts = [f"{article['title']} {article['content']}" for article in articles]
        return self.vectorizer.fit_transform(texts)
    
    def get_recommendations(self, limit=10):
        """Get personalized news recommendations"""
        if not self.articles:
            return []
            
        # Get article features
        features = self._extract_features(self.articles)
        
        # Calculate similarity scores
        similarity_matrix = cosine_similarity(features)
        
        # Get top recommendations
        article_scores = []
        for i, article in enumerate(self.articles):
            # Calculate average similarity with other articles
            avg_similarity = np.mean(similarity_matrix[i])
            
            # Add recency factor (articles from last 24 hours get a boost)
            published_at = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
            hours_old = (datetime.now(published_at.tzinfo) - published_at).total_seconds() / 3600
            recency_factor = 1.0 if hours_old <= 24 else 0.5
            
            final_score = avg_similarity * recency_factor
            article_scores.append((article, final_score))
            
        # Sort by score and return top recommendations
        article_scores.sort(key=lambda x: x[1], reverse=True)
        recommendations = article_scores[:limit]
        
        # Format results
        return [{
            'header': article['title'],
            'source': article['source'],
            'url': article['url'],
            'published_at': article['published_at'],
            'score': float(score)
        } for article, score in recommendations]

def test_recommender():
    # Initialize recommender
    recommender = NewsRecommender()
    
    # Load sample data
    recommender.load_articles('ratmir_not_gpt.json')
    
    # Set some example user interests
    recommender.set_user_interests(['technology', 'politics', 'business'])
    
    # Get recommendations
    recommendations = recommender.get_recommendations(limit=5)
    
    # Print results
    print("\nRecommended Articles:")
    print("====================")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['header']}")
        print(f"   Source: {rec['source']}")
        print(f"   Score: {rec['score']:.2f}")
        print(f"   URL: {rec['url']}")

if __name__ == "__main__":
    test_recommender() 