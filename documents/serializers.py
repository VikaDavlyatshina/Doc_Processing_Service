from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Document.
    Превращает объект в JSON и обратно.
    """

    # Человекочитаемый статус (поле только для чтения)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # Email владельца (вместо ID)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    # Email модератора (вместо ID)
    reviewed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",              # ID документа
            "user",            # Кто загрузил (только чтение)
            "user_email",
            "file",            # Сам файл
            "status",          # Статус (только чтение)
            "status_display",  # Человекочитаемый статус
            "comment",         # Комментарий
            "uploaded_at",     # Дата загрузки (только чтение)
            "reviewed_by",     # Кто проверил (только чтение)
            "reviewed_by_email",
            "reviewed_at",     # Дата проверки (только чтение)
        ]
        read_only_fields = [
            "user",           # user нельзя редактировать через API
            "status",         # статус меняется только через approve/reject
            "uploaded_at",    # дата загрузки устанавливается автоматически
            "reviewed_by",    # заполняется при approve/reject
            "reviewed_at",    # заполняется при approve/reject
        ]
        extra_kwargs = {
            "user_note": {
                "required": True,
                "allow_blank": False,
                "help_text": "Короткий комментарий к документу (обязательно)",
            }
        }

    def get_reviewed_by_email(self, obj):
        """Возвращает email модератора или None, если документ не проверен."""
        return obj.reviewed_by.email if obj.reviewed_by else None

    def validate_user_note(self, value):
        """Проверяет, что комментарий владельца не пустой."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Укажите короткий комментарий к документу"
            )
        return value.strip()

    def validate_comment(self, value):
        """Проверяет длину комментария (если он есть)."""
        if value and len(value) > 500:
            raise serializers.ValidationError(
                "Комментарий не может быть длиннее 500 символов"
            )
        return value
