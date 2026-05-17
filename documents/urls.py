from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .apps import DocumentsConfig
from .views import DocumentViewSet

app_name = DocumentsConfig.name


# ROUTER — автоматически создаёт URL для ViewSet
router = DefaultRouter()
router.register(r"", DocumentViewSet, basename="documents")

# После регистрации router создаются такие URL-маршруты:
# GET    /documents/        → список
# POST   /documents/        → создать
# GET    /documents/{id}/   → просмотр
# PUT    /documents/{id}/   → обновить
# PATCH  /documents/{id}/   → частично обновить
# DELETE /documents/{id}/   → удалить

urlpatterns = [
    # Все URL от router (CRUD для документа)
    path("", include(router.urls)),
]
