from django.core.exceptions import PermissionDenied
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from documents.models import Document
from users.permissions import IsModerator, IsOwnerOnly
from documents.serializers import DocumentSerializer
from documents.services import (approve_document, reject_document,
                                replace_document_file, send_document_to_review)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Основной ViewSet для работы с документами (CRUD + создание).

    Доступные эндпоинты (все требуют авторизации):
    - POST   /api/documents/           -> создать новый документ (обязательно поле user_note)
    - GET    /api/documents/           -> список документов (свои или все, зависит от прав)
    - GET    /api/documents/{id}/      -> просмотр одного документа
    - DELETE /api/documents/{id}/      -> удалить документ (только владелец)
    """

    # Сериализатор для преобразования объектов Document в JSON и обратно
    serializer_class = DocumentSerializer

    def get_queryset(self):
        """
        Определяет, какие документы видит пользователь в списке.
        """
        user = self.request.user

        # Неавторизованные пользователи не видят документов
        if not user.is_authenticated:
            return Document.objects.none()

        # Модераторы видят все документы, кроме черновиков и документов удалённых пользователей
        if user.has_perm("documents.can_view_all_documents"):
            return Document.objects.filter(
                user__deleted_at__isnull=True  # исключаем документы удалённых пользователей
            ).exclude(
                status="draft"
            )  # исключаем черновики

        # Обычный пользователь видит только свои документы
        return Document.objects.filter(user=user)

    def get_permissions(self):
        """
        Назначает разные права доступа для разных действий (эндпоинтов).

        - destroy (удаление) — только авторизованный пользователь и владелец документа
        - остальные действия (list, create, retrieve) — только авторизация
        """
        # Удалить документ может только его владелец (проверка через кастомный permission)
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsOwnerOnly()]

        # Все остальные действия требуют только авторизации
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        """
        Вызывается при создании нового документа (POST /api/documents/).

        1. Проверяем, что пользователь не модератор (модераторы не могут создавать документы)
        2. Сохраняем документ, автоматически подставляя текущего пользователя в поле user
        3. Логируем действие "создан" в историю изменений документа
        """
        user = self.request.user

        # Модераторы (состоящие в группе Document Moderator) не могут создавать документы
        if user.groups.filter(name="Document Moderator").exists():
            raise PermissionDenied("Модераторы не могут создавать документы")

        # Сохраняем документ, подставляя автора
        document = serializer.save(user=user)

        # Записываем в историю: кто, когда и какое действие выполнил
        document.log_action(user=user, action="created", new_status="draft")

    def perform_destroy(self, instance):
        """Удаление документа с логированием"""
        user = self.request.user

        # Логируем удаление
        instance.log_action(
            user=user,
            action='deleted',
            old_status=instance.status,
            new_status=None
        )

        # Удаляем файл с диска
        if instance.file:
            instance.file.delete(save=False)

        # Удаляем запись из БД
        instance.delete()


class DocumentOwnerViewSet(viewsets.GenericViewSet):
    """
    ViewSet для действий, доступных ТОЛЬКО ВЛАДЕЛЬЦУ документа.

    Доступные эндпоинты:
    - POST /api/documents/{id}/update-file/   -> заменить файл документа
    - POST /api/documents/{id}/submit/       -> отправить черновик на проверку модератору

    Все действия требуют авторизации и проверки, что пользователь является владельцем документа.
    """

    # Проверяем, что пользователь авторизован И является владельцем документа
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]

    def get_queryset(self):
        """
        Ограничиваем выборку только документами текущего пользователя для оптимизации запросов.
        """
        return Document.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def update_file(self, request, pk=None):
        """
        Заменяет файл документа (например, после отклонения модератором).

        Особенности:
        - После замены файла статус документа автоматически становится 'pending'
        - Документ снова отправляется на проверку модератору
        - Старые данные модерации (комментарий, кто проверил, дата) сбрасываются
        """
        document = self.get_object()
        new_file = request.FILES.get("file")

        # Проверяем, что пользователь действительно приложил файл
        if not new_file:
            return Response({"error": "Файл не передан"}, status=400)

        # Вызываем бизнес-логику замены файла из сервисного слоя
        result = replace_document_file(document, new_file, request.user)
        return Response(result)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Отправляет черновик (draft) на проверку модератору.

        Особенности:
        - Статус меняется с 'draft' на 'pending'
        - Модератор увидит документ в своей очереди на проверку
        - Документ должен быть в статусе 'draft', иначе вернётся ошибка
        """
        document = self.get_object()

        # Проверка статуса (черновик)
        if document.status != "draft":
            return Response(
                {"error": f"Документ уже в статусе: {document.get_status_display()}"},
                status=400,
            )

        # Вызываем бизнес-логику отправки на проверку
        result = send_document_to_review(document, request.user)
        return Response(result)


class DocumentModerationViewSet(viewsets.GenericViewSet):
    """
    ViewSet для действий, доступных ТОЛЬКО МОДЕРАТОРУ.

    Доступные эндпоинты:
    - POST /api/documents/{id}/approve/   -> подтвердить документ
    - POST /api/documents/{id}/reject/   -> отклонить документ (с обязательным комментарием)

    Все действия требуют прав модератора (проверка через кастомный permission IsModerator).
    """

    # Проверяем, что пользователь имеет права модератора (группа Document Moderator)
    permission_classes = [permissions.IsAuthenticated, IsModerator]

    # Ограничиваем выборку только документами, ожидающими проверки (status='pending')
    # Также исключаем документы удалённых пользователей
    queryset = Document.objects.filter(status="pending", user__deleted_at__isnull=True)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Подтверждает документ.

        Что происходит:
        - Статус документа меняется на 'approved'
        - Заполняется поле reviewed_by (кто подтвердил)
        - Заполняется поле reviewed_at (дата подтверждения)
        - Пользователю отправляется уведомление на email
        """
        document = self.get_object()
        result = approve_document(document, request.user)
        return Response(result)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """
        Отклоняет документ с указанием причины.

        Что происходит:
        - Статус документа меняется на 'rejected'
        - Сохраняется комментарий модератора (причина отклонения)
        - Заполняются поля reviewed_by и reviewed_at
        - Пользователю отправляется уведомление на email с причиной отказа

        Комментарий обязателен — пользователь должен знать, что исправить.
        """
        document = self.get_object()

        # Получаем комментарий из тела запроса и удаляем лишние пробелы
        comment = request.data.get("comment", "").strip()

        # Комментарий обязателен — без него документ нельзя отклонить
        if not comment:
            return Response({"error": "Укажите причину отклонения"}, status=400)

        # Вызываем бизнес-логику отклонения
        result = reject_document(document, request.user, comment)
        return Response(result)
