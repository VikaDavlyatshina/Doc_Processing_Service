from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.permissions import IsUserManager
from users.serializers import UserCreateSerializer, UserSerializer


@extend_schema_view(
    post=extend_schema(
        summary="📝 Регистрация пользователя",
        description="Создаёт нового пользователя. Доступно всем (без авторизации).",
        request=UserCreateSerializer,
        responses={201: UserCreateSerializer},
        tags=["users"],
    )
)
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


@extend_schema_view(
    get=extend_schema(
        summary="👤 Просмотр профиля",
        description="Возвращает профиль текущего авторизованного пользователя.",
        responses={200: UserSerializer},
        tags=["users-profile"],
    ),
    patch=extend_schema(
        summary="👤 Редактирование профиля",
        description="Обновляет профиль текущего пользователя. Поддерживает загрузку аватара (multipart/form-data).",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string", "description": "Имя"},
                    "last_name": {"type": "string", "description": "Фамилия"},
                    "phone": {"type": "string", "description": "Телефон"},
                    "avatar": {
                        "type": "string",
                        "format": "binary",
                        "description": "Аватар (JPG, PNG, GIF, до 5 МБ)",
                    },
                },
                "required": [],
            }
        },
        responses={200: UserSerializer},
        tags=["users-profile"],
    ),
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Просмотр и редактирование своего профиля.
    Требует авторизации.
    """

    # Доступные методы
    http_method_names = ["get", "patch"]

    # Какой сериализатор использовать
    serializer_class = UserSerializer

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # Переопределяем get_object, чтобы получить текущего пользователя
    def get_object(self):
        """Возвращает текущего авторизованного пользователя."""
        return self.request.user


class UserSoftDeleteView(APIView):
    """
    Мягкое удаление (деактивация) своего профиля.
    Пользователь не может войти, но данные сохраняются.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Мягкое удаление профиля",
        description="Деактивирует аккаунт текущего пользователя. Пользователь не может войти, но данные сохраняются.",
        request=None,
        responses={
            204: None,
            400: {"description": "Профиль уже удалён или пользователь администратор"},
        },
        tags=["users-profile"],
    )
    def delete(self, request):
        user = request.user

        # Если пользователь уже удален - возвращаем сообщение об ошибке
        if user.is_deleted:
            return Response(
                {"error": "Профиль уже удалён"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Нельзя деактивировать администратора через API
        if user.is_staff:
            return Response(
                {"error": "Нельзя деактивировать администратора через API"},
                status=status.HTTP_400_BAD_REQUEST,
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

    @extend_schema(
        summary="🔒 Восстановление пользователя (только менеджер)",
        description="Восстанавливает удалённый аккаунт. Доступно только менеджерам пользователей.",
        request=None,
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            404: {"description": "Удалённый пользователь не найден"},
        },
        tags=["users-admin"],
    )
    def post(self, request, user_id):
        # Ищем удалённого пользователя через _base_manager,
        # так как обычный менеджер скрывает пользователей с deleted_at
        user = User._base_manager.filter(id=user_id, deleted_at__isnull=False).first()

        if not user:
            return Response(
                {"error": "Удалённый пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Восстанавливаем пользователя, сохраняя данные о том, кто выполнил действие
        user.restore(performed_by=request.user)
        return Response({"detail": f"Пользователь {user.email} восстановлен"})
