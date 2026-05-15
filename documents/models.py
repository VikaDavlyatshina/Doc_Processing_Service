from django.db import models
from django.utils import timezone
from .validators import check_document_file
from config import settings


# Create your models here.

def user_document_path(instance, filename):
    """
    Сохраняет файл в структуру:
    documents/user_{username}/YYYY-MM-DD/filename
    """
    # Берём email до @ как имя пользователя
    username = instance.user.email.split('@')[0]

    # Дата загрузки в формате ГГГГ-ММ-ДД (используем текущую дату)
    date_str = timezone.now().strftime('%Y-%m-%d')

    # Возвращаем путь: user_ivan/2026-01-15/passport.pdf
    return f'documents/user_{username}/{date_str}/{filename}'


class Document(models.Model):
    """Модель документа, загруженного пользователем."""

    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Подтверждён'),
        ('rejected', 'Отклонён'),
    ]

    # Кто загрузил
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Пользователь'
    )

    # Сам файл
    file = models.FileField(
        upload_to=user_document_path,
        verbose_name='Файл',
        validators=[check_document_file],
    )

    # Статус
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )

    # Комментарий (причина отклонения)
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий',
        help_text='Причина отклонения (заполняется администратором)'
    )

    # Даты

    # Дата загрузки
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )
    # Дата обновления
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    # Кто и когда проверил
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_documents',
        verbose_name='Проверил'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата проверки'
    )

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-uploaded_at']  # новые документы сверху
        permissions = [
            ('can_approve_document', 'Может подтверждать документы'),
            ('can_reject_document', 'Может отклонять документы'),
            ('can_view_all_documents', 'Может просматривать все документы'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.file.name} - {self.get_status_display()}"

    def approve(self, moderator):
        """Подтвердить документ."""
        self.status = 'approved'           # 1. Меняем статус
        self.reviewed_by = moderator       # 2. Запоминаем, кто подтвердил
        self.reviewed_at = timezone.now()  # 3. Запоминаем, когда подтвердили
        self.save()                        # 4. Сохраняем всё в БД

    def reject(self, moderator, comment=''):
        """Отклонить документ."""
        self.status = 'rejected'           # 1. Меняем статус
        self.comment = comment             # 2. Сохраняем причину отклонения
        self.reviewed_by = moderator       # 3. Кто отклонил
        self.reviewed_at = timezone.now()  # 4. Когда отклонили
        self.save()                        # 5. Сохраняем