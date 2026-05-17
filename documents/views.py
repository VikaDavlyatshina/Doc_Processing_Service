from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from documents.models import Document
from documents.permissions import IsOwnerOnly, CanApproveDocument, CanRejectDocument
from documents.serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):

    serializer_class = DocumentSerializer

    # Этот метод решает, какие документы увидит пользователь в списке
    def get_queryset(self):
        user = self.request.user

        # Если пользователь не залогинен — пустой список
        if not user.is_authenticated:
            return Document.objects.none()

        # Если есть право "видеть всё" — показываем все документы
        if user.has_perm('documents.can_view_all_documents'):
            return Document.objects.all()

        # Иначе — только свои
        return Document.objects.filter(user=user)

    # Этот метод решает, КАКИЕ права проверять для каждого действия
    def get_permissions(self):
        # Создать документ может любой залогиненный
        if self.action == 'create':
            return [permissions.IsAuthenticated()]

        # Просмотреть список или один документ — любой залогиненный
        # get_queryset сам ограничит список
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]

        # Изменить или удалить документ — только владелец
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOnly()]

        # Подтвердить документ — только с правом approve
        if self.action == 'approve':
            return [permissions.IsAuthenticated(), CanApproveDocument()]

        # Отклонить документ — только с правом reject
        if self.action == 'reject':
            return [permissions.IsAuthenticated(), CanRejectDocument()]

        # На всякий случай — требуем авторизацию
        return [permissions.IsAuthenticated()]

    # При создании документа подставляем автора
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # Эндпоинт для подтверждения
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        doc = self.get_object()
        if doc.status != 'pending':
            return Response({'error': 'Уже обработан'}, status=400)
        doc.approve(moderator=request.user)
        return Response({'status': 'approved'})

    # Эндпоинт для отклонения
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        doc = self.get_object()
        if doc.status != 'pending':
            return Response({'error': 'Уже обработан'}, status=400)
        comment = request.data.get('comment', '').strip()
        if not comment:
            return Response({'error': 'Укажите причину'}, status=400)
        doc.reject(moderator=request.user, comment=comment)
        return Response({'status': 'rejected'})