from django.contrib import admin
from django.utils.safestring import mark_safe

from users.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Админка для управления пользователями"""

    # Колонки в списке пользователей
    list_display = [
        "id",  # ID пользователя
        "email",  # Email (логин)
        "first_name",  # Имя
        "last_name",  # Фамилия
        "status_badge",  # Статус (активен/удалён/неактивен)
        "deleted_at",  # Дата мягкого удаления
        "is_staff",  # Доступ в админку
    ]

    # Фильтры в правой боковой панели
    list_filter = ["is_active", "is_staff", "deleted_at"]

    # Поиск по этим полям
    search_fields = ["email", "first_name", "last_name", "phone"]

    # Поля, которые нельзя редактировать (только чтение)
    readonly_fields = ["deleted_at"]

    # Показываем ВСЕХ пользователей (включая удалённых)
    def get_queryset(self, request):
        return User._base_manager.all()

    # Группировка полей на странице редактирования
    fieldsets = (
        (
            "Основная информация",
            {"fields": ("email", "first_name", "last_name", "phone", "avatar")},
        ),
        (
            "Права доступа",
            {
                "fields": ("is_staff", "is_superuser", "groups", "user_permissions"),
                "classes": ("collapse",),  # Свёрнутая секция
            },
        ),
        ("Мягкое удаление", {"fields": ("deleted_at",), "classes": ("collapse",)}),
    )

    # Цветной индикатор статуса пользователя
    def status_badge(self, obj):
        if obj.deleted_at:
            # Удалён: красный текст + дата
            return mark_safe(
                f'<span style="color: #dc3545;">🗑 Удалён</span> '
                f'<span style="color: #6c757d; font-size: 11px;">({obj.deleted_at.strftime("%d.%m.%Y")})</span>'
            )
        if not obj.is_active:
            # Неактивен: оранжевый
            return mark_safe('<span style="color: #e67e22;">⚠ Неактивен</span>')
        # Активен: зелёная точка
        return mark_safe('<span style="color: #27ae60;">● Активен</span>')

    status_badge.short_description = "Статус"

    # Массовое действие: восстановление удалённых пользователей
    actions = ["restore_selected"]

    def restore_selected(self, request, queryset):
        """Восстанавливает выбранных пользователей (очищает deleted_at и делает is_active=True)"""
        updated = queryset.filter(deleted_at__isnull=False).update(
            deleted_at=None, is_active=True
        )
        self.message_user(request, f"Восстановлено {updated} пользователей.")

    restore_selected.short_description = "Восстановить выбранных"
