from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from documents.models import Document
from documents.permissions import IsOwnerOnly
from documents.serializers import DocumentSerializer
from documents.services import (approve_document, reject_document,
                                replace_document_file, send_document_to_review,
                                validate_document_status)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с документами.

    Доступные эндпоинты (требуют авторизации):
    - POST   /api/documents/           -> создать документ (требует user_note)
    - GET    /api/documents/           -> список документов
    - GET    /api/documents/{id}/      -> просмотр документа
    - DELETE /api/documents/{id}/      -> удалить документ
    """

    serializer_class = DocumentSerializer

    # ============================================================
    # 1. Какие документы показывать в списке
    # ============================================================

    def get_queryset(self):
        """Возвращает список документов с учётом прав пользователя."""
        user = self.request.user

        # Неавторизованные не видят ничего
        if not user.is_authenticated:
            return Document.objects.none()

        # Модератор видит всё, кроме черновиков (их проверять не нужно)
        if user.has_perm("documents.can_view_all_documents"):
            return Document.objects.exclude(status="draft")

        # Обычный пользователь видит только свои документы
        return Document.objects.filter(user=user)

    # ============================================================
    # 2. Какие права проверять для каждого действия
    # ============================================================

    def get_permissions(self):
        """Назначает права для разных действий."""
        # Удалить документ может только владелец
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsOwnerOnly()]

        # Для list, create, retrieve — достаточно авторизации
        return [permissions.IsAuthenticated()]

    # ============================================================
    # 3. Создание документа (автор и запрет модераторам)
    # ============================================================

    def perform_create(self, serializer):
        """
        При создании:
        - подставляем автора из токена
        - запрещаем модераторам создавать документы
        - логируем создание
        """
        user = self.request.user

        # Модераторы не могут создавать документы (у них есть своя роль)
        if user.has_perm("documents.can_approve_document") or user.has_perm(
            "documents.can_reject_document"
        ):
            raise PermissionDenied("Модераторы не могут создавать документы")

        # Создаём документ и логируем
        document = serializer.save(user=user)
        document.log_action(user=user, action="created", new_status="draft")


class DocumentOwnerViewsSet(viewsets.GenericViewSet):
    """
    Действия, доступные только владельцу документа:
    - POST /api/documents/{id}/update-file/   -> заменить файл
    - POST /api/documents/{id}/submit/       -> отправить на проверку
    """

    # Все действия требуют авторизации и проверки, что пользователь — владелец
    permission_classes = [permissions.IsAuthenticated(), IsOwnerOnly()]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        """Ограничиваем выборку только документами текущего пользователя."""
        return Document.objects.filter(user=self.request.user)

    # ============================================================
    # 4. Замена файла (владелец)
    # ============================================================

    @action(detail=True, methods=["post"])
    def update_file(self, request, pk=None):
        """
        Заменяет файл и отправляет документ на повторную проверку.
        Статус становится 'pending'.
        """
        document = self.get_object()
        new_file = request.FILES.get("file")

        # Проверяем, что файл передан
        if not new_file:
            return Response(
                {"error": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Вызываем бизнес-логику
        result = replace_document_file(document, new_file, request.user)
        return Response(result)

    # ============================================================
    # 5. Отправка на проверку (владелец)
    # ============================================================

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Отправляет черновик на проверку модератору.
        Статус меняется с 'draft' на 'pending'.
        """
        document = self.get_object()

        # Проверяем, что документ действительно в статусе "черновик"
        try:
            validate_document_status(document, "draft")
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Отправляем на проверку
        result = send_document_to_review(document, request.user)
        return Response(result)


class DocumentModerationViewSet(viewsets.GenericViewSet):
    """
    Действия, доступные только модератору:
    - POST /api/documents/{id}/approve/   -> подтвердить
    - POST /api/documents/{id}/reject/   -> отклонить
    """

    permission_classes = [permissions.IsAuthenticated()]
    queryset = Document.objects.all()

    # ============================================================
    # 6. Подтверждение документа (модератор)
    # ============================================================

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Подтверждает документ. Статус становится 'approved'.
        """
        # Проверяем глобальное право (есть ли у пользователя роль модератора)
        if not request.user.has_perm("documents.can_approve_document"):
            raise PermissionDenied("У вас нет права подтверждать документы")

        document = self.get_object()

        # Проверяем, что документ ещё не обработан
        try:
            validate_document_status(document, "pending")
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Подтверждаем
        result = approve_document(document, request.user)
        return Response(result)

    # ============================================================
    # 7. Отклонение документа (модератор)
    # ============================================================

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """
        Отклоняет документ. Статус становится 'rejected'.
        Комментарий с причиной обязателен.
        """
        # Проверяем глобальное право
        if not request.user.has_perm("documents.can_reject_document"):
            raise PermissionDenied("У вас нет права отклонять документы")

        document = self.get_object()

        # Проверяем, что документ ещё не обработан
        try:
            validate_document_status(document, "pending")
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, что комментарий передан
        comment = request.data.get("comment", "").strip()
        if not comment:
            return Response(
                {"error": "Укажите причину отклонения"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Отклоняем
        result = reject_document(document, request.user, comment)
        return Response(result)
