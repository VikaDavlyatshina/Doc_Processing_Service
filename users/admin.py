from django.contrib import admin, messages
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
        "deleted_by",
        "restored_at",
        "restored_by",
        "is_staff",  # Доступ в админку
    ]

    # Фильтры в правой боковой панели
    list_filter = ["is_active", "is_staff", "deleted_at"]

    # Поиск по этим полям
    search_fields = ["email", "first_name", "last_name", "phone"]

    # Поля, которые нельзя редактировать (только чтение)
    readonly_fields = ["deleted_at", "deleted_by", "restored_at", "restored_by"]

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
        ("Мягкое удаление", {
            "fields": ("deleted_at", "deleted_by", "restored_at", "restored_by"),
            "classes": ("collapse",),
        }),
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
    actions = ["restore_selected", "deactivate_selected"]

    def restore_selected(self, request, queryset):
        """Массовое восстановление выбранных пользователей"""
        restored = 0
        skipped_active = 0

        for user in queryset:
            # Проверка: только удалённые
            if user.deleted_at is None:
                skipped_active += 1
                continue

            user.restore(performed_by=request.user)
            restored += 1

        messages_list = []
        if restored:
            messages_list.append(f"✅ Восстановлено: {restored}")
        if skipped_active:
            messages_list.append(f"⚠️ Активные пользователи пропущены: {skipped_active}")

        if messages_list:
            self.message_user(request, " | ".join(messages_list), messages.SUCCESS)
        else:
            self.message_user(request, "Нет пользователей для восстановления", messages.WARNING)
    def deactivate_selected(self, request, queryset):
        """Массовая деактивация выбранных пользователей"""
        deactivated = 0
        skipped_superuser = 0
        skipped_self = 0
        skipped_already_deactivated = 0

        for user in queryset:
            # Проверка: уже деактивирован
            if user.deleted_at is not None:
                skipped_already_deactivated += 1
                continue

            # Проверка: суперпользователь
            if user.is_superuser:
                skipped_superuser += 1
                continue

            # Проверка: нельзя деактивировать самого себя
            if user == request.user:
                skipped_self += 1
                continue

            # Деактивируем
            user.soft_delete(performed_by=request.user)
            deactivated += 1

        # Формируем сообщение
        messages_list = []
        if deactivated:
            messages_list.append(f"✅ Деактивировано: {deactivated}")
        if skipped_already_deactivated:
            messages_list.append(f"⚠️ Уже деактивированы: {skipped_already_deactivated}")
        if skipped_superuser:
            messages_list.append(f"⚠️ Суперпользователи пропущены: {skipped_superuser}")
        if skipped_self:
            messages_list.append(f"⚠️ Свой аккаунт пропущен: {skipped_self}")

        if messages_list:
            self.message_user(request, " | ".join(messages_list), messages.SUCCESS)
        else:
            self.message_user(request, "Нет пользователей для деактивации", messages.WARNING)