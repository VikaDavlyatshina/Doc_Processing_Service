from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


# Create your models here.

class UserManager(BaseUserManager):
    """Кастомный менеджер для модели User без username"""

    def create_user(self, email, password=None, **extra_fields):
        """ Создаёт обычного пользователя """

        if not email:
            raise ValueError("Email обязателен")

        email = self.normalize_email(email)

        # Устанавливаем значения по умолчанию
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        # Создаём объяект в памяти
        user = self.model(email=email, **extra_fields)
        # Устанавливаем пароль с хэшированием
        user.set_password(password)
        # Сохраняем пользователя
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """ Создаёт суперпользователя """

        # Устанавливаем значения по умолчанию
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        # Валидация
        if not extra_fields.get("is_staff"):
            raise ValueError("Суперпользователь должен иметь is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Суперпользователь должен иметь is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Кастомная модель пользователя"""

    # Отключаем поле username
    username = None

    # Email — основной идентификатор
    email = models.EmailField(
        unique=True,
        verbose_name='Email',
        help_text='Используется для входа в систему'
    )

    phone = PhoneNumberField(blank=True, null=True, verbose_name="Телефон", help_text="Введите номер телефона")

    first_name = models.CharField(max_length=50, verbose_name='Имя', help_text='Укажите своё имя')

    last_name = models.CharField(max_length=50, verbose_name='Фамилия', help_text='Укажите свою фамилию')

    avatar = models.ImageField(
        upload_to="users/avatars",
        blank=True,
        null=True,
        verbose_name="Фото профиля",
        help_text="Загрузите фото профиля",
    )

    # Токен для подтверждения почты
    # token = models.CharField(max_length=100, verbose_name="Token", blank=True, null=True)

    # Настройки аутентификации
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # Подключаем менеджер
    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email

    def get_full_name(self):
        """ Получение полного имени """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.email.split("@")[0]

    def get_short_name(self):
        """ Получение имени """
        if self.first_name:
            return self.first_name
        return self.email.split("@")[0]