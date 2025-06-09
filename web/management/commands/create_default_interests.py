from django.core.management.base import BaseCommand
from web.models import Interest

class Command(BaseCommand):
    help = 'Creates default interests'

    def handle(self, *args, **kwargs):
        # Сначала удалим все существующие интересы
        Interest.objects.all().delete()
        
        interests = [
            {'name': 'technology', 'description': 'Technology and IT news'},
            {'name': 'science', 'description': 'Scientific discoveries and research'},
            {'name': 'business', 'description': 'Business and economy news'},
            {'name': 'sports', 'description': 'Sports news and events'},
            {'name': 'entertainment', 'description': 'Entertainment and celebrity news'},
            {'name': 'health', 'description': 'Health and medical news'},
            {'name': 'politics', 'description': 'Political news and events'},
            {'name': 'environment', 'description': 'Environmental news and climate'},
            {'name': 'education', 'description': 'Education and learning news'},
            {'name': 'travel', 'description': 'Travel and tourism news'},
            {'name': 'food', 'description': 'Food and culinary news'},
            {'name': 'fashion', 'description': 'Fashion and style news'},
            {'name': 'art', 'description': 'Art and culture news'},
            {'name': 'gaming', 'description': 'Gaming and esports news'},
            {'name': 'automotive', 'description': 'Automotive and car news'}
        ]

        for interest in interests:
            Interest.objects.get_or_create(
                name=interest['name'],
                defaults={'description': interest['description']}
            )
            self.stdout.write(f'Created interest: {interest["name"]}') 