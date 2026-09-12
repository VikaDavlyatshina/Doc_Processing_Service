"""
Тесты для приложения users.

Проверяют:
- Регистрацию
- JWT-токены
- Профиль
- Мягкое удаление
- Восстановление
- Права доступа
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

# Celery выполняем синхронно, без Redis
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


@override_settings(**CELERY_TEST_SETTINGS)
class UserAPITestCase(TestCase):
    """Тесты API пользователей."""

    def setUp(self):
        self.client = APIClient()

        # Пользователи
        self.user = User.objects.create_user(
            email="user@example.com",
            password="user123",
            first_name="Иван",
            last_name="Иванов",
        )

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="admin123",
        )

        # Менеджер пользователей (может восстанавливать)
        group, _ = Group.objects.get_or_create(name="User Manager")
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="manager123",
        )
        self.manager.groups.add(group)

        # Модератор документов (не может восстанавливать)
        group, _ = Group.objects.get_or_create(name="Document Moderator")
        self.moderator = User.objects.create_user(
            email="moderator@example.com",
            password="moderator123",
            is_staff=True,
        )
        self.moderator.groups.add(group)

        # Токены для всех ролей
        self.user_token = _get_token(self.client, "user@example.com", "user123")
        self.admin_token = _get_token(self.client, "admin@example.com", "admin123")
        self.manager_token = _get_token(
            self.client, "manager@example.com", "manager123"
        )
        self.moderator_token = _get_token(
            self.client, "moderator@example.com", "moderator123"
        )

    # ========================================================================
    # РЕГИСТРАЦИЯ
    # ========================================================================

    def test_register_success(self):
        """Успешная регистрация → 201."""
        url = reverse("users:user_register")
        data = {
            "email": "new@example.com",
            "password": "newpass123",
            "first_name": "Пётр",
            "last_name": "Петров",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "new@example.com")
        self.assertNotIn("password", response.data)

    def test_register_duplicate_email(self):
        """Повторный email → 400."""
        url = reverse("users:user_register")
        data = {"email": "user@example.com", "password": "pass123"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_missing_fields(self):
        """Без email и пароля → 400."""
        url = reverse("users:user_register")
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("password", response.data)

    def test_register_deleted_email(self):
        """Удалённый email → 400."""
        deleted = User.objects.create_user(
            email="deleted@example.com", password="pass123"
        )
        deleted.soft_delete()

        url = reverse("users:user_register")
        data = {"email": "deleted@example.com", "password": "newpass123"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ========================================================================
    # JWT-ТОКЕНЫ
    # ========================================================================

    def test_token_obtain_success(self):
        """Верный логин/пароль → access + refresh."""
        url = reverse("users:token_obtain_pair")
        data = {"email": "user@example.com", "password": "user123"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_wrong_password(self):
        """Неверный пароль → 401."""
        url = reverse("users:token_obtain_pair")
        data = {"email": "user@example.com", "password": "wrong"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_success(self):
        """Обновление access по refresh → 200."""
        # Получаем refresh
        url = reverse("users:token_obtain_pair")
        data = {"email": "user@example.com", "password": "user123"}
        tokens = self.client.post(url, data, format="json")
        refresh = tokens.data["refresh"]

        # Обновляем
        url = reverse("users:token_refresh")
        response = self.client.post(url, {"refresh": refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    # ========================================================================
    # ПРОФИЛЬ
    # ========================================================================

    def test_profile_get(self):
        """Просмотр своего профиля → 200."""
        url = reverse("users:user_profile")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@example.com")

    def test_profile_update(self):
        """Редактирование профиля → 200."""
        url = reverse("users:user_profile")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.patch(url, {"first_name": "Пётр"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Пётр")

    def test_profile_email_readonly(self):
        """Email нельзя изменить."""
        url = reverse("users:user_profile")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        response = self.client.patch(url, {"email": "hack@example.com"}, format="json")
        self.assertEqual(response.data["email"], "user@example.com")

    # ========================================================================
    # SOFT DELETE
    # ========================================================================

    def test_soft_delete(self):
        """Удаление → 204, флаги is_active=False, вход запрещён."""
        # Удаляем
        url = reverse("users:user_soft_delete")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверяем флаги
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.is_deleted)

        # Пробуем войти
        token_url = reverse("users:token_obtain_pair")
        data = {"email": "user@example.com", "password": "user123"}
        response = self.client.post(token_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ========================================================================
    # ВОССТАНОВЛЕНИЕ
    # ========================================================================

    def _delete_and_restore(self, token, expected_status):
        """Хелпер: удалить пользователя и попытаться восстановить."""
        self.user.soft_delete()
        url = reverse("users:user_restore", args=[self.user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post(url)
        self.assertEqual(response.status_code, expected_status)
        return response

    def test_restore_by_admin(self):
        """Админ восстанавливает → 200."""
        self._delete_and_restore(self.admin_token, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_restore_by_manager(self):
        """Менеджер пользователей восстанавливает → 200."""
        self._delete_and_restore(self.manager_token, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_restore_by_moderator_forbidden(self):
        """Модератор документов не может → 403."""
        self._delete_and_restore(self.moderator_token, status.HTTP_403_FORBIDDEN)

    def test_restore_not_deleted(self):
        """Не удалённый пользователь → 404."""
        url = reverse("users:user_restore", args=[self.user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ========================================================================
    # ПРАВА ДОСТУПА
    # ========================================================================

    def test_unauthorized_access(self):
        """Все эндпоинты без токена → 401."""
        endpoints = [
            ("get", "users:user_profile"),
            ("patch", "users:user_profile"),
            ("delete", "users:user_soft_delete"),
        ]
        self.client.credentials()  # Сбрасываем токен

        for method, url_name in endpoints:
            url = reverse(url_name)
            response = getattr(self.client, method)(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"{method.upper()} {url_name} должен требовать авторизацию",
            )

    def test_register_weak_password(self):
        """Слишком простой пароль → 400."""
        url = reverse("users:user_register")
        data = {
            "email": "weak@example.com",
            "password": "123",
            "first_name": "Слабый",
            "last_name": "Пароль",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_numeric_password(self):
        """Пароль только из цифр → 400."""
        url = reverse("users:user_register")
        data = {
            "email": "numeric@example.com",
            "password": "12345678",
            "first_name": "Цифры",
            "last_name": "Пароль",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_empty_first_name(self):
        """Пустое имя → 400."""
        url = reverse("users:user_register")
        data = {
            "email": "noname@example.com",
            "password": "ValidPass123!",
            "first_name": "",
            "last_name": "Фамилия",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_empty_last_name(self):
        """Пустая фамилия → 400."""
        url = reverse("users:user_register")
        data = {
            "email": "noname@example.com",
            "password": "ValidPass123!",
            "first_name": "Имя",
            "last_name": "",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_avatar_too_large(self):
        """Аватар больше 5 МБ → 400."""
        url = reverse("users:user_profile")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        large_file = SimpleUploadedFile(
            "large.jpg",
            b"X" * (6 * 1024 * 1024),
            content_type="image/jpeg",
        )

        response = self.client.patch(url, {"avatar": large_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_avatar_not_image(self):
        """Не изображение в аватар → 400."""
        url = reverse("users:user_profile")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        not_image = SimpleUploadedFile(
            "doc.pdf",
            b"%PDF-1.4\nfake pdf",
            content_type="application/pdf",
        )

        response = self.client.patch(url, {"avatar": not_image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
