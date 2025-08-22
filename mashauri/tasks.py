from celery import shared_task
from .utils import schedule_six_pm_emails_mashauri_fixed
from .models import Dispatch
from django.utils.timezone import now


@shared_task
def six_pm_mashauri_fixed():
    schedule_six_pm_emails_mashauri_fixed()
    print("Running my scheduled function!")


@shared_task
def update_expired_dispatches_mashauri_fixed():
    expired_dispatches = Dispatch.objects.filter(
        is_expired=False,
        sla_timer__lte=now())
    count = expired_dispatches.update(
        is_expired=True,
        expired_at=now())
    return f'{count} dispatches marked as expired.'
