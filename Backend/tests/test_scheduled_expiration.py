from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import yaml

from app.core.database import Base
from app.models.quotation import Quotation, QuotationStatus
from app.tasks.celery_app import celery_app
import app.tasks.expire_quotations as expiration_task


def test_expiration_task_marks_expired_quotation(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(expiration_task, "SessionLocal", test_session)

    quotation_id = str(uuid.uuid4())
    db = test_session()
    try:
        db.add(
            Quotation(
                id=quotation_id,
                reference=f"EXP-{quotation_id}",
                client_name="Expiration test",
                client_email="expiration@example.com",
                creation_date=date.today() - timedelta(days=10),
                validity_date=date.today() - timedelta(days=1),
                status=QuotationStatus.ENVOYEE,
                total_amount=Decimal("10.00"),
            )
        )
        db.commit()
    finally:
        db.close()

    assert expiration_task.expire_quotations.run() == 1

    db = test_session()
    try:
        quotation = db.get(Quotation, quotation_id)
        assert quotation.status == QuotationStatus.EXPIREE
    finally:
        db.close()
        test_engine.dispose()


def test_render_schedules_crons_without_celery_or_redis():
    root = Path(__file__).resolve().parents[2]
    render_config = yaml.safe_load((root / "render.yaml").read_text(encoding="utf-8"))
    api = next(
        service for service in render_config["services"]
        if service["name"] == "proquote-erp-api"
    )
    cron = next(
        service for service in render_config["services"]
        if service["name"] == "proquote-erp-expire-quotations"
    )
    reminder_cron = next(
        service for service in render_config["services"]
        if service["name"] == "proquote-erp-payment-reminders"
    )

    assert api["preDeployCommand"] == "alembic upgrade head"
    assert any(
        variable.get("key") == "DATABASE_URL"
        and variable.get("fromDatabase", {}).get("name") == "proquote-erp-db"
        for variable in cron["envVars"]
    )
    assert cron["schedule"] == "0 * * * *"
    assert cron["dockerCommand"] == "python -m app.tasks.run_expiration_job"
    assert reminder_cron["schedule"] == "0 8 * * *"
    assert reminder_cron["dockerCommand"] == "python -m app.tasks.run_payment_reminders_job"
    assert any(
        variable.get("key") == "DATABASE_URL"
        and variable.get("fromDatabase", {}).get("name") == "proquote-erp-db"
        and variable.get("fromDatabase", {}).get("property") == "connectionString"
        for variable in reminder_cron["envVars"]
    )
    assert all(
        variable.get("sync") is False
        for variable in reminder_cron["envVars"]
        if variable.get("key") in {"SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"}
    )
    assert next(
        database for database in render_config["databases"]
        if database["name"] == "proquote-erp-db"
    )["plan"] == "basic-1gb"
    assert celery_app.conf.beat_schedule == {}
    assert all(
        service["type"] not in {"worker", "keyvalue"}
        for service in render_config["services"]
    )


def test_payment_reminder_job_requires_smtp_settings(monkeypatch):
    from app.tasks import run_payment_reminders_job

    monkeypatch.setattr(run_payment_reminders_job, "ensure_database_migrations_are_current", lambda: None)
    monkeypatch.setattr(run_payment_reminders_job.settings, "SMTP_HOST", "")
    monkeypatch.setattr(run_payment_reminders_job.settings, "MAIL_FROM", "")

    try:
        run_payment_reminders_job.main()
    except RuntimeError as exc:
        assert "SMTP_HOST" in str(exc)
        assert "MAIL_FROM" in str(exc)
    else:
        raise AssertionError("The scheduled job must reject missing mail settings.")


def test_payment_reminder_job_runs_when_mail_settings_are_configured(monkeypatch, capsys):
    from app.tasks import run_payment_reminders_job

    monkeypatch.setattr(run_payment_reminders_job, "ensure_database_migrations_are_current", lambda: None)
    monkeypatch.setattr(run_payment_reminders_job.settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(run_payment_reminders_job.settings, "MAIL_FROM", "test@example.test")
    monkeypatch.setattr(run_payment_reminders_job.send_payment_reminders, "run", lambda: 3)

    run_payment_reminders_job.main()

    assert "reminders sent: 3" in capsys.readouterr().out
