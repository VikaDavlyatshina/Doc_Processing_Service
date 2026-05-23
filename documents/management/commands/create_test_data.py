from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from documents.models import Document

User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт тестовые данные для DocFlow"

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ ДЛЯ DOCFLOW")
        self.stdout.write("=" * 60)

        # Проверяем, есть ли уже данные
        if User.objects.filter(email="admin@docflow.com").exists():
            self.stdout.write(
                self.style.WARNING("Данные уже существуют, пропускаем...")
            )
            self.stdout.write("   - Админ: admin@docflow.com / Admin123!")
            self.stdout.write("   - Модератор: moderator@docflow.com / Moderator123!")
            self.stdout.write(f"   - Документов: {Document.objects.count()}")
            return

        # ====================================================================
        # 1. СОЗДАНИЕ ГРУПП
        # ====================================================================
        self.stdout.write("\n1. Проверка и создание групп...")

        moderator_group, created = Group.objects.get_or_create(
            name="Document Moderator"
        )
        self.stdout.write(
            f"   - Группа 'Document Moderator': {'создана' if created else 'существует'}"
        )

        user_manager_group, created = Group.objects.get_or_create(name="User Manager")
        self.stdout.write(
            f"   - Группа 'User Manager': {'создана' if created else 'существует'}"
        )

        # ====================================================================
        # 2. СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ
        # ====================================================================
        self.stdout.write("\n2. Создание тестовых пользователей...")

        # Администратор
        admin = User.objects.create_superuser(
            email="admin@docflow.com",
            password="Admin123!",
            first_name="Администратор",
            last_name="Системы",
            phone="+79990000001",
        )
        self.stdout.write(
            self.style.SUCCESS("   ✅ Создан: admin@docflow.com (пароль: Admin123!)")
        )

        # Модератор документов
        moderator = User.objects.create_user(
            email="moderator@docflow.com",
            password="Moderator123!",
            first_name="Модератор",
            last_name="Документов",
            phone="+79990000002",
            is_staff=True,
        )
        moderator.groups.add(moderator_group)
        self.stdout.write(
            self.style.SUCCESS(
                "   ✅ Создан: moderator@docflow.com (пароль: Moderator123!)"
            )
        )

        # Менеджер пользователей
        user_manager = User.objects.create_user(
            email="usermanager@docflow.com",
            password="UserMan123!",
            first_name="Менеджер",
            last_name="Пользователей",
            phone="+79990000003",
            is_staff=True,
        )
        user_manager.groups.add(user_manager_group)
        self.stdout.write(
            self.style.SUCCESS(
                "   ✅ Создан: usermanager@docflow.com (пароль: UserMan123!)"
            )
        )

        # Обычные пользователи
        users = []
        for i in range(1, 4):
            user = User.objects.create_user(
                email=f"user{i}@docflow.com",
                password=f"User{i}123!",
                first_name=f"Пользователь{i}",
                last_name=f"Фамилия{i}",
                phone=f"+7999000000{i}",
            )
            users.append(user)
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✅ Создан: user{i}@docflow.com (пароль: User{i}123!)"
                )
            )

        # Удалённый пользователь
        deleted_user = User.objects.create_user(
            email="deleted@docflow.com",
            password="Deleted123!",
            first_name="Удалённый",
            last_name="Пользователь",
            phone="+79990000099",
            is_active=False,
        )
        if hasattr(deleted_user, "soft_delete"):
            deleted_user.soft_delete(performed_by=admin)
        self.stdout.write(
            self.style.SUCCESS(
                "   ✅ Создан и удалён: deleted@docflow.com (пароль: Deleted123!)"
            )
        )

        # ====================================================================
        # 3. ФУНКЦИИ ДЛЯ СОЗДАНИЯ ФАЙЛОВ
        # ====================================================================
        def create_test_pdf(filename):
            content = b"%PDF-1.4\n%\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test document) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000215 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n298\n%%EOF"
            return ContentFile(content, name=filename)

        def create_test_image(filename):
            img = Image.new("RGB", (100, 100), color="red")
            img_io = BytesIO()
            img.save(img_io, format="PNG")
            return ContentFile(img_io.getvalue(), name=filename)

        # ====================================================================
        # 4. СОЗДАНИЕ ДОКУМЕНТОВ
        # ====================================================================
        self.stdout.write("\n3. Создание тестовых документов...")

        test_pdf = create_test_pdf("document.pdf")
        test_image = create_test_image("document.png")

        # Черновик
        doc_draft = Document.objects.create(
            user=users[0],
            file=test_pdf,
            user_note="Черновик заявления на отпуск",
            status="draft",
        )
        self.stdout.write(f"   ✅ Документ DRAFT: ID={doc_draft.id}")

        # На проверке 1
        doc_pending = Document.objects.create(
            user=users[1],
            file=test_pdf,
            user_note="Заявление на отпуск с 1 июня",
            status="pending",
        )
        self.stdout.write(f"   ✅ Документ PENDING: ID={doc_pending.id}")

        # Подтверждён
        doc_approved = Document.objects.create(
            user=users[0],
            file=test_pdf,
            user_note="Заявление на премию",
            status="approved",
        )
        self.stdout.write(f"   ✅ Документ APPROVED: ID={doc_approved.id}")

        # Отклонён
        doc_rejected = Document.objects.create(
            user=users[1],
            file=test_image,
            user_note="Скан паспорта",
            status="rejected",
        )
        self.stdout.write(f"   ✅ Документ REJECTED: ID={doc_rejected.id}")

        # На проверке 2
        doc_pending2 = Document.objects.create(
            user=users[2],
            file=test_pdf,
            user_note="Отчёт о работе за май",
            status="pending",
        )
        self.stdout.write(f"   ✅ Документ PENDING: ID={doc_pending2.id}")

        # ====================================================================
        # 5. ВЫВОД ИТОГОВ
        # ====================================================================
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("ИТОГИ СОЗДАНИЯ ТЕСТОВЫХ ДАННЫХ")
        self.stdout.write("=" * 60)

        self.stdout.write("\n👥 ПОЛЬЗОВАТЕЛИ:")
        self.stdout.write("   - Администратор: admin@docflow.com / Admin123!")
        self.stdout.write(
            "   - Модератор документов: moderator@docflow.com / Moderator123!"
        )
        self.stdout.write(
            "   - Менеджер пользователей: usermanager@docflow.com / UserMan123!"
        )
        for i in range(1, 4):
            self.stdout.write(
                f"   - Пользователь{i}: user{i}@docflow.com / User{i}123!"
            )
        self.stdout.write(
            "  - Удалённый пользователь: deleted@docflow.com / Deleted123!"
        )

        self.stdout.write("\n📊 СТАТИСТИКА:")
        self.stdout.write(f"   - Всего пользователей: {User.objects.count()}")
        self.stdout.write(f"   - Всего документов: {Document.objects.count()}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ ТЕСТОВЫЕ ДАННЫЕ УСПЕШНО СОЗДАНЫ"))
        self.stdout.write("=" * 60)
