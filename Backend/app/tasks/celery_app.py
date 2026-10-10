"""Configure les tâches périodiques exécutées par Celery."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "backend",
    broker=settings.REDIS_URL,
    include=[
        "app.tasks.payment_reminders",
        "app.tasks.expire_quotations",
    ],
)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "send-payment-reminders-daily": {
        "task": "app.tasks.payment_reminders.send_payment_reminders",
        "schedule": 86400.0,
    },
    "expire-quotations-hourly": {
        "task": "app.tasks.expire_quotations.expire_quotations",
        "schedule": 3600.0,
    },
}
