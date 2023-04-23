import os
from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_management.settings")

app = Celery("task_management")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
