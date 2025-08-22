from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mashauri_core.settings')

app = Celery('mashauri_core')
app.conf.enable_utc = False

app.config_from_object(settings, namespace='CELERY')

app.conf.beat_schedule = {
    'send-mail-every-4pm': {
        'task': 'mashauri.tasks.six_pm_mashauri_fixed',
        'schedule': crontab(hour=18, minute=0),
    },

    'update-expired-dispatches': {
        'task': 'mashauri.tasks.update_expired_dispatches_mashauri_fixed',
        'schedule': crontab(minute='*/5'),
    },
}

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
