from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from users.views import (UserCreateAPIView, UserProfileView, UserRestoreView,
                         UserSoftDeleteView)

app_name = "users"

urlpatterns = [
    # ========================================================================
    # АВТОРИЗАЦИЯ
    # ========================================================================
    # POST /api/users/token/ - получить access и refresh токены (логин)
    # POST /api/users/token/refresh/ - обновить access токен по refresh
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # ========================================================================
    # РЕГИСТРАЦИЯ
    # ========================================================================
    # POST /api/users/register/ - создать нового пользователя (доступно всем)
    path("register/", UserCreateAPIView.as_view(), name="user_register"),
    # ========================================================================
    # ПРОФИЛЬ
    # ========================================================================
    # GET    /api/users/profile/ - просмотр своего профиля
    # PATCH  /api/users/profile/ - обновление профиля
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    # ========================================================================
    # УДАЛЕНИЕ ПРОФИЛЯ
    # ========================================================================
    # DELETE /api/users/profile/delete/ - мягкое удаление (деактивация)
    # Пользователь не может войти, но данные сохраняются
    path("profile/delete/", UserSoftDeleteView.as_view(), name="user_soft_delete"),
    # ========================================================================
    # ВОССТАНОВЛЕНИЕ ПРОФИЛЯ (только администратор)
    # ========================================================================
    # POST /api/users/profile/restore/<id>/ - восстановить удалённого пользователя
    path(
        "profile/restore/<int:user_id>/", UserRestoreView.as_view(), name="user_restore"
    ),
]
