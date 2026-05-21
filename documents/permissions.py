from rest_framework import permissions


class IsOwnerOnly(permissions.BasePermission):
    """Проверяет, является ли пользователь владельцем документа"""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsModerator(permissions.BasePermission):
    """Проверяет, что пользователь состоит в группе модераторов документов"""

    def has_permission(self, request, view):
        return request.user.groups.filter(name="Document Moderator").exists()
