from django.core.management.base import BaseCommand
from web.telegram_bot import main
import sys

class Command(BaseCommand):
    help = 'Запускает Telegram бота'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Запуск Telegram бота...'))
        try:
            main()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Бот остановлен пользователем'))
            sys.exit(0)
        except Exception as e:
            if "another instance is already running" in str(e).lower():
                self.stdout.write(self.style.ERROR('Бот уже запущен в другом процессе'))
            else:
                self.stdout.write(self.style.ERROR(f'Ошибка при запуске бота: {e}'))
            sys.exit(1) 