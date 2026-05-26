import os
from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = "Создаёт суперпользователя из переменных окружения, если его нет"

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        first_name = os.environ.get("DJANGO_SUPERUSER_FIRST_NAME")
        last_name = os.environ.get("DJANGO_SUPERUSER_LAST_NAME")

        if not all([email, password, first_name, last_name]):
            self.stdout.write("Не все переменные окружения заданы")
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Суперпользователь {email} уже существует")
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        self.stdout.write(f"Суперпользователь {email} создан")