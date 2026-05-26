from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from .models import User
from .validators import (validate_avatar, validate_first_name,
                         validate_last_name, validate_password)


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания пользователя.
    Используется при регистрации нового пользователя.
    """

    # Поле пароля с валидацией: принимается при регистрации, но  не возвращается в ответе
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    # Поле телефона: необязательное при регистрации
    phone = PhoneNumberField(required=False)

    class Meta:
        model = User
        # Поля, которые указываются при регистрации нового пользователя
        fields = ["id", "email", "phone", "password", "first_name", "last_name"]
        # ID генерируется автоматически, пользователь не может его указать
        read_only_fields = ["id"]
        extra_kwargs = {
            "email": {
                "validators": [],  # Убираем стандартнуб проверку Джанго
            }
        }

    # ========================================================================
    # ВАЛИДАЦИЯ ПОЛЕЙ
    # ========================================================================

    def validate_email(self, value):
        """
        Проверка email на уникальность и статус пользователя.

        Возможные сценарии:
        1. Email свободен → можно регистрироваться
        2. Активный пользователь с таким email уже есть → ошибка
        3. Удалённый пользователь с таким email есть → ошибка с предложением обратиться к администратору
        """
        # Используем _base_manager, чтобы найти пользователя даже если он удалён
        user = User._base_manager.filter(email=value).first()

        if user:
            if user.is_deleted:
                # Пользователь мягко удалён, но данные сохранены
                raise serializers.ValidationError(
                    "Этот аккаунт был удалён. Для восстановления обратитесь к администратору."
                )
            else:
                # Активный пользователь
                raise serializers.ValidationError(
                    "Пользователь с таким email уже существует"
                )
        return value

    def validate_first_name(self, value):
        """Валидация имени"""
        return validate_first_name(value)

    def validate_last_name(self, value):
        """Валидация фамилии"""
        return validate_last_name(value)

    # ========================================================================
    # СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
    # ========================================================================

    def create(self, validated_data):
        """
        Создаёт нового пользователя в базе данных.

        Если пользователь удалил аккаунт, он не может зарегистрироваться снова
        без помощи администратора. Это сделано для сохранения целостности данных
        (документы удалённого пользователя остаются в системе).
        """
        password = validated_data.pop("password")
        email = validated_data.pop("email")

        return User.objects.create_user(
            email=email,
            password=password,
            **validated_data,
        )


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для просмотра и редактирования профиля пользователя.
    Используется в эндпоинтах:
    - GET    /api/users/profile/   (просмотр)
    - PATCH  /api/users/profile/   (частичное обновление)
    """

    class Meta:
        model = User
        # Поля для отображения
        fields = ["id", "email", "phone", "first_name", "last_name", "avatar"]
        # ID и email нельзя изменять после создания
        read_only_fields = ["id", "email"]

    def validate_avatar(self, value):
        """Проверка аватара"""
        return validate_avatar(value)
