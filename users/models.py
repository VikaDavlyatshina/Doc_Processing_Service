from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    """
    Кастомный менеджер для модели User.
    Отвечает за создание пользователей и фильтрацию удалённых.
    """

    def get_queryset(self):
        """
        Переопределяем стандартный запрос.
        По умолчанию возвращаем только активных пользователей (не удалённых).
        Удалённые пользователи исключаются автоматически.
        """
        return super().get_queryset().filter(deleted_at__isnull=True)

    def active(self):
        """
        Возвращает только активных (не удалённых) пользователей.
        """
        return self.get_queryset()

    def create_user(self, email, password=None, **extra_fields):
        """
        Создаёт обычного пользователя.
        """
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)

        # Значения по умолчанию для обычного пользователя
        extra_fields.setdefault("is_active", True)     # Пользователь активен сразу после регистрации
        extra_fields.setdefault("is_staff", False)     # Нет доступа в админку
        extra_fields.setdefault("is_superuser", False) # Не суперпользователь

        # Хэшируем пароль и сохраняем
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Создаёт суперпользователя.
        """
        # Устанавливаем права
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        # Валидация прав
        if not extra_fields.get("is_staff"):
            raise ValueError("Суперпользователь должен иметь is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Суперпользователь должен иметь is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Кастомная модель пользователя.
    Аутентификация по email (вместо стандартного username).
    Поддерживает мягкое удаление (сохранение данных в БД с блокировкой входа).
    """

    # Отключаем стандартное поле username (оно не используется)
    username = None

    # Email
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Используется для входа в систему"
    )

    # Телефон (необязательный)
    phone = PhoneNumberField(
        blank=True,
        null=True,
        verbose_name="Телефон",
        help_text="Введите номер телефона"
    )

    # Личные данные
    first_name = models.CharField(
        max_length=50,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=50,
        verbose_name="Фамилия"
    )

    # Аватар профиля (загружается пользователем, необязательный)
    avatar = models.ImageField(
        upload_to="users/avatars",
        blank=True,
        null=True,
        verbose_name="Фото профиля"
    )
    # Поле для мягкого удаления:
    # - NULL = пользователь активен
    # - дата = пользователь удалён (запись остаётся в БД, но вход заблокирован)
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата удаления"
    )

    # ==================================================================
    # НАСТРОЙКИ АУТЕНТИФИКАЦИИ
    # ==================================================================

    # Для входа используется email
    USERNAME_FIELD = "email"
    # Поля, которые запрашиваются при создании суперпользователя
    REQUIRED_FIELDS = ["first_name", "last_name"]

    # Подключаем кастомный менеджер
    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        """Строковое представление пользователя (для админки и отладки)."""
        return self.email

    # ==================================================================
    # МЕТОДЫ МЯГКОГО УДАЛЕНИЯ
    # ==================================================================

    def soft_delete(self):
        """
        Мягкое удаление пользователя.
        - Заполняет дату удаления
        - Деактивирует учётную запись (блокирует вход)
        Сама запись остаётся в базе данных.
        """
        self.deleted_at = timezone.now()   # Запоминаем момент удаления
        self.is_active = False              # Блокируем возможность входа
        self.save()

    def restore(self):
        """
        Восстановление мягко удалённого пользователя.
        - Очищает дату удаления
        - Активирует учётную запись (разрешает вход)
        """
        self.deleted_at = None              # Очищаем метку удаления
        self.is_active = True               # Разблокируем вход
        self.save()

    @property
    def is_deleted(self):
        """
        Проверяет, удалён ли пользователь.
        Возвращает True, если deleted_at заполнен (не NULL).
        """
        return self.deleted_at is not None

    # ==================================================================
    # МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ИМЕНИ
    # ==================================================================

    def get_full_name(self):
        """
        Возвращает полное имя пользователя (Имя + Фамилия).
        Если имя не заполнено, возвращает часть email до @.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.email.split("@")[0]

    def get_short_name(self):
        """
        Возвращает короткое имя (только имя).
        Если имя не заполнено, возвращает часть email до @.
        """
        if self.first_name:
            return self.first_name
        return self.email.split("@")[0]