from django.db import models
from django.utils import timezone

from config import settings

from .validators import check_document_file

# Create your models here.


class DocumentLog(models.Model):
    """Модель для хранения истории изменений и логирования действий с документом."""

    # Список действий для логирования
    ACTION_CHOICES = [
        ("created", "Создан"),
        ("submitted", "Отправлен на проверку"),
        ("approved", "Подтверждён"),
        ("rejected", "Отклонён"),
        ("file_updated", "Файл заменён"),
        ("deleted", "Удалён"),
    ]

    # К какому документу относится лог
    document = models.ForeignKey(
        "Document", on_delete=models.CASCADE, related_name="logs"
    )
    # Кто совершил действие
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    # Тип действия
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    # Комментарий
    comment = models.TextField(blank=True)
    # Статус до действия
    old_status = models.CharField(max_length=20, blank=True)
    # Статус после действия
    new_status = models.CharField(max_length=20, blank=True)
    # Дата создания лога (заполняется автоматически)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Сортировка: новые записи всегда будут вверху списка
        ordering = ["-created_at"]
        # Отображение названия модели в админ-панели Django
        verbose_name = "История документа"
        verbose_name_plural = "История документов"

    def __str__(self):
        # Строковое представление лога для админки или отладки
        return f"{self.document.id} - {self.action} - {self.created_at}"


def user_document_path(instance, filename):
    """
    Сохраняет файл в структуру:
    documents/user_{username}/YYYY-MM-DD/filename
    """
    # Берём email до @ как имя пользователя
    username = instance.user.email.split("@")[0]

    # Дата загрузки в формате ГГГГ-ММ-ДД (используем текущую дату)
    date_str = timezone.now().strftime("%Y-%m-%d")

    # Возвращаем путь: user_ivan/2026-01-15/passport.pdf
    return f"documents/user_{username}/{date_str}/{filename}"


class Document(models.Model):
    """Модель документа, загруженного пользователем."""

    STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("pending", "На рассмотрении"),
        ("approved", "Подтверждён"),
        ("rejected", "Отклонён"),
    ]

    # Кто загрузил
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Пользователь",
    )

    # Сам файл
    file = models.FileField(
        upload_to=user_document_path,
        verbose_name="Файл",
        validators=[check_document_file],
    )
    # Комментарий пользователя (обязательный при создании)
    user_note = models.TextField(
        verbose_name="Комментарий пользователя",
        help_text="Пояснение к документу",
    )

    # Статус
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name="Статус"
    )

    # Комментарий администратора (только при отклонении)
    comment = models.TextField(
        blank=True,  # Можно пустое при создании
        verbose_name="Причина отклонения",
        help_text="Заполняется администратором при отклонении",
    )

    # Даты

    # Дата загрузки
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")
    # Дата обновления
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    # Кто и когда проверил
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_documents",
        verbose_name="Проверил",
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата проверки"
    )

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ["-uploaded_at"]  # новые документы сверху
        permissions = [
            ("can_approve_document", "Может подтверждать документы"),
            ("can_reject_document", "Может отклонять документы"),
            ("can_view_all_documents", "Может просматривать все документы"),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.file.name} - {self.get_status_display()}"

    def log_action(self, user, action, comment="", old_status=None, new_status=None):
        """Записывает действие в историю"""
        DocumentLog.objects.create(
            document=self,
            user=user,
            action=action,
            comment=comment,
            old_status=old_status or self.status,
            new_status=new_status or self.status,
        )

    def approve(self, moderator):
        """Подтвердить документ."""
        old_status = self.status  # ← сохраняем старый статус ДО изменения
        self.status = "approved"  # 1. Меняем статус
        self.reviewed_by = moderator  # 2. Запоминаем, кто подтвердил
        self.reviewed_at = timezone.now()  # 3. Запоминаем, когда подтвердили
        self.save()  # 4. Сохраняем всё в БД

        self.log_action(
            user=moderator,
            action="approved",
            old_status=old_status,
            new_status="approved",
        )

    def reject(self, moderator, comment=""):
        """Отклонить документ."""
        old_status = self.status  # ← сохраняем старый статус ДО изменения
        self.status = "rejected"  # 1. Меняем статус
        self.comment = comment  # 2. Сохраняем причину отклонения
        self.reviewed_by = moderator  # 3. Кто отклонил
        self.reviewed_at = timezone.now()  # 4. Когда отклонили
        self.save()  # 5. Сохраняем

        self.log_action(
            user=moderator,
            action="rejected",
            comment=comment,
            old_status=old_status,
            new_status="rejected",
        )
