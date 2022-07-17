import os
import django
from django.conf import settings
from celery import Celery


# Создание и настройка очереди задач.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelservice.settings')
django.setup()
app = Celery('channelservice')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
