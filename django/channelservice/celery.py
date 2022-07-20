import os
from celery import Celery


# Создание и настройка очереди задач.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelservice.settings')
app = Celery('channelservice')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
