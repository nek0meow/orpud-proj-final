from django.core.management.base import BaseCommand
from web.models import Source
from web.parsers import PARSERS
from datetime import datetime

class Command(BaseCommand):
    help = 'Fetch news from all configured sources'

    def handle(self, *args, **options):
        sources = Source.objects.filter(is_active=True)
        for source in sources:
            try:
                parser_class = PARSERS.get(source.source_type)
                if parser_class:
                    parser = parser_class(source)
                    parser.parse()
                    source.last_parsed = datetime.now()
                    source.save()
                    self.stdout.write(self.style.SUCCESS(f'Successfully parsed {source.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'No parser found for {source.name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error parsing {source.name}: {str(e)}')) 