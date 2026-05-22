from rest_framework import permissions


class IsOwnerOnly(permissions.BasePermission):
    """Проверяет, является ли пользователь владельцем документа"""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsModerator(permissions.BasePermission):
    """Проверяет, что пользователь состоит в группе модераторов документов"""

    def has_permission(self, request, view):
        # Суперпользователь может всё
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name="Document Moderator").exists()


class IsUserManager(permissions.BasePermission):
    """Проверяет, что пользователь в группе менеджеров пользователей или суперпользователь"""
    def has_permission(self, request, view):
        # Суперпользователь может всё
        if request.user.is_superuser:
            return True
        # Обычный пользователь может, если он в группе User Manager
        return request.user.groups.filter(name="User Manager").exists()