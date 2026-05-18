from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .apps import DocumentsConfig
from .views import (DocumentModerationViewSet, DocumentOwnerViewsSet,
                    DocumentViewSet)

app_name = DocumentsConfig.name


# ROUTER — автоматически создаёт URL для ViewSet
router = DefaultRouter()
router.register(r"", DocumentViewSet, basename="documents")

# После регистрации router создаются такие URL-маршруты:
# GET    /documents/        → список
# POST   /documents/        → создать
# GET    /documents/{id}/   → просмотр
# DELETE /documents/{id}/   → удалить
# POST    /documents/{id}/update-file/   → обновить документ
# POST  /documents/{id}/submit/   → отправить черновик документа на проверку
# POST  /documents/{id}/approve/   → подтвердить документ
# POST  /documents/{id}/reject/   → отклонить документ

urlpatterns = [
    # Все URL от router (CRUD для документа)
    path("", include(router.urls)),
    # Обновление документа владельцем
    path(
        "<int:pk>/update-file/", DocumentOwnerViewsSet.as_view({"post": "update_file"})
    ),
    # Отправка черновика документа на проверку модератору
    path("<int:pk>/submit/", DocumentOwnerViewsSet.as_view({"post": "submit"})),
    # Подтверждение документа модератором
    path("<int:pk>/approve/", DocumentModerationViewSet.as_view({"post": "approve"})),
    # Отклонение документа модератором
    path("<int:pk>/reject/", DocumentModerationViewSet.as_view({"post": "reject"})),
]
