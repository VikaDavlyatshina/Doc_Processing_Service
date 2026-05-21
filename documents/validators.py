from pathlib import Path

import magic
from django.core.exceptions import ValidationError

"""
MIME-тип — это универсальный идентификатор формата, который указывает компьютеру (или браузеру),
какие данные содержатся в файле и как с ними нужно работать
"""


# Разрешенные mime-типы
ALLOWED_MIME_TYPES = {
    "application/msword",  # DOC (старый Word)
    # DOCX (старый Word)
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",  # JPG изображения
    "image/jpeg",  # PNG изображения
    "application/pdf",  # PDF документы
}

# Разрешенные расширения
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}

# Максимальный размер файла- 10 МБ
MAX_FILE_SIZE = 10 * 1024 * 1024


def check_document_file(file):
    """Проверка файла"""

    # Проверяем, что файл не пустой
    if file.size == 0:
        raise ValidationError("Файл пустой или незагружен.")

    # 1) Проверка размера файла
    if file.size > MAX_FILE_SIZE:
        raise ValidationError("Файл слишком большой. Максимальный размер файла: 10 МБ")

    # 2) Проверяем расширение файла

    # Извлекаем расширение с помощью метода suffix
    # Приводим всё к нижнему регистру для удобства сравнения
    file_extension = Path(file.name).suffix.lower()
    # Если текущего расширения нет в списке разрешенных - выбрасываем исключение
    if file_extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Недопустимое расширение: {file_extension}")

    # 3) Проверяем реальный тип файла
    try:
        mime = magic.from_buffer(file.read(2048), mime=True)
    except Exception as e:
        raise ValidationError(f"Не удалось определить тип файла: {e}")
    finally:
        file.seek(0)  # возвращаем курсор в начало файла

    if mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Неподдерживаемый формат файла: {mime}. Разрешены: PDF, JPEG, PNG, DOC, DOCX"
        )

    # Если все проверки пройдены — возвращаем файл
    return file

def validate_comment_length(comment, max_length=500):
    """
    Проверяет, что комментарий не превышает максимальную длину.
    Возвращает очищенный комментарий или выбрасывает ValidationError.
    """
    if not comment or not comment.strip():
        raise ValidationError("Укажите причину отклонения")
    if len(comment) > max_length:
        raise ValidationError(f"Комментарий не может быть длиннее {max_length} символов")
    return comment.strip()