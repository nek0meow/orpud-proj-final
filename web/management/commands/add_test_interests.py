from django.core.management.base import BaseCommand
from web.models import Interest

class Command(BaseCommand):
    help = 'Adds test interests to the database'

    def handle(self, *args, **kwargs):
        # List of test interests
        test_interests = [
            'Technology',
            'Science',
            'Business',
            'Politics',
            'Sports',
            'Entertainment',
            'Health',
            'Environment',
            'Education',
            'Travel',
            'Food',
            'Art',
            'Music',
            'Fashion',
            'Gaming'
        ]

        # Create interests if they don't exist
        for interest_name in test_interests:
            Interest.objects.get_or_create(name=interest_name)
            self.stdout.write(self.style.SUCCESS(f'Successfully added interest: {interest_name}')) 