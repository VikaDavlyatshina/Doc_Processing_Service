from documents.serializers import DocumentSerializer

from .tasks import (notify_admin_new_document, notify_user_document_approved,
                    notify_user_document_rejected)


def replace_document_file(document, new_file, user):
    """
    Заменяет файл документа и отправляет его на повторную проверку.
    Статус становится 'pending'.
    """
    # Сохраняем исходный статус для истории
    old_status = document.status

    # Обновляем файл и отправляем на проверку
    document.file = new_file
    document.status = "pending"

    # Сбрасываем старые данные модерации
    document.reviewed_by = None
    document.reviewed_at = None
    document.comment = ""

    # Сохраняем изменения
    document.save()

    # Записываем действие в историю изменений
    document.log_action(
        user=user, action="file_updated", old_status=old_status, new_status="pending"
    )

    # Отправляем сообщение админу о новом документе
    notify_admin_new_document.delay(document.id)

    # Возвращаем полные данные документа
    serializer = DocumentSerializer(document)
    return serializer.data


def send_document_to_review(document, user):
    """
    Отправляет черновик на проверку модератору.
    Статус меняется с 'draft' на 'pending'.
    """
    # Сохраняем исходный статус для истории
    old_status = document.status

    # Меняем статус
    document.status = "pending"
    document.save()

    # Логируем
    document.log_action(
        user=user, action="submitted", old_status=old_status, new_status="pending"
    )

    # Отправляем уведомление админу о новом документе
    notify_admin_new_document.delay(document.id)

    # Возвращаем полные данные документа
    serializer = DocumentSerializer(document)
    return serializer.data


def approve_document(document, moderator):
    """
    Подтверждает документ. Статус становится 'approved'.
    """

    # Вызываем метод модели
    document.approve(moderator=moderator)

    # Отправляем уведомление пользователю о подтверждении
    notify_user_document_approved.delay(document.id)

    # Возвращаем полные данные документа
    serializer = DocumentSerializer(document)
    return serializer.data


def reject_document(document, moderator, comment):
    """
    Отклоняет документ с указанием причины.
    Статус становится 'rejected'.
    """

    # Вызываем метод модели
    document.reject(moderator=moderator, comment=comment)

    # Отправляем уведомление пользователю об отклонении
    notify_user_document_rejected.delay(document.id)

    # Возвращаем полные данные документа
    serializer = DocumentSerializer(document)
    return serializer.data
