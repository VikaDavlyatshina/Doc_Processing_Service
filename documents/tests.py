"""
Тесты для приложения documents.

Проверяют:
- Загрузку документа
- Валидацию файлов
- Статусы документа
- Отправку на модерацию
- Замену файла
- Права доступа
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document

User = get_user_model()

CELERY_TEST_SETTINGS = {
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
    "CELERY_BROKER_URL": "memory://",
}


def _get_token(client, email, password):
    """Хелпер: получить JWT access токен."""
    url = reverse("users:token_obtain_pair")
    response = client.post(url, {"email": email, "password": password}, format="json")
    return response.data.get("access")


def _make_file(name="test.pdf", content_type="application/pdf", valid=True):
    """Хелпер: создать тестовый файл."""
    if valid and name.endswith(".pdf"):
        content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
    else:
        content = b"file_content"
    return SimpleUploadedFile(name, content, content_type=content_type)


def _create_document(user, user_note="Документ", status="draft"):
    """Хелпер: создать документ с файлом."""
    return Document.objects.create(
        user=user,
        file=_make_file(),
        user_note=user_note,
        status=status,
    )


@override_settings(**CELERY_TEST_SETTINGS)
class DocumentAPITestCase(TestCase):
    """Тесты API документов."""

    def setUp(self):
        self.client = APIClient()

        # Пользователи
        self.user = User.objects.create_user(
            email="user@example.com",
            password="user123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="other123",
        )

        # Модератор документов
        from django.contrib.auth.models import Group

        group, _ = Group.objects.get_or_create(name="Document Moderator")
        self.moderator = User.objects.create_user(
            email="moderator@example.com",
            password="moderator123",
            is_staff=True,
        )
        self.moderator.groups.add(group)

        # Токены
        self.user_token = _get_token(self.client, "user@example.com", "user123")
        self.other_token = _get_token(self.client, "other@example.com", "other123")
        self.moderator_token = _get_token(
            self.client, "moderator@example.com", "moderator123"
        )

    # ========================================================================
    # ЗАГРУЗКА
    # ========================================================================

    def _make_file(name="test.pdf", content_type="application/pdf", valid=True):
        """Хелпер: создать тестовый файл."""
        if valid and name.endswith(".pdf"):
            # Минимальный валидный PDF
            content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
        elif valid and (name.endswith(".doc") or name.endswith(".docx")):
            content = b"PK\x03\x04"  # сигнатура DOCX
        else:
            content = b"file_content"
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_upload_invalid_extension(self):
        """Файл .exe → 400."""
        url = reverse("documents:documents-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.post(
            url,
            {
                "file": _make_file("virus.exe", "application/x-msdownload"),
                "user_note": "Вирус",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_without_file(self):
        """Без файла → 400."""
        url = reverse("documents:documents-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.post(url, {"user_note": "Пусто"}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_unauthorized(self):
        """Без токена → 401."""
        url = reverse("documents:documents-list")
        response = self.client.post(
            url,
            {"file": _make_file(), "user_note": "Документ"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ========================================================================
    # ЗАМЕНА ФАЙЛА
    # ========================================================================

    def test_replace_file(self):
        """Замена файла до отправки → 200."""
        doc = _create_document(self.user, status="draft")

        url = reverse("documents:document-update-file", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.post(
            url,
            {"file": _make_file("new.pdf")},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_replace_after_submit_forbidden(self):
        """Нельзя заменить после отправки → 400."""
        doc = _create_document(self.user, status="pending")

        url = reverse("documents:document-update-file", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.post(
            url,
            {"file": _make_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_replace_by_other_user_not_found(self):
        """Чужой документ нельзя заменить → 404."""
        doc = _create_document(self.user, status="draft")

        url = reverse("documents:document-update-file", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_token}")

        response = self.client.post(url, {"file": _make_file()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ========================================================================
    # СТАТУСЫ И МОДЕРАЦИЯ
    # ========================================================================

    def test_submit_for_review(self):
        """Отправка на модерацию → статус pending."""
        doc = _create_document(self.user, status="draft")

        url = reverse("documents:document-submit", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc.refresh_from_db()
        self.assertEqual(doc.status, "pending")

    def test_submit_already_pending(self):
        """Нельзя отправить уже отправленный → 400."""
        doc = _create_document(self.user, status="pending")

        url = reverse("documents:document-submit", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_list_only_own(self):
        """Видит только свои документы."""
        _create_document(self.user, user_note="Мой")
        _create_document(self.other_user, user_note="Чужой")

        url = reverse("documents:documents-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)

    # ========================================================================
    # ПРАВА ДОСТУПА
    # ========================================================================

    def test_access_other_document_forbidden(self):
        """Чужой документ не виден → 404."""
        doc = _create_document(self.user, status="draft")

        url = reverse("documents:documents-detail", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_token}")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_file_too_large(self):
        """Файл больше 10 МБ → 400."""
        url = reverse("documents:documents-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        large_file = SimpleUploadedFile(
            "large.pdf",
            b"X" * (11 * 1024 * 1024),
            content_type="application/pdf",
        )

        response = self.client.post(
            url,
            {"file": large_file, "user_note": "Большой"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_empty_file(self):
        """Пустой файл → 400."""
        url = reverse("documents:documents-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        empty_file = SimpleUploadedFile(
            "empty.pdf",
            b"",
            content_type="application/pdf",
        )

        response = self.client.post(
            url,
            {"file": empty_file, "user_note": "Пустой"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_by_moderator(self):
        """Модератор подтверждает → статус approved."""
        doc = _create_document(self.user, status="pending")

        url = reverse("documents:document-approve", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.moderator_token}")

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc.refresh_from_db()
        self.assertEqual(doc.status, "approved")

    def test_reject_by_moderator(self):
        """Модератор отклоняет с комментарием → статус rejected."""
        doc = _create_document(self.user, status="pending")

        url = reverse("documents:document-reject", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.moderator_token}")

        response = self.client.post(
            url,
            {"comment": "Неверный формат файла"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc.refresh_from_db()
        self.assertEqual(doc.status, "rejected")

    def test_reject_without_comment(self):
        """Отклонение без комментария → 400."""
        doc = _create_document(self.user, status="pending")

        url = reverse("documents:document-reject", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.moderator_token}")

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_by_regular_user_forbidden(self):
        """Обычный пользователь не может подтвердить → 403."""
        doc = _create_document(self.user, status="pending")

        url = reverse("documents:document-approve", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_create_document(self):
        """Модератор не может создавать документы → 403."""
        url = reverse("documents:documents-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.moderator_token}")

        response = self.client.post(
            url,
            {"file": _make_file(), "user_note": "Документ"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_document(self):
        """Владелец удаляет документ."""
        doc = _create_document(self.user, status="draft")

        url = reverse("documents:documents-detail", args=[doc.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Document.objects.filter(id=doc.id).count(), 0)
