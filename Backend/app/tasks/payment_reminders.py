from datetime import date

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.services.payment_reminder_service import get_due_quotations, send_reminder_for_quotation


def _log_task_execution(db, task_name: str, processed: int, status: str = "success", details: dict | None = None):
    audit = AuditLog(
        user_id=None,
        action="task.executed",
        entity_type="system_task",
        entity_id=task_name,
        details={
            "processed": processed,
            "status": status,
            **(details or {}),
        },
    )
    db.add(audit)
    db.commit()


@celery_app.task
def send_payment_reminders():
    db = SessionLocal()
    task_name = "send_payment_reminders"
    try:
        today = date.today()
        quotas = get_due_quotations(db, today)
        reminders_sent = 0
        for quotation in quotas:
            try:
                reminder = send_reminder_for_quotation(db, quotation, today)
                if reminder is not None:
                    reminders_sent += 1
            except Exception:
                db.rollback()
        _log_task_execution(db, task_name, reminders_sent)
        return reminders_sent
    except Exception as exc:
        db.rollback()
        _log_task_execution(db, task_name, 0, status="failed", details={"error_type": type(exc).__name__})
        raise
    finally:
        db.close()
