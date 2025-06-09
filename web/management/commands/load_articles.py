import json
from django.core.management.base import BaseCommand
from web.models import Article, Source, Category
from datetime import datetime

class Command(BaseCommand):
    help = 'Load articles from JSON file'

    def handle(self, *args, **options):
        # Create default source if it doesn't exist
        source, _ = Source.objects.get_or_create(
            name='Currents API',
            defaults={
                'link': 'https://currentsapi.services/',
                'source_type': 'currents'
            }
        )

        # Create default category if it doesn't exist
        category, _ = Category.objects.get_or_create(
            name='General',
            defaults={'description': 'General news'}
        )

        # Read and process the JSON file
        with open('ratmir_not_gpt.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for article_data in data['articles']:
                # Convert published_at to datetime
                published_at = datetime.strptime(
                    article_data['published_at'], 
                    '%Y-%m-%dT%H:%M:%SZ'
                )

                # Create or update article
                article, created = Article.objects.update_or_create(
                    url=article_data['url'],
                    defaults={
                        'title': article_data['title'],
                        'content': article_data['content'],
                        'source': source,
                        'category': category,
                        'published_at': published_at
                    }
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created article: {article.title}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated article: {article.title}')
                    ) 