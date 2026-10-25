"""Configure les tâches périodiques exécutées par Celery."""

from celery import Celery

celery_app = Celery(
    "backend",
    broker="memory://",
    include=[
        "app.tasks.payment_reminders",
        "app.tasks.expire_quotations",
    ],
)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {}
