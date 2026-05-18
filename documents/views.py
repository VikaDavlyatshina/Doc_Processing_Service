from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from documents.models import Document
from documents.permissions import CanApproveDocument, CanRejectDocument, IsOwnerOnly
from documents.serializers import DocumentSerializer
from documents.services import (
    handle_file_update,
    check_document_status,
    handle_submit,
    handle_approve,
    handle_reject
)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с документами.

    Доступные эндпоинты (требуют авторизации):
    - POST   /api/documents/           -> создать документ (требует user_note)
    - GET    /api/documents/           -> список документов
    - GET    /api/documents/{id}/      -> просмотр документа
    - DELETE /api/documents/{id}/      -> удалить документ
    - POST   /api/documents/{id}/update-file/  -> заменить файл (владелец)
    - POST   /api/documents/{id}/submit/      -> отправить на проверку
    - POST   /api/documents/{id}/approve/     -> подтвердить (модератор)
    - POST   /api/documents/{id}/reject/      -> отклонить (модератор)
    """

    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]  # все действия требуют авторизации

    # ================================================================
    # 1. КАКИЕ ДОКУМЕНТЫ ПОКАЗЫВАТЬ
    # ================================================================

    def get_queryset(self):
        """Возвращает список документов с учётом прав пользователя."""
        user = self.request.user

        if not user.is_authenticated:
            return Document.objects.none()

        # Модератор видит всё, кроме черновиков
        if user.has_perm("documents.can_view_all_documents"):
            return Document.objects.exclude(status="draft")

        # Обычный пользователь видит только свои документы
        return Document.objects.filter(user=user)

    # ================================================================
    # 2. КАКИЕ ПРАВА ПРОВЕРЯТЬ
    # ================================================================

    def get_permissions(self):
        """Добавляет дополнительные права (IsAuthenticated уже есть)."""

        # Только владелец
        if self.action in ["destroy", "update_file", "submit"]:
            return [IsOwnerOnly()]

        # Только модератор с правом approve
        if self.action == "approve":
            return [CanApproveDocument()]

        # Только модератор с правом reject
        if self.action == "reject":
            return [CanRejectDocument()]

        # Для list, create, retrieve — только IsAuthenticated
        return []

    # ================================================================
    # 3. СОЗДАНИЕ (автоматическая подстановка автора)
    # ================================================================

    def perform_create(self, serializer):
        """При создании документа подставляем текущего пользователя."""
        document = serializer.save(user=self.request.user)
        document.log_action(user=self.request.user, action='created', new_status='draft')

    # ================================================================
    # 4. ЗАМЕНИТЬ ФАЙЛ (только владелец)
    # ================================================================

    @action(detail=True, methods=['post'])
    def update_file(self, request, pk=None):
        """Заменяет файл и сбрасывает статус в черновик."""
        document = self.get_object()
        new_file = request.FILES.get('file')

        if not new_file:
            return Response(
                {'error': 'Файл не передан'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = handle_file_update(document, new_file)
        return Response(result)

    # ================================================================
    # 5. ОТПРАВИТЬ НА ПРОВЕРКУ (только владелец)
    # ================================================================

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Отправляет черновик на проверку модератору."""
        document = self.get_object()

        error = check_document_status(document, 'draft')
        if error:
            return error

        result = handle_submit(document)
        return Response(result)

    # ================================================================
    # 6. ПОДТВЕРДИТЬ (только модератор)
    # ================================================================

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Подтверждает документ (статус -> approved)."""
        document = self.get_object()

        error = check_document_status(document, 'pending')
        if error:
            return error

        result = handle_approve(document, request.user)
        return Response(result)

    # ================================================================
    # 7. ОТКЛОНИТЬ (только модератор)
    # ================================================================

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклоняет документ с обязательным комментарием."""
        document = self.get_object()

        error = check_document_status(document, 'pending')
        if error:
            return error

        comment = request.data.get('comment', '').strip()
        if not comment:
            return Response(
                {'error': 'Укажите причину отклонения'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = handle_reject(document, request.user, comment)
        return Response(result)