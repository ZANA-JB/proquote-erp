from datetime import date, timedelta
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.article import Article
from app.models.audit_log import AuditLog
from app.models.payment_reminder import ReminderStatus
from app.models.quotation import Quotation, QuotationStatus
from app.models.user import User
from app.services import email_service, payment_reminder_service


def test_quotation_email_contains_pdf_attachment_without_opening_smtp(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "quotation.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    captured: list[EmailMessage] = []
    monkeypatch.setattr(email_service.settings, "MAIL_FROM", "test@example.com")
    monkeypatch.setattr(email_service.settings, "COMPANY_NAME", "ProQuote Test")
    monkeypatch.setattr(email_service, "_send_email", lambda message: captured.append(message) or True)
    quotation = SimpleNamespace(
        reference="Q-TEST-001",
        client_name="Client Test",
        client_email="client@example.com",
    )

    assert email_service.send_quotation_email(quotation, str(pdf_path)) is True

    assert len(captured) == 1
    assert captured[0]["To"] == "client@example.com"
    assert captured[0]["Subject"] == "Quotation Q-TEST-001"
    attachment = list(captured[0].iter_attachments())[0]
    assert attachment.get_content() == b"%PDF-test"


def test_email_send_reports_smtp_failure_without_real_connection(monkeypatch):
    message = EmailMessage()

    def fail_connection():
        raise OSError("mock SMTP failure")

    monkeypatch.setattr(email_service, "_open_smtp_connection", fail_connection)

    assert email_service._send_email(message) is False


def test_quotation_email_without_sender_is_not_sent(monkeypatch):
    monkeypatch.setattr(email_service.settings, "MAIL_FROM", "")

    def fail_if_sent(_message):
        raise AssertionError("SMTP must not be called")

    monkeypatch.setattr(email_service, "_send_email", fail_if_sent)

    assert email_service.send_quotation_email(
        SimpleNamespace(reference="Q-TEST-002", client_name="Client", client_email="client@example.com"),
        "unused.pdf",
    ) is False


def test_due_quotations_are_accepted_unpaid_and_past_threshold():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    db = test_session()
    today = date(2026, 3, 20)
    eligible = Quotation(
        reference="REM-ELIGIBLE",
        client_name="Eligible",
        client_email="eligible@example.com",
        validity_date=today - timedelta(days=8),
        status=QuotationStatus.ACCEPTEE,
        total_amount=Decimal("10.00"),
        is_paid=False,
    )
    db.add_all(
        [
            eligible,
            Quotation(
                reference="REM-PAID",
                client_name="Paid",
                client_email="paid@example.com",
                validity_date=today - timedelta(days=10),
                status=QuotationStatus.ACCEPTEE,
                total_amount=Decimal("10.00"),
                is_paid=True,
            ),
            Quotation(
                reference="REM-SENT",
                client_name="Sent",
                client_email="sent@example.com",
                validity_date=today - timedelta(days=10),
                status=QuotationStatus.ENVOYEE,
                total_amount=Decimal("10.00"),
                is_paid=False,
            ),
            Quotation(
                reference="REM-RECENT",
                client_name="Recent",
                client_email="recent@example.com",
                validity_date=today - timedelta(days=6),
                status=QuotationStatus.ACCEPTEE,
                total_amount=Decimal("10.00"),
                is_paid=False,
            ),
        ]
    )
    db.commit()
    try:
        assert payment_reminder_service.get_due_quotations(db, today) == [eligible]
    finally:
        db.close()
        test_engine.dispose()


def test_failed_payment_reminder_is_recorded_as_failure(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    db = test_session()
    today = date(2026, 3, 20)
    quotation = Quotation(
        reference="REM-FAIL",
        client_name="Failure",
        client_email="failure@example.com",
        validity_date=today - timedelta(days=8),
        status=QuotationStatus.ACCEPTEE,
        total_amount=Decimal("10.00"),
        is_paid=False,
    )
    db.add(quotation)
    db.commit()
    monkeypatch.setattr(payment_reminder_service, "send_payment_reminder_email", lambda *_args: False)

    try:
        reminder = payment_reminder_service.send_reminder_for_quotation(db, quotation, today)
        assert reminder is not None
        assert reminder.reminder_status == ReminderStatus.ECHEC
        audit = db.query(AuditLog).filter(AuditLog.entity_id == reminder.id).one()
        assert audit.action == "payment_reminder.failed"
        assert audit.details["status"] == ReminderStatus.ECHEC.value
    finally:
        db.close()
        test_engine.dispose()
