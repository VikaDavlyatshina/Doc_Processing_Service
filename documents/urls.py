from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .apps import DocumentsConfig
from .views import (DocumentModerationViewSet, DocumentOwnerViewSet,
                    DocumentViewSet)

app_name = DocumentsConfig.name

# ============================================================================
# ROUTER ДЛЯ БАЗОВОГО CRUD
# ============================================================================
# DefaultRouter автоматически создаёт стандартные URL для ViewSet:
#   GET    /documents/        → список документов
#   POST   /documents/        → создать документ
#   GET    /documents/{id}/   → просмотр одного документа
#   DELETE /documents/{id}/   → удалить документ
# ============================================================================
router = DefaultRouter()
router.register(r"", DocumentViewSet, basename="documents")

urlpatterns = [
    # Базовые CRUD-маршруты (создание, список, просмотр, удаление)
    path("", include(router.urls)),
    # Замена файла документа (после отклонения или для обновления)
    path(
        "<int:pk>/update-file/",
        DocumentOwnerViewSet.as_view({"post": "update_file"}),
        name="document-update-file",
    ),
    # Отправка черновика на проверку модератору
    path(
        "<int:pk>/submit/",
        DocumentOwnerViewSet.as_view({"post": "submit"}),
        name="document-submit",
    ),
    # ========================================================================
    # ДЕЙСТВИЯ МОДЕРАТОРА (только для пользователей с правами модератора)
    # ========================================================================
    # Подтверждение документа (статус → approved)
    path(
        "<int:pk>/approve/",
        DocumentModerationViewSet.as_view({"post": "approve"}),
        name="document-approve",
    ),
    # Отклонение документа с комментарием (статус → rejected)
    path(
        "<int:pk>/reject/",
        DocumentModerationViewSet.as_view({"post": "reject"}),
        name="document-reject",
    ),
]
