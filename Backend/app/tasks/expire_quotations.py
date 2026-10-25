from datetime import date

from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.quotation import Quotation, QuotationStatus
from app.models.user import User  # noqa: F401  # Registers AuditLog's foreign-key target.
from app.services.status_service import change_status, StatusTransitionError
from app.tasks.celery_app import celery_app


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
def expire_quotations():
    db = SessionLocal()
    task_name = "expire_quotations"
    try:
        today = date.today()
        expired_quotations = (
            db.query(Quotation)
            .filter(Quotation.status == QuotationStatus.ENVOYEE)
            .filter(Quotation.validity_date < today)
            .all()
        )

        processed = 0
        for quotation in expired_quotations:
            try:
                change_status(quotation, QuotationStatus.EXPIREE, db)
                audit = AuditLog(
                    user_id=None,
                    action="quotation.auto_expired",
                    entity_type="Quotation",
                    entity_id=quotation.id,
                    details={
                        "validity_date": quotation.validity_date.isoformat() if quotation.validity_date else None,
                        "previous_status": QuotationStatus.ENVOYEE.value,
                    },
                )
                db.add(audit)
                db.commit()
                processed += 1
            except StatusTransitionError:
                db.rollback()
            except Exception:
                db.rollback()

        _log_task_execution(db, task_name, processed)
        return processed
    except Exception as exc:
        db.rollback()
        _log_task_execution(db, task_name, 0, status="failed", details={"error_type": type(exc).__name__})
        raise
    finally:
        db.close()
