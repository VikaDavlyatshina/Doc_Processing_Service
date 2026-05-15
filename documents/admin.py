from django.contrib import admin, messages

from documents.models import Document


# Register your models here.

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'uploaded_at', 'reviewed_by', 'reviewed_at']
    list_filter = ['status']

    # Определяем действия
    actions = ['approve_documents', 'reject_documents']

    def approve_documents(self, request, queryset):
        """
        Подтвердить выбранные документы.
        """
        # Обновляем статус у всех выбранных документов
        updated = queryset.update(status='approved')
        # Показываем сообщение об успехе
        self.message_user(
            request,
            f'Подтверждено {updated} документов.',
            messages.SUCCESS
        )

    approve_documents.short_description = 'Подтвердить выбранные документы'

    def reject_documents(self, request, queryset):
        """
        Отклонить выбранные документы.
        """
        updated = queryset.update(status='rejected')
        self.message_user(
            request,
            f'Отклонено {updated} документов.',
            messages.SUCCESS
        )

    reject_documents.short_description = 'Отклонить выбранные документы'