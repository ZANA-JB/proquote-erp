import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import verify_password
from app.models.user import User, UserRole
from app import bootstrap_test_user as bootstrap


def test_test_user_creation_uses_collaborator_role_and_hashed_password(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine)
    monkeypatch.setattr(bootstrap, "SessionLocal", test_session)
    monkeypatch.setattr(bootstrap, "ensure_database_migrations_are_current", lambda: None)
    password = "temporary-test-password"

    try:
        bootstrap.create_test_user(" Test.User@example.com ", "Test User", password)
        with test_session() as db:
            user = db.query(User).filter(User.email == "test.user@example.com").one()
            assert user.role == UserRole.COLLABORATEUR
            assert user.is_active is True
            assert user.hashed_password != password
            assert verify_password(password, user.hashed_password)

        with pytest.raises(SystemExit, match="already exists"):
            bootstrap.create_test_user("test.user@example.com", "Another Name", "another-test-password")

        with test_session() as db:
            user = db.query(User).filter(User.email == "test.user@example.com").one()
            assert user.full_name == "Test User"
            assert verify_password(password, user.hashed_password)
    finally:
        test_engine.dispose()


def test_demo_seeding_refuses_production_before_database_access(monkeypatch):
    from app.core import seed

    monkeypatch.setattr(seed.settings, "ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="disabled in production"):
        seed.seed_admin("non-production-test-password")

    with pytest.raises(RuntimeError, match="disabled in production"):
        seed.seed_demo_quotations()
