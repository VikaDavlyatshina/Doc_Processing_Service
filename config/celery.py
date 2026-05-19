import os

from celery import Celery

# Устанавливаем настройки Django по умолчанию
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Создаём экземпляр Celery
app = Celery("config")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.

# Загружаем настройки из settings.py с префиксом CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
# Автоматически находим задачи в приложениях
app.autodiscover_tasks()
