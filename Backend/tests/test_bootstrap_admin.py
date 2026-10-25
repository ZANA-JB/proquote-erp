from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import bootstrap_admin as bootstrap
from app.core.database import Base
from app.core.security import verify_password
from app.models import Quotation
from app.models.audit_log import AuditLog
from app.models.quotation import QuotationStatus
from app.models.user import User, UserRole


def make_test_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)


def test_rerunning_bootstrap_resets_only_target_admin_and_keeps_linked_data(monkeypatch):
    engine, test_session = make_test_session()
    monkeypatch.setattr(bootstrap, "SessionLocal", test_session)
    old_password = "old-administrator-password"
    new_password = "new-administrator-password"

    try:
        with test_session() as db:
            admin = User(
                email="admin@example.com",
                hashed_password=bootstrap.get_password_hash(old_password),
                full_name="Original Administrator",
                role=UserRole.ADMIN,
                is_active=True,
                token_version=4,
            )
            db.add(admin)
            db.flush()
            admin_id = admin.id
            quotation = Quotation(
                reference="ADMIN-QUOTATION",
                client_name="Existing client",
                client_email="client@example.com",
                creation_date=date(2026, 10, 25),
                status=QuotationStatus.ENVOYEE,
                total_amount=100,
                created_by=admin_id,
            )
            db.add(quotation)
            db.add(
                AuditLog(
                    user_id=admin_id,
                    action="auth.login",
                    entity_type="User",
                    entity_id=admin_id,
                )
            )
            db.commit()

        result = bootstrap.configure_admin_account(
            "ADMIN@example.com",
            "Name should not replace the existing one",
            new_password,
        )

        with test_session() as db:
            admin = db.query(User).filter(User.id == admin_id).one()
            quotation = db.query(Quotation).filter(Quotation.reference == "ADMIN-QUOTATION").one()
            audit_log = db.query(AuditLog).one()

            assert result == "reset"
            assert admin.email == "admin@example.com"
            assert admin.full_name == "Original Administrator"
            assert admin.role == UserRole.ADMIN
            assert admin.is_active is True
            assert admin.token_version == 5
            assert verify_password(new_password, admin.hashed_password)
            assert not verify_password(old_password, admin.hashed_password)
            assert quotation.created_by == admin_id
            assert audit_log.user_id == admin_id
    finally:
        engine.dispose()


def test_bootstrap_creates_first_admin(monkeypatch):
    engine, test_session = make_test_session()
    monkeypatch.setattr(bootstrap, "SessionLocal", test_session)

    try:
        result = bootstrap.configure_admin_account(
            "new.admin@example.com",
            "New Administrator",
            "new-administrator-password",
        )
        with test_session() as db:
            admin = db.query(User).filter(User.email == "new.admin@example.com").one()
            assert result == "created"
            assert admin.role == UserRole.ADMIN
            assert admin.full_name == "New Administrator"
            assert admin.token_version == 1
            assert verify_password("new-administrator-password", admin.hashed_password)
    finally:
        engine.dispose()


def test_bootstrap_refuses_to_create_a_different_admin_if_one_exists(monkeypatch):
    engine, test_session = make_test_session()
    monkeypatch.setattr(bootstrap, "SessionLocal", test_session)

    try:
        with test_session() as db:
            db.add(
                User(
                    email="existing.admin@example.com",
                    hashed_password=bootstrap.get_password_hash("existing-administrator-password"),
                    full_name="Existing Administrator",
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            db.commit()

        with pytest.raises(SystemExit, match="exact email"):
            bootstrap.configure_admin_account(
                "another.admin@example.com",
                "Another Administrator",
                "another-administrator-password",
            )

        with test_session() as db:
            assert db.query(User).count() == 1
    finally:
        engine.dispose()


def test_bootstrap_refuses_to_reset_a_non_admin_account(monkeypatch):
    engine, test_session = make_test_session()
    monkeypatch.setattr(bootstrap, "SessionLocal", test_session)

    try:
        with test_session() as db:
            db.add(
                User(
                    email="collaborator@example.com",
                    hashed_password=bootstrap.get_password_hash("collaborator-password"),
                    full_name="Collaborator",
                    role=UserRole.COLLABORATEUR,
                    is_active=True,
                )
            )
            db.commit()

        with pytest.raises(SystemExit, match="non-administrator"):
            bootstrap.configure_admin_account(
                "collaborator@example.com",
                "Collaborator",
                "new-administrator-password",
            )

        with test_session() as db:
            user = db.query(User).filter(User.email == "collaborator@example.com").one()
            assert user.role == UserRole.COLLABORATEUR
            assert verify_password("collaborator-password", user.hashed_password)
    finally:
        engine.dispose()
