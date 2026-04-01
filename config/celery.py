import os
from celery import Celery

# устанавливаем переменную окружения для Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# создаем приложение Celery
app = Celery('config')

# загружаем настройки из Django settings с префиксом 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим задачи в установленных приложениях
app.autodiscover_tasks()

# == Для отладки: выводим, что задача запущена ==
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

