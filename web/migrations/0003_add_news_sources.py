from django.db import migrations

def add_news_sources(apps, schema_editor):
    Source = apps.get_model('web', 'Source')
    sources = [
        ('NewsAPI', 'https://newsapi.org', 'newsapi'),
        ('GNews', 'https://gnews.io', 'gnews'),
        ('Mediastack', 'https://mediastack.com', 'mediastack'),
        ('The Guardian', 'https://open-platform.theguardian.com', 'guardian'),
        ('Currents API', 'https://currentsapi.services', 'currents'),
    ]
    
    for name, link, source_type in sources:
        Source.objects.create(
            name=name,
            link=link,
            source_type=source_type,
            is_active=True
        )

def remove_news_sources(apps, schema_editor):
    Source = apps.get_model('web', 'Source')
    Source.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('web', '0002_source_api_key_source_source_type_alter_source_link'),
    ]

    operations = [
        migrations.RunPython(add_news_sources, remove_news_sources),
    ] 