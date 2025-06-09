from django.core.management.base import BaseCommand
from web.models import Article, Source

class Command(BaseCommand):
    help = 'Show statistics about articles in database'

    def handle(self, *args, **options):
        self.stdout.write(f"Всего статей: {Article.objects.count()}")
        self.stdout.write("По источникам:")
        for source in Source.objects.all():
            count = Article.objects.filter(source=source).count()
            self.stdout.write(f"{source.name}: {count}") 