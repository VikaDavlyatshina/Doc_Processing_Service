# Этот файл выполняется при запуске Django.
# "Когда Django стартует, сразу загрузи Celery".


from .celery import app as celery_app

__all__ = ("celery_app",)
