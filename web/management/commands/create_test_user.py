from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from web.models import UserProfile, Interest

class Command(BaseCommand):
    help = 'Creates a test user with interests'

    def handle(self, *args, **kwargs):
        # Create test user
        username = 'testuser'
        password = 'testpass123'
        email = 'test@example.com'

        # Create user if doesn't exist
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True
            }
        )
        
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created test user: {username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Test user already exists: {username}'))

        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Add some interests
        interests = Interest.objects.filter(name__in=['Technology', 'Science', 'Business', 'Politics'])
        profile.interests.set(interests)
        
        # Add some custom tags
        profile.custom_tags = ['AI', 'Machine Learning', 'Data Science']
        profile.save()

        self.stdout.write(self.style.SUCCESS(f'Added interests to test user: {", ".join(i.name for i in interests)}'))
        self.stdout.write(self.style.SUCCESS(f'Added custom tags: {", ".join(profile.custom_tags)}'))
        self.stdout.write(self.style.SUCCESS(f'Test user credentials - Username: {username}, Password: {password}')) 