from django.core.exceptions import ValidationError


# ============================================================
# 1. Проверка статуса документа
# ============================================================

def validate_document_status(document, expected_status):
    """
    Проверяет, что документ находится в ожидаемом статусе.
    Если нет — выбрасывает ValidationError.
    """
    if document.status != expected_status:
        raise ValidationError(
            f'Документ уже в статусе: {document.get_status_display()}'
        )


# ============================================================
# 2. Замена файла владельцем
# ============================================================

def replace_document_file(document, new_file, user):
    """
    Заменяет файл документа и отправляет его на повторную проверку.
    Статус становится 'pending'.
    """
    # Сохраняем исходный статус для истории
    old_status = document.status

    # Обновляем файл и отправляем на проверку
    document.file = new_file
    document.status = 'pending'

    # Сбрасываем старые данные модерации
    document.reviewed_by = None
    document.reviewed_at = None
    document.comment = ''

    # Сохраняем изменения
    document.save()

    # Записываем действие в историю изменений
    document.log_action(
        user=user,
        action='file_updated',
        old_status=old_status,
        new_status='pending'
    )

    return {'status': 'file_updated', 'file': document.file.url}


# ============================================================
# 3. Отправка на проверку (владелец)
# ============================================================

def send_document_to_review(document, user):
    """
    Отправляет черновик на проверку модератору.
    Статус меняется с 'draft' на 'pending'.
    """
    # Сохраняем исходный статус для истории
    old_status = document.status

    # Меняем статус
    document.status = 'pending'
    document.save()

    # Логируем
    document.log_action(
        user=user,
        action='submitted',
        old_status=old_status,
        new_status='pending'
    )

    return {'status': 'submitted'}


# ============================================================
# 4. Подтверждение документа (модератор)
# ============================================================

def approve_document(document, moderator):
    """
    Подтверждает документ. Статус становится 'approved'.
    """
    # Сохраняем исходный статус для истории
    old_status = document.status

    # Вызываем метод модели
    document.approve(moderator=moderator)

    # Логируем
    document.log_action(
        user=moderator,
        action='approved',
        old_status=old_status,
        new_status='approved'
    )

    return {'status': 'approved'}


# ============================================================
# 5. Отклонение документа (модератор)
# ============================================================

def reject_document(document, moderator, comment):
    """
    Отклоняет документ с указанием причины.
    Статус становится 'rejected'.
    """
    # Сохраняем исходный статус для истории
    old_status = document.status

    # Вызываем метод модели
    document.reject(moderator=moderator, comment=comment)

    # Логируем
    document.log_action(
        user=moderator,
        action='rejected',
        comment=comment,
        old_status=old_status,
        new_status='rejected'
    )

    return {'status': 'rejected', 'comment': comment}