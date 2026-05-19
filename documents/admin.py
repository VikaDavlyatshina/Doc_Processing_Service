from django.contrib import admin, messages
from django.utils.safestring import mark_safe

from .models import Document, DocumentLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Админка документов"""

    # Что видим в списке
    list_display = [
        "id",
        "user",
        "user_note",
        "file_link",
        "status_colored",
        "uploaded_at",
    ]
    list_filter = ["status"]
    search_fields = ["user__email", "user_note"]

    # Поля в форме редактирования
    fields = [
        "user",
        "file",
        "user_note",
        "status",
        "comment",
        "uploaded_at",
        "reviewed_by",
        "reviewed_at",
    ]

    # Только чтение
    readonly_fields = ["uploaded_at", "reviewed_at"]

    # Массовые действия
    actions = ["approve_selected", "reject_selected"]

    # ============================================================
    # Ссылка на файл
    # ============================================================
    def file_link(self, obj):
        if obj.file:
            return mark_safe(f'<a href="{obj.file.url}" download>📄 Скачать</a>')
        return "-"

    file_link.short_description = "Файл"

    # ============================================================
    # Статус с цветом
    # ============================================================
    def status_colored(self, obj):
        colors = {
            "draft": "gray",
            "pending": "orange",
            "approved": "green",
            "rejected": "red",
        }
        color = colors.get(obj.status, "black")
        return mark_safe(f'<b style="color:{color};">{obj.get_status_display()}</b>')

    status_colored.short_description = "Статус"
    status_colored.admin_order_field = "status"

    # ============================================================
    # Массовое подтверждение
    # ============================================================
    def approve_selected(self, request, queryset):
        count = 0
        for doc in queryset.filter(status="pending"):
            doc.approve(moderator=request.user)
            count += 1
        self.message_user(request, f"Подтверждено: {count}", messages.SUCCESS)

    approve_selected.short_description = "Подтвердить выбранные"

    # ============================================================
    # Массовое отклонение
    # ============================================================
    def reject_selected(self, request, queryset):
        count = 0
        for doc in queryset.filter(status="pending"):
            doc.reject(moderator=request.user, comment="Отклонено в админке")
            count += 1
        self.message_user(request, f"Отклонено: {count}", messages.WARNING)

    reject_selected.short_description = "Отклонить выбранные"


@admin.register(DocumentLog)
class DocumentLogAdmin(admin.ModelAdmin):
    """История действий — только просмотр"""

    list_display = [
        "id",
        "document_link",
        "action",
        "user_email",
        "old_status",
        "new_status",
        "created_at",
    ]
    list_filter = ["action", "created_at"]
    search_fields = ["document__id", "user__email"]
    readonly_fields = [
        "document",
        "user",
        "action",
        "comment",
        "old_status",
        "new_status",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def document_link(self, obj):
        url = f"/admin/documents/document/{obj.document.id}/change/"
        return mark_safe(f'<a href="{url}">Документ #{obj.document.id}</a>')

    document_link.short_description = "Документ"

    def user_email(self, obj):
        return obj.user.email if obj.user else "-"

    user_email.short_description = "Кто сделал"
