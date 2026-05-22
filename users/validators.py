from PIL import Image
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password as django_validate_password


def validate_avatar(value):
    """
    Проверка загружаемого аватара:
    1. Размер файла не должен превышать 5 МБ
    2. Файл должен быть реальным изображением (проверка через Pillow)
    """
    max_size_mb = 5
    max_size_bytes = max_size_mb * 1024 * 1024

    # Проверка размера
    if value.size > max_size_bytes:
        raise ValidationError(f"Размер аватара не должен превышать {max_size_mb} МБ")

    # Проверка, что файл действительно является изображением
    try:
        # verify() проверяет целостность данных изображения
        image = Image.open(value)
        image.verify()
        # Возвращаем указатель файла в начало для дальнейшего использования
        value.seek(0)
    except Exception:
        raise ValidationError("Файл не является изображением или повреждён")

    return value


def validate_password(value):
    """Стандартные валидаторы Django с русскими сообщениями"""
    try:
        django_validate_password(value)
    except ValidationError as e:
        # Словарь перевода ошибок
        error_messages = {
            'This password is too short. It must contain at least 8 characters.':
                'Пароль слишком короткий. Минимум 8 символов.',
            'This password is too common.':
                'Пароль слишком простой. Используйте более сложный пароль.',
            'This password is entirely numeric.':
                'Пароль не может состоять только из цифр.',
            'The password is too similar to the email address.':
                'Пароль слишком похож на email адрес.',
            'The password is too similar to the first name.':
                'Пароль слишком похож на имя.',
            'The password is too similar to the last name.':
                'Пароль слишком похож на фамилию.',
        }
        # Переводим первое сообщение об ошибке
        first_error = e.messages[0] if e.messages else str(e)
        russian_error = error_messages.get(first_error, first_error)
        raise ValidationError(russian_error)
    return value


def validate_first_name(value):
    """Имя обязательно для заполнения. Пустые строки не допускаются."""
    if not value or not value.strip():
        raise ValidationError("Имя обязательно")
    return value.strip()


def validate_last_name(value):
    """Фамилия обязательна для заполнения. Пустые строки не допускаются."""
    if not value or not value.strip():
        raise ValidationError("Фамилия обязательна")
    return value.strip()

