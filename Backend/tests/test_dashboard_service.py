from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.quotation import Quotation, QuotationStatus
from app.services.dashboard_service import get_summary


def test_dashboard_conversion_uses_all_issued_quotations_and_excludes_drafts():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine)
    db = test_session()
    statuses = [
        QuotationStatus.BROUILLON,
        QuotationStatus.ENVOYEE,
        QuotationStatus.ACCEPTEE,
        QuotationStatus.REFUSEE,
        QuotationStatus.EXPIREE,
    ]
    db.add_all(
        Quotation(
            reference=f"DASH-{index}",
            client_name="Dashboard test",
            client_email="dashboard@example.test",
            creation_date=date.today(),
            status=status,
            total_amount=Decimal("10.00"),
        )
        for index, status in enumerate(statuses)
    )
    db.commit()

    try:
        summary = get_summary(db)
        assert summary.total_quotations == 5
        assert summary.draft_count == 1
        assert summary.conversion_rate == 0.25
        assert summary.total_amount == 50
    finally:
        db.close()
        test_engine.dispose()


def test_dashboard_summary_is_scoped_to_collaborator_quotations():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine)
    db = test_session()
    db.add_all(
        [
            Quotation(
                reference="DASH-MINE",
                client_name="My quotation",
                client_email="mine@example.test",
                creation_date=date.today(),
                status=QuotationStatus.ACCEPTEE,
                total_amount=Decimal("10.00"),
                created_by="collaborator-1",
            ),
            Quotation(
                reference="DASH-OTHER",
                client_name="Other quotation",
                client_email="other@example.test",
                creation_date=date.today(),
                status=QuotationStatus.ENVOYEE,
                total_amount=Decimal("100.00"),
                created_by="collaborator-2",
            ),
        ]
    )
    db.commit()

    try:
        summary = get_summary(db, user_id="collaborator-1", role="COLLABORATEUR")
        assert summary.total_quotations == 1
        assert summary.accepted_count == 1
        assert summary.sent_count == 0
        assert summary.conversion_rate == 1.0
        assert summary.total_amount == 10
    finally:
        db.close()
        test_engine.dispose()
