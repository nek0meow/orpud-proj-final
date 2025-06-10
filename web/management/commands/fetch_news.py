from django.core.management.base import BaseCommand
from web.news_fetcher import NewsFetcher

class Command(BaseCommand):
    help = 'Fetches news from configured APIs'

    def handle(self, *args, **options):
        self.stdout.write('Starting news fetch...')
        
        fetcher = NewsFetcher()
        fetcher.fetch_all_news()
        
        self.stdout.write(self.style.SUCCESS('Successfully fetched news from all APIs')) 