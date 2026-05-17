from rest_framework import permissions

class CanApproveDocument(permissions.BasePermission):
    """Проверяет, может ли пользователь подтверждать документы"""
    def has_permission(self, request, view):
        return request.user.has_perm('documents.can_approve_document')

class CanRejectDocument(permissions.BasePermission):
    """Проверяет, может ли пользователь отклонять документы"""
    def has_permission(self, request, view):
        return request.user.has_perm('documents.can_reject_document')

class IsOwnerOnly(permissions.BasePermission):
    """Проверяет, является ли пользователь владельцем документа"""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
