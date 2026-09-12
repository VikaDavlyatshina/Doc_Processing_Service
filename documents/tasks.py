from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from documents.models import Document


@shared_task
def notify_admin_new_document(document_id):
    """Отправляет администратору уведомление о новом документе"""
    try:
        doc = Document.objects.get(id=document_id)
        subject = f"Новый документ на проверку #{doc.id}"
        message = f"""
Пользователь {doc.user.email} загрузил новый документ.

Комментарий: {doc.user_note}
Файл: {doc.file.name}
Загружен: {doc.uploaded_at}

Ссылка для просмотра: {settings.SITE_URL}/admin/documents/document/{doc.id}/change/
        """
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            # Если письмо не отправилось - пропускаем
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )

    # Если документа нет - пропускаем
    except Document.DoesNotExist:
        pass


@shared_task
def notify_user_document_approved(document_id):
    """Отправляет пользователю уведомление о подтверждении документа"""
    try:
        doc = Document.objects.get(id=document_id)
        subject = f"Ваш документ #{doc.id} подтверждён"
        message = f"""
Здравствуйте!

Ваш документ "{doc.user_note}" успешно проверен и подтверждён.

Статус: Подтверждён
Дата проверки: {doc.reviewed_at}

Спасибо за использование сервиса.
        """
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[doc.user.email],
            # Если письмо не отправилось - пропускаем
            fail_silently=True,
        )
    # Если документа нет - пропускаем
    except Document.DoesNotExist:
        pass


@shared_task
def notify_user_document_rejected(document_id):
    """Отправляет пользователю уведомление об отклонении документа"""
    try:
        doc = Document.objects.get(id=document_id)
        subject = f"Ваш документ #{doc.id} отклонён"
        message = f"""
Здравствуйте!

Ваш документ "{doc.user_note}" был отклонён.

Причина: {doc.comment}

Пожалуйста, исправьте замечания и загрузите документ заново.
        """
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[doc.user.email],
            fail_silently=True,
        )

    # Если документа нет - пропускаем
    except Document.DoesNotExist:
        pass


@shared_task
def check_overdue_documents():
    """Проверяет документы, ожидающие проверки больше 2 часов"""
    threshold = timezone.now() - timedelta(hours=2)
    overdue_docs = Document.objects.filter(status="pending", uploaded_at__lt=threshold)

    for doc in overdue_docs:
        subject = f"ВНИМАНИЕ: Документ #{doc.id} ожидает проверки более 2 часов"
        message = f"""
Документ #{doc.id} от пользователя {doc.user.email} ожидает проверки более 2 часов.

Комментарий: {doc.user_note}
Загружен: {doc.uploaded_at}
Ссылка для просмотра: {settings.SITE_URL}/admin/documents/document/{doc.id}/change/
        """
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )
