# импортируем celery , чтобы оно запускалось при старте Django
from .celery import app as celery_app

__all__ = ('celery_app')
