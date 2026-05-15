from django.contrib import admin, messages
from django.utils import timezone
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'uploaded_at', 'reviewed_by', 'reviewed_at']
    list_filter = ['status']
    actions = ['approve_documents', 'reject_documents']

    def approve_documents(self, request, queryset):
        updated = 0
        for document in queryset:
            if document.status == 'pending':
                document.approve(moderator=request.user)
                updated += 1
        self.message_user(
            request,
            f'Подтверждено {updated} документов.',
            messages.SUCCESS
        )
    approve_documents.short_description = 'Подтвердить выбранные документы'

    def reject_documents(self, request, queryset):
        updated = 0
        for document in queryset:
            if document.status == 'pending':
                document.reject(
                    moderator=request.user,
                    comment='Отклонено модератором через админку'
                )
                updated += 1
        self.message_user(
            request,
            f'Отклонено {updated} документов.',
            messages.WARNING
        )
    reject_documents.short_description = 'Отклонить выбранные документы'