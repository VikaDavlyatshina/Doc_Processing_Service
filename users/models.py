from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
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
        # deleted_at__isnull=True = дата удаления не заполнена → пользователь активен
        return super().get_queryset().filter(deleted_at__isnull=True)

    def active(self):
        """
        Возвращает только активных (не удалённых) пользователей.
        Явный метод для читаемости кода.
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
        extra_fields.setdefault(
            "is_active", True
        )  # Пользователь активен сразу после регистрации
        extra_fields.setdefault("is_staff", False)  # Нет доступа в админку
        extra_fields.setdefault("is_superuser", False)  # Не суперпользователь

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
        extra_fields.setdefault("is_staff", True)  # Доступ в админку
        extra_fields.setdefault("is_superuser", True)  # Все права
        extra_fields.setdefault("is_active", True)  # Активен сразу

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

    # ==================================================================
    # 1. ОСНОВНЫЕ ПОЛЯ (аутентификация)
    # ==================================================================

    # Отключаем стандартное поле username (оно не используется)
    username = None

    # Email — основной идентификатор для входа
    email = models.EmailField(
        unique=True, verbose_name="Email", help_text="Используется для входа в систему"
    )

    # ==================================================================
    # 2. КОНТАКТНЫЕ ДАННЫЕ
    # ==================================================================

    # Телефон (необязательный)
    phone = PhoneNumberField(
        blank=True,
        null=True,
        verbose_name="Телефон",
        help_text="Введите номер телефона",
    )

    # Личные данные
    first_name = models.CharField(max_length=50, verbose_name="Имя")
    last_name = models.CharField(max_length=50, verbose_name="Фамилия")

    # Аватар профиля (загружается пользователем, необязательный)
    avatar = models.ImageField(
        upload_to="users/avatars", blank=True, null=True, verbose_name="Фото профиля"
    )

    # ==================================================================
    # 3. ПОЛЯ ДЛЯ МЯГКОГО УДАЛЕНИЯ (сохраняем историю, но блокируем вход)
    # ==================================================================

    # deleted_at = дата удаления (NULL = пользователь активен)
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата удаления"
    )
    # deleted_by = кто выполнил удаление (ссылка на пользователя)
    deleted_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_users",
        verbose_name="Кто удалил",
    )

    # restored_at = дата восстановления (для аудита)
    restored_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата восстановления"
    )
    # restored_by = кто выполнил восстановление (ссылка на пользователя)
    restored_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restored_users",
        verbose_name="Кто восстановил",
    )

    # ==================================================================
    # 4. НАСТРОЙКИ АУТЕНТИФИКАЦИИ DJANGO
    # ==================================================================

    # Для входа используется email (вместо username)
    USERNAME_FIELD = "email"
    # Поля, которые запрашиваются при создании суперпользователя
    REQUIRED_FIELDS = ["first_name", "last_name"]

    # Подключаем кастомный менеджер (автоматически фильтрует удалённых)
    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        """Строковое представление пользователя (для админки и отладки)."""
        return self.email

    # ==================================================================
    # 5. МЕТОДЫ МЯГКОГО УДАЛЕНИЯ И ВОССТАНОВЛЕНИЯ
    # ==================================================================

    def soft_delete(self, performed_by=None):
        """
        Мягкое удаление пользователя.
        1. Заполняем дату удаления (deleted_at)
        2. Запоминаем, кто удалил (deleted_by)
        3. Блокируем вход (is_active = False)
        Сама запись остаётся в БД — можно восстановить.
        """
        self.deleted_at = timezone.now()  # Момент удаления
        self.deleted_by = performed_by  # Кто удалил (админ или сам пользователь)
        self.is_active = False  # Блокируем вход в систему
        self.save()

    def restore(self, performed_by=None):
        """
        Восстановление мягко удалённого пользователя.
        1. Очищаем дату удаления (deleted_at)
        2. Очищаем "кто удалил" (deleted_by)
        3. Заполняем дату восстановления (restored_at)
        4. Запоминаем, кто восстановил (restored_by
        5. Разблокируем вход (is_active = True)
        """
        self.deleted_at = None  # Очищаем метку удаления
        self.deleted_by = None  # Очищаем, кто удалил
        self.restored_at = timezone.now()  # Запоминаем момент восстановления
        self.restored_by = performed_by  # Запоминаем, кто восстановил
        self.is_active = True  # Разблокируем вход
        self.save()

    @property
    def is_deleted(self):
        """
        Проверяет, удалён ли пользователь.
        Возвращает True, если deleted_at заполнен (не NULL).
        Удобно для проверок: if user.is_deleted: ...
        """
        return self.deleted_at is not None

    # ==================================================================
    # 6. МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ИМЕНИ
    # ==================================================================

    def get_full_name(self):
        """
        Возвращает полное имя пользователя (Имя + Фамилия).
        Если имя не заполнено, возвращает часть email до @.
        Используется в письмах и интерфейсе.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.email.split("@")[0]
