from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from users.models import User


class Command(BaseCommand):
    help = "Создаёт группу менеджеров пользователей"

    def handle(self, *args, **options):
        user_ct = ContentType.objects.get_for_model(User)
        permissions = Permission.objects.filter(
            content_type=user_ct,
            codename__in=[
                "view_user",      # просмотр
                "change_user",    # изменение (для восстановления)
            ],
        )

        group, created = Group.objects.get_or_create(name="User Manager")
        group.permissions.set(permissions)

        self.stdout.write(self.style.SUCCESS(
            f"Группа 'User Manager' {'создана' if created else 'обновлена'}"
        ))