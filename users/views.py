from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.permissions import IsUserManager
from users.serializers import UserCreateSerializer, UserSerializer


class UserCreateAPIView(generics.CreateAPIView):
    """
    Регистрация нового пользователя.
    Доступна всем (не требует авторизации).
    """
    # queryset требуется для работы CreateAPIView
    queryset = User.objects.all()

    # Какой сериализатор использовать для преобразования данных
    serializer_class = UserCreateSerializer

    # Разрешаем доступ всем (без токена)
    permission_classes = [permissions.AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Просмотр и редактирование своего профиля.
    Требует авторизации.
    """
    # Какой сериализатор использовать
    serializer_class = UserSerializer

    # Переопределяем get_object, чтобы получить текущего пользователя
    def get_object(self):
        """Возвращает текущего авторизованного пользователя."""
        return self.request.user


class UserSoftDeleteView(APIView):
    """
    Мягкое удаление (деактивация) своего профиля.
    Пользователь не может войти, но данные сохраняются.
    """

    def delete(self, request):
        user = request.user

        # Если пользователь уже удален - возвращаем сообщение об ошибке
        if user.is_deleted:
            return Response(
                {"error": "Профиль уже удалён"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Нельзя деактивировать администратора через API
        if user.is_staff:
            return Response(
                {"error": "Нельзя деактивировать администратора через API"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Выполняем мягкое удаление, сохраняя данные о том, кто выполнил действие
        user.soft_delete(performed_by=user)
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserRestoreView(APIView):
    """
    Восстановление аккаунта пользователя.
    Доступно для менеджеров пользователей.
    """
    # Только администраторы пользователей могут восстанавливать пользователей
    permission_classes = [permissions.IsAuthenticated, IsUserManager]

    def post(self, request, user_id):
        # Ищем удалённого пользователя через _base_manager,
        # так как обычный менеджер скрывает пользователей с deleted_at
        user = User._base_manager.filter(id=user_id, deleted_at__isnull=False).first()

        if not user:
            return Response(
                {"error": "Удалённый пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Восстанавливаем пользователя, сохраняя данные о том, кто выполнил действие
        user.restore(performed_by=request.user)
        return Response({"detail": f"Пользователь {user.email} восстановлен"})