"""
Тесты для приложения users.

Проверяют:
- Регистрацию пользователя
- Получение JWT токенов
- Просмотр и редактирование профиля
- Мягкое удаление и восстановление профиля
- Права доступа
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()


# ============================================================================
# НАСТРОЙКИ ДЛЯ ТЕСТОВ (ОТКЛЮЧАЕМ CELERY)
# ============================================================================
# Эти настройки позволяют тестам не зависеть от Redis
# Celery задачи выполняются синхронно (сразу), а не уходят в очередь
CELERY_TEST_SETTINGS = {
    'CELERY_TASK_ALWAYS_EAGER': True,
    'CELERY_TASK_EAGER_PROPAGATES': True,
    'CELERY_BROKER_URL': 'memory://',
}


@override_settings(**CELERY_TEST_SETTINGS)
class UserAPITestCase(TestCase):
    """Тестирование API для работы с пользователями."""

    def setUp(self):
        """Подготовка данных перед каждым тестом."""
        self.client = APIClient()

        # ================================================================
        # 1. ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ
        # ================================================================
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Тест',
            last_name='Пользователь',
            phone='+79123456789'
        )

        # ================================================================
        # 2. СУПЕРПОЛЬЗОВАТЕЛЬ (АДМИН) — для восстановления
        # ================================================================
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123',
            first_name='Админ',
            last_name='Админов'
        )

        # ================================================================
        # 3. МОДЕРАТОР — не имеет права восстанавливать
        # ================================================================
        group, _ = Group.objects.get_or_create(name='Document Moderator')
        self.moderator = User.objects.create_user(
            email='moderator@example.com',
            password='moderator123',
            first_name='Модератор',
            last_name='Модераторов',
            is_staff=True,
        )
        self.moderator.groups.add(group)

        # ================================================================
        # 4. JWT ТОКЕНЫ
        # ================================================================
        user_token_response = self.client.post(
            reverse('users:token_obtain_pair'),
            {'email': 'testuser@example.com', 'password': 'testpass123'},
            format='json'
        )
        self.user_token = user_token_response.data.get('access')

        admin_token_response = self.client.post(
            reverse('users:token_obtain_pair'),
            {'email': 'admin@example.com', 'password': 'admin123'},
            format='json'
        )
        self.admin_token = admin_token_response.data.get('access')

        moderator_token_response = self.client.post(
            reverse('users:token_obtain_pair'),
            {'email': 'moderator@example.com', 'password': 'moderator123'},
            format='json'
        )
        self.moderator_token = moderator_token_response.data.get('access')

    # ========================================================================
    # ТЕСТ 1: РЕГИСТРАЦИЯ
    # ========================================================================

    def test_register_user_success(self):
        """Регистрация с корректными данными → 201 Created."""
        url = reverse('users:user_register')
        data = {
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'first_name': 'Новый',
            'last_name': 'Пользователь',
            'phone': '+79876543210'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')
        self.assertNotIn('password', response.data)

        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.first_name, 'Новый')
        self.assertEqual(user.last_name, 'Пользователь')

    def test_register_user_duplicate_email_fails(self):
        """Регистрация с существующим email → 400 Bad Request."""
        url = reverse('users:user_register')
        data = {
            'email': 'testuser@example.com',
            'password': 'newpass123',
            'first_name': 'Дубликат',
            'last_name': 'Пользователь'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_user_missing_fields_fails(self):
        """Регистрация без email/password → 400 Bad Request."""
        url = reverse('users:user_register')
        data = {
            'first_name': 'Неполный',
            'last_name': 'Пользователь'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)

    def test_register_with_deleted_email_fails(self):
        """
        Проверка: удалённый пользователь не может зарегистрироваться снова.
        Ожидается: 400 Bad Request с сообщением об обращении к администратору.
        """
        # Создаём пользователя и мягко удаляем его
        deleted_user = User.objects.create_user(
            email='deleted@example.com',
            password='pass123',
            first_name='Удалённый',
            last_name='Пользователь'
        )
        deleted_user.soft_delete()

        url = reverse('users:user_register')
        data = {
            'email': 'deleted@example.com',
            'password': 'newpass123',
            'first_name': 'Новый',
            'last_name': 'Пользователь'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('администратор', str(response.data).lower())

    # ========================================================================
    # ТЕСТ 2: JWT ТОКЕНЫ
    # ========================================================================

    def test_token_obtain_success(self):
        """Верные email/пароль → 200 OK, access и refresh токены."""
        url = reverse('users:token_obtain_pair')
        data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_token_obtain_wrong_password_fails(self):
        """Неверный пароль → 401 Unauthorized."""
        url = reverse('users:token_obtain_pair')
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_success(self):
        """Обновление access токена по refresh → 200 OK."""
        token_url = reverse('users:token_obtain_pair')
        token_data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }
        token_response = self.client.post(token_url, token_data, format='json')
        refresh_token = token_response.data.get('refresh')

        refresh_url = reverse('users:token_refresh')
        response = self.client.post(refresh_url, {'refresh': refresh_token}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    # ========================================================================
    # ТЕСТ 3: ПРОСМОТР ПРОФИЛЯ
    # ========================================================================

    def test_profile_retrieve_success(self):
        """Авторизованный пользователь видит свой профиль → 200 OK."""
        url = reverse('users:user_profile')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'testuser@example.com')
        self.assertEqual(response.data['first_name'], 'Тест')
        self.assertEqual(response.data['last_name'], 'Пользователь')

    def test_profile_retrieve_unauthenticated_fails(self):
        """Неавторизованный пользователь не видит профиль → 401."""
        url = reverse('users:user_profile')
        self.client.credentials()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ========================================================================
    # ТЕСТ 4: РЕДАКТИРОВАНИЕ ПРОФИЛЯ
    # ========================================================================

    def test_profile_update_success(self):
        """PATCH с корректными данными → 200 OK, данные обновлены."""
        url = reverse('users:user_profile')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')

        response = self.client.patch(
            url,
            {'first_name': 'НовоеИмя', 'phone': '+79998887766'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'НовоеИмя')
        self.assertEqual(response.data['phone'], '+79998887766')

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'НовоеИмя')
        self.assertEqual(self.user.phone, '+79998887766')

    def test_profile_update_email_is_readonly(self):
        """Поле email нельзя изменить → 200 OK, email не меняется."""
        url = reverse('users:user_profile')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')

        response = self.client.patch(
            url,
            {'email': 'newemail@example.com'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'testuser@example.com')

    def test_profile_update_avatar_success(self):
        """Загрузка аватара → 200 OK, аватар сохранён."""
        url = reverse('users:user_profile')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')

        avatar_content = b'GIF89a\x01\x00\x01\x00\x00\xff\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        avatar = SimpleUploadedFile('avatar.gif', avatar_content, content_type='image/gif')

        response = self.client.patch(
            url,
            {'avatar': avatar},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data.get('avatar'))

    # ========================================================================
    # ТЕСТ 5: МЯГКОЕ УДАЛЕНИЕ ПРОФИЛЯ
    # ========================================================================

    def test_soft_delete_profile_success(self):
        """Мягкое удаление профиля → 204, is_active=False, deleted_at заполнено."""
        url = reverse('users:user_soft_delete')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.deleted_at)
        self.assertTrue(self.user.is_deleted)

    def test_soft_deleted_user_cannot_login(self):
        """Удалённый пользователь не может войти → 401."""
        self.user.soft_delete()

        url = reverse('users:token_obtain_pair')
        data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ========================================================================
    # ТЕСТ 6: ВОССТАНОВЛЕНИЕ ПРОФИЛЯ
    # ========================================================================

    def test_restore_profile_by_admin_success(self):
        """Админ (суперпользователь) восстанавливает удалённого пользователя → 200 OK."""
        # Удаляем пользователя
        self.user.soft_delete()
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_deleted)

        url = reverse('users:user_restore', args=[self.user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('восстановлен', response.data['detail'].lower())

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.deleted_at)
        self.assertFalse(self.user.is_deleted)

    def test_moderator_cannot_restore_user(self):
        """Модератор не может восстановить пользователя → 403 Forbidden."""
        self.user.soft_delete()
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_deleted)

        url = reverse('users:user_restore', args=[self.user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.moderator_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_restore_not_deleted_user_fails(self):
        """Восстановление не удалённого пользователя → 404."""
        url = reverse('users:user_restore', args=[self.user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('не найден', response.data['error'].lower())

    def test_restore_nonexistent_user_fails(self):
        """Восстановление несуществующего пользователя → 404."""
        url = reverse('users:user_restore', args=[99999])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ========================================================================
    # ТЕСТ 7: МЕТОДЫ МОДЕЛИ
    # ========================================================================

    def test_get_full_name(self):
        """get_full_name() возвращает 'Имя Фамилия'."""
        self.assertEqual(self.user.get_full_name(), 'Тест Пользователь')

    def test_get_short_name(self):
        """get_short_name() возвращает только имя."""
        self.assertEqual(self.user.get_short_name(), 'Тест')

    def test_get_full_name_without_last_name(self):
        """get_full_name() без фамилии возвращает только имя."""
        user = User.objects.create_user(
            email='nofirst@example.com',
            password='pass123',
            first_name='Только'
        )
        self.assertEqual(user.get_full_name(), 'Только')

    def test_is_deleted_property(self):
        """is_deleted правильно определяет удалённого пользователя."""
        self.assertFalse(self.user.is_deleted)
        self.user.soft_delete()
        self.assertTrue(self.user.is_deleted)

    # ========================================================================
    # ТЕСТ 8: ДОСТУП К ЭНДПОИНТАМ
    # ========================================================================

    def test_profile_endpoint_requires_auth(self):
        """Эндпоинт профиля требует авторизации."""
        url = reverse('users:user_profile')
        self.client.credentials()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.patch(url, {'first_name': 'test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_soft_delete_endpoint_requires_auth(self):
        """Эндпоинт удаления требует авторизации."""
        url = reverse('users:user_soft_delete')
        self.client.credentials()

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_restore_by_user_manager_success(self):
        """Пользователь из группы User Manager может восстановить аккаунт."""
        # Создаём группу и добавляем в неё пользователя
        group, _ = Group.objects.get_or_create(name='User Manager')
        self.user_manager = User.objects.create_user(
            email='manager@example.com',
            password='manager123',
            first_name='Менеджер',
            last_name='Пользователей'
        )
        self.user_manager.groups.add(group)

        # Получаем токен
        token_response = self.client.post(
            reverse('users:token_obtain_pair'),
            {'email': 'manager@example.com', 'password': 'manager123'},
            format='json'
        )
        manager_token = token_response.data.get('access')

        # Удаляем пользователя
        self.user.soft_delete()

        # Восстанавливаем
        url = reverse('users:user_restore', args=[self.user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {manager_token}')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)