import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UAMSAPI.settings')

app = Celery('UAMSAPI')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks()
