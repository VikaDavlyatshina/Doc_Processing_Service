import os

from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe

from .models import Document, DocumentLog


class UserStatusFilter(SimpleListFilter):
    """Фильтр: показывать документы активных или удалённых пользователей"""

    title = "Статус пользователя"
    parameter_name = "user_status"

    def lookups(self, request, model_admin):
        return (
            ("active", "Активные пользователи"),
            ("deleted", "Удалённые пользователи"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(user__deleted_at__isnull=True)
        if self.value() == "deleted":
            return queryset.filter(user__deleted_at__isnull=False)
        return queryset


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Админка для управления документами"""

    # Отображаемые колонки в списке
    list_display = [
        "id",
        "user_link",
        "user_note",
        "file_link",
        "status_colored",
        "uploaded_at",
        "reviewed_by",
        "reviewed_at",
    ]

    # Фильтры в правой боковой панели
    list_filter = ["status", UserStatusFilter]

    # Поля поиска (работают через верхнее поле)
    search_fields = ["user__email", "user_note", "id"]

    # Поля, которые нельзя редактировать (только чтение)
    readonly_fields = ["uploaded_at", "reviewed_at", "reviewed_by"]

    # Массовые действия (выпадающий список)
    actions = ["approve_selected", "reject_selected"]

    def save_model(self, request, obj, form, change):
        """При сохранении документа — логируем создание или изменение статуса"""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new:
            # Новый документ
            obj.log_action(
                user=request.user,
                action="created",
                old_status=None,
                new_status=obj.status,
            )
            self.message_user(request, f"Документ #{obj.id} создан", messages.SUCCESS)

        elif change and "status" in form.changed_data:
            # Изменился статус
            old_status = form.initial.get("status")
            new_status = obj.status

            # Определяем тип действия
            if new_status == "approved":
                action = "approved"
            elif new_status == "rejected":
                action = "rejected"
            elif old_status == "draft" and new_status == "pending":
                action = "submitted"
            else:
                action = "status_changed"

            obj.log_action(
                user=request.user,
                action=action,
                old_status=old_status,
                new_status=new_status,
            )
            self.message_user(
                request, f"Статус документа #{obj.id} изменён", messages.SUCCESS
            )

    def file_link(self, obj):
        if obj.file:
            name = os.path.basename(obj.file.name)
            return mark_safe(f'<a href="{obj.file.url}" target="_blank">📄 {name}</a>')
        return "-"

    file_link.short_description = "Файл"

    def status_colored(self, obj):
        """Цветной статус документа"""
        colors = {
            "draft": "gray",
            "pending": "orange",
            "approved": "green",
            "rejected": "red",
        }
        color = colors.get(obj.status, "black")
        return mark_safe(f'<b style="color:{color};">{obj.get_status_display()}</b>')

    status_colored.short_description = "Статус"

    def user_link(self, obj):
        """Email пользователя. Для удалённых — красный с корзиной"""
        if obj.user.deleted_at:
            return mark_safe(f'<span style="color: #dc3545;">🗑 {obj.user.email}</span>')
        return obj.user.email

    user_link.short_description = "Пользователь"

    def approve_selected(self, request, queryset):
        """Массовое подтверждение документов"""
        count = 0
        for doc in queryset.filter(status="pending"):
            doc.approve(moderator=request.user)
            count += 1
        self.message_user(request, f"Подтверждено: {count}", messages.SUCCESS)

    approve_selected.short_description = "Подтвердить выбранные"

    def reject_selected(self, request, queryset):
        """Массовое отклонение документов"""
        count = 0
        for doc in queryset.filter(status="pending"):
            doc.reject(moderator=request.user, comment="Отклонено в админке")
            count += 1
        self.message_user(request, f"Отклонено: {count}", messages.WARNING)

    reject_selected.short_description = "Отклонить выбранные"


@admin.register(DocumentLog)
class DocumentLogAdmin(admin.ModelAdmin):
    """Админка для истории документа — только чтение"""

    list_display = [
        "id",
        "document_link",
        "action",
        "user_display",
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

    # Запрещаем добавление, изменение и удаление записей вручную
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True  # Разрешено для каскадного удаления при удалении документа

    def document_link(self, obj):
        """Ссылка на страницу редактирования документа"""
        url = f"/admin/documents/document/{obj.document.id}/change/"
        return mark_safe(f'<a href="{url}">Документ #{obj.document.id}</a>')

    document_link.short_description = "Документ"

    def user_display(self, obj):
        """Кто совершил действие. Для удалённых — красный с корзиной"""
        if obj.user and obj.user.deleted_at:
            return mark_safe(f'<span style="color: #dc3545;">🗑 {obj.user.email}</span>')
        return obj.user.email if obj.user else "-"

    user_display.short_description = "Кто сделал"
