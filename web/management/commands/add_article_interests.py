from django.core.management.base import BaseCommand
from web.models import Article, Interest
import random

class Command(BaseCommand):
    help = 'Adds random interests to existing articles'

    def handle(self, *args, **kwargs):
        # Get all articles and interests
        articles = Article.objects.all()
        interests = list(Interest.objects.all())

        if not interests:
            self.stdout.write(self.style.ERROR('No interests found. Please run add_test_interests first.'))
            return

        # Add 2-4 random interests to each article
        for article in articles:
            # Clear existing interests
            article.interests.clear()
            
            # Add 2-4 random interests
            num_interests = random.randint(2, 4)
            selected_interests = random.sample(interests, num_interests)
            
            for interest in selected_interests:
                article.interests.add(interest)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Added interests to article "{article.title}": {", ".join(i.name for i in selected_interests)}'
                )
            ) 