from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from documents.models import Document


class Command(BaseCommand):
    help = 'Создаёт группу модераторов и назначает права (кастомные + для админки)'

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(Document)

        # 1. КАСТОМНЫЕ права (для API)
        custom_permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=[
                'can_approve_document',
                'can_reject_document',
                'can_view_all_documents',
            ]
        )

        # 2. СТАНДАРТНЫЕ права для админки
        admin_permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=[
                'view_document',    # видеть документы в админке
                'change_document',  # менять статус через actions
            ]
        )

        # Объединяем оба набора прав
        all_permissions = custom_permissions | admin_permissions

        # Создаём группу
        group, created = Group.objects.get_or_create(name='Document Moderator')
        group.permissions.set(all_permissions)

        self.stdout.write(self.style.SUCCESS(
            'Группа модераторов создана. Добавлены: кастомные права + view_document, change_document'
        ))