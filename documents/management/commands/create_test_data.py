"""
Скрипт для создания тестовых данных в проекте DocFlow.
Запуск: python manage.py shell < create_test_data.py
Или: python create_test_data.py (после настройки Django)
"""

from io import BytesIO
from PIL import Image


from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.utils import timezone

from documents.models import Document, DocumentLog

User = get_user_model()

print("=" * 60)
print("СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ ДЛЯ DOCFLOW")
print("=" * 60)


# ============================================================================
# 1. СОЗДАНИЕ ГРУПП (если не созданы)
# ============================================================================

print("\n1. Проверка и создание групп...")

# Группа модераторов документов
moderator_group, _ = Group.objects.get_or_create(name='Document Moderator')
print(f"   - Группа 'Document Moderator': {'существует' if not _ else 'создана'}")

# Группа менеджеров пользователей
user_manager_group, _ = Group.objects.get_or_create(name='User Manager')
print(f"   - Группа 'User Manager': {'существует' if not _ else 'создана'}")

# Группа админов (обычно не создаётся, но для полноты)
admin_group, _ = Group.objects.get_or_create(name='Admin')
print(f"   - Группа 'Admin': {'существует' if not _ else 'создана'}")


# ============================================================================
# 2. СОЗДАНИЕ ТЕСТОВЫХ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

print("\n2. Создание тестовых пользователей...")

# Суперпользователь (администратор)
admin, created = User.objects.get_or_create(
    email='admin@docflow.com',
    defaults={
        'first_name': 'Администратор',
        'last_name': 'Системы',
        'phone': '+79990000001',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
    }
)
if created:
    admin.set_password('Admin123!')
    admin.save()
    print(f"   ✅ Создан: {admin.email} (пароль: Admin123!)")
else:
    print(f"   📌 Существует: {admin.email}")

# Модератор документов
moderator, created = User.objects.get_or_create(
    email='moderator@docflow.com',
    defaults={
        'first_name': 'Модератор',
        'last_name': 'Документов',
        'phone': '+79990000002',
        'is_staff': True,
        'is_active': True,
    }
)
if created:
    moderator.set_password('Moderator123!')
    moderator.save()
    moderator.groups.add(moderator_group)
    print(f"   ✅ Создан: {moderator.email} (пароль: Moderator123!)")
else:
    print(f"   📌 Существует: {moderator.email}")

# Менеджер пользователей
user_manager, created = User.objects.get_or_create(
    email='usermanager@docflow.com',
    defaults={
        'first_name': 'Менеджер',
        'last_name': 'Пользователей',
        'phone': '+79990000003',
        'is_staff': True,
        'is_active': True,
    }
)
if created:
    user_manager.set_password('UserMan123!')
    user_manager.save()
    user_manager.groups.add(user_manager_group)
    print(f"   ✅ Создан: {user_manager.email} (пароль: UserMan123!)")
else:
    print(f"   📌 Существует: {user_manager.email}")

# Обычные пользователи
users = []
for i in range(1, 4):
    user, created = User.objects.get_or_create(
        email=f'user{i}@docflow.com',
        defaults={
            'first_name': f'Пользователь{i}',
            'last_name': f'Фамилия{i}',
            'phone': f'+7999000000{i}',
            'is_active': True,
        }
    )
    if created:
        user.set_password(f'User{i}123!')
        user.save()
        print(f"   ✅ Создан: {user.email} (пароль: User{i}123!)")
    else:
        print(f"   📌 Существует: {user.email}")
    users.append(user)

# Удалённый пользователь (для теста восстановления)
deleted_user, created = User.objects.get_or_create(
    email='deleted@docflow.com',
    defaults={
        'first_name': 'Удалённый',
        'last_name': 'Пользователь',
        'phone': '+79990000099',
        'is_active': False,
    }
)
if created:
    deleted_user.set_password('Deleted123!')
    deleted_user.save()
    deleted_user.soft_delete(performed_by=admin)
    print(f"   ✅ Создан и удалён: {deleted_user.email} (пароль: Deleted123!)")
else:
    print(f"   📌 Существует (возможно удалён): {deleted_user.email}")


# ============================================================================
# 3. ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ТЕСТОВЫХ ФАЙЛОВ
# ============================================================================

def create_test_pdf(filename):
    """Создаёт тестовый PDF файл в памяти"""
    content = f'%PDF-1.4\n%\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test document) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000215 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n298\n%%EOF'.encode()
    return ContentFile(content, name=filename)


def create_test_image(filename):
    """Создаёт тестовое изображение в памяти"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    return ContentFile(img_io.getvalue(), name=filename)


# ============================================================================
# 4. СОЗДАНИЕ ТЕСТОВЫХ ДОКУМЕНТОВ
# ============================================================================

print("\n3. Создание тестовых документов...")

# Создаём тестовые файлы
test_pdf = create_test_pdf('document.pdf')
test_image = create_test_image('document.png')

# Документ в статусе DRAFT (черновик)
doc_draft = Document.objects.create(
    user=users[0],
    file=test_pdf,
    user_note='Черновик заявления на отпуск',
    status='draft'
)
doc_draft.log_action(user=users[0], action='created', new_status='draft')
print(f"   ✅ Документ DRAFT: ID={doc_draft.id} (пользователь: {users[0].email})")

# Документ в статусе PENDING (на проверке)
doc_pending = Document.objects.create(
    user=users[1],
    file=test_pdf,
    user_note='Заявление на отпуск с 1 июня',
    status='pending'
)
doc_pending.log_action(user=users[1], action='created', new_status='draft')
doc_pending.log_action(user=users[1], action='submitted', old_status='draft', new_status='pending')
print(f"   ✅ Документ PENDING: ID={doc_pending.id} (пользователь: {users[1].email})")

# Документ в статусе APPROVED (подтверждён)
doc_approved = Document.objects.create(
    user=users[0],
    file=test_pdf,
    user_note='Заявление на премию',
    status='approved'
)
doc_approved.log_action(user=users[0], action='created', new_status='draft')
doc_approved.log_action(user=users[0], action='submitted', old_status='draft', new_status='pending')
doc_approved.approve(moderator=moderator)
print(f"   ✅ Документ APPROVED: ID={doc_approved.id} (проверил: {moderator.email})")

# Документ в статусе REJECTED (отклонён с комментарием)
doc_rejected = Document.objects.create(
    user=users[1],
    file=test_image,
    user_note='Скан паспорта',
    status='rejected'
)
doc_rejected.log_action(user=users[1], action='created', new_status='draft')
doc_rejected.log_action(user=users[1], action='submitted', old_status='draft', new_status='pending')
doc_rejected.reject(moderator=moderator, comment='Нечитаемый скан, загрузите чёткую копию')
print(f"   ✅ Документ REJECTED: ID={doc_rejected.id} (причина: Нечитаемый скан)")

# Ещё один документ в статусе PENDING для демонстрации
doc_pending2 = Document.objects.create(
    user=users[2],
    file=test_pdf,
    user_note='Отчёт о работе за май',
    status='pending'
)
doc_pending2.log_action(user=users[2], action='created', new_status='draft')
doc_pending2.log_action(user=users[2], action='submitted', old_status='draft', new_status='pending')
print(f"   ✅ Документ PENDING: ID={doc_pending2.id} (пользователь: {users[2].email})")


# ============================================================================
# 5. ВЫВОД ИТОГОВ
# ============================================================================

print("\n" + "=" * 60)
print("ИТОГИ СОЗДАНИЯ ТЕСТОВЫХ ДАННЫХ")
print("=" * 60)

print(f"\n👥 ПОЛЬЗОВАТЕЛИ:")
print(f"   - Администратор: admin@docflow.com / Admin123!")
print(f"   - Модератор документов: moderator@docflow.com / Moderator123!")
print(f"   - Менеджер пользователей: usermanager@docflow.com / UserMan123!")
for i, user in enumerate(users, 1):
    print(f"   - Пользователь{i}: user{i}@docflow.com / User{i}123!")
print(f"   - Удалённый пользователь: deleted@docflow.com / Deleted123!")

print(f"\n📄 ДОКУМЕНТЫ:")
print(f"   - Черновик (draft): ID={doc_draft.id}")
print(f"   - На проверке (pending): ID={doc_pending.id}, ID={doc_pending2.id}")
print(f"   - Подтверждён (approved): ID={doc_approved.id}")
print(f"   - Отклонён (rejected): ID={doc_rejected.id}")

print(f"\n📊 СТАТИСТИКА:")
print(f"   - Всего пользователей: {User.objects.count()}")
print(f"   - Активных пользователей: {User.objects.active().count()}")
print(f"   - Мягко удалённых: {User.objects.filter(deleted_at__isnull=False).count()}")
print(f"   - Всего документов: {Document.objects.count()}")
print(f"   - Черновиков: {Document.objects.filter(status='draft').count()}")
print(f"   - На проверке: {Document.objects.filter(status='pending').count()}")
print(f"   - Подтверждённых: {Document.objects.filter(status='approved').count()}")
print(f"   - Отклонённых: {Document.objects.filter(status='rejected').count()}")

print("\n" + "=" * 60)
print("ТЕСТОВЫЕ ДАННЫЕ УСПЕШНО СОЗДАНЫ")
print("=" * 60)