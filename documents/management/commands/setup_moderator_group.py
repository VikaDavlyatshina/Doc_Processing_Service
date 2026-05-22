from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from documents.models import Document, DocumentLog


class Command(BaseCommand):
    help = "Создаёт группу модераторов и назначает права"

    def handle(self, *args, **options):
        # ================================================================
        # ПРАВА НА ДОКУМЕНТЫ
        # ================================================================
        doc_ct = ContentType.objects.get_for_model(Document)
        doc_perms = Permission.objects.filter(
            content_type=doc_ct,
            codename__in=[
                "can_approve_document",
                "can_reject_document",
                "can_view_all_documents",
                "view_document",
                "change_document",
            ],
        )

        # ================================================================
        # ПРАВА НА ИСТОРИЮ ДОКУМЕНТОВ (только просмотр)
        # ================================================================
        log_ct = ContentType.objects.get_for_model(DocumentLog)
        log_perms = Permission.objects.filter(
            content_type=log_ct,
            codename__in=[
                "view_documentlog",  # только просмотр истории
            ],
        )

        # ================================================================
        # ПРАВА НА ПОЛЬЗОВАТЕЛЕЙ (только просмотр)
        # ================================================================
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_ct = ContentType.objects.get_for_model(User)
        user_perms = Permission.objects.filter(
            content_type=user_ct,
            codename__in=[
                "view_user",  # только просмотр
            ],
        )

        # Объединяем все права
        all_permissions = doc_perms | log_perms | user_perms

        # Создаём/обновляем группу
        group, created = Group.objects.get_or_create(name="Document Moderator")
        group.permissions.set(all_permissions)

        self.stdout.write(self.style.SUCCESS(
            f"Группа {'создана' if created else 'обновлена'}. "
            f"Назначено {all_permissions.count()} прав."
        ))