from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Document.
    Превращает объект в JSON и обратно.
    """

    # Человекочитаемый статус (поле только для чтения)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',  # ID документа
            'user',  # Кто загрузил (только чтение)
            'file',  # Сам файл
            'status',  # Статус (только чтение)
            'status_display',  # Человекочитаемый статус
            'comment',  # Комментарий
            'uploaded_at',  # Дата загрузки (только чтение)
            'reviewed_by',  # Кто проверил (только чтение)
            'reviewed_at',  # Дата проверки (только чтение)
        ]
        read_only_fields = [
            'user',  # user нельзя редактировать через API
            'status',  # статус меняется только через approve/reject
            'uploaded_at',  # дата загрузки устанавливается автоматически
            'reviewed_by',  # заполняется при approve/reject
            'reviewed_at',  # заполняется при approve/reject
        ]

    def validate_comment(self, value):
        """Проверяет длину комментария"""
        if len(value) > 500:
            raise serializers.ValidationError('Комментарий не может быть длиннее 500 символов')
        return value