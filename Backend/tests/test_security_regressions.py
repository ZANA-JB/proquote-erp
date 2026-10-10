from datetime import date
from decimal import Decimal
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest

from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_admin
from app.main import app
from app.models.article import Article
from app.models.access_request import AccessRequest
from app.models.quotation import Quotation, QuotationStatus
from app.models.user import User
from app.services.pdf_service import _sanitize_reference


client = TestClient(app)
TEST_PASSWORD = "test-only-password"


@pytest.fixture(scope="module", autouse=True)
def initialize_test_database():
    Base.metadata.create_all(bind=engine)


def _login(email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _create_quotation(created_by: str) -> tuple[str, str]:
    quotation_id = str(uuid.uuid4())
    article_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        quotation = Quotation(
            id=quotation_id,
            reference=f"SEC-{quotation_id}",
            client_name="Security test client",
            client_email="client@example.com",
            creation_date=date.today(),
            status=QuotationStatus.BROUILLON,
            total_amount=Decimal("10.00"),
            created_by=created_by,
        )
        article = Article(
            id=article_id,
            designation="Security test item",
            quantity=Decimal("1"),
            unit="u",
            unit_price=Decimal("10.00"),
            line_total=Decimal("10.00"),
            quotation=quotation,
        )
        db.add(quotation)
        db.add(article)
        db.commit()
        return quotation_id, article_id
    finally:
        db.close()


def test_access_request_never_returns_or_stores_plaintext_password():
    seed_admin(TEST_PASSWORD)
    email = f"request-{uuid.uuid4()}@example.com"
    response = client.post(
        "/api/v1/access-requests",
        json={
            "nomComplet": "Security test",
            "email": email,
            "motDePasse": "new-request-password-123",
            "profilSouhaite": "COMMERCIAL",
        },
    )

    assert response.status_code == 200, response.text
    assert "motDePasse" not in response.json()
    assert "new-request-password-123" not in response.text

    db = SessionLocal()
    try:
        request = db.query(AccessRequest).filter(AccessRequest.email == email).one()
        assert request.password_hash.startswith("$pbkdf2-sha256$")
    finally:
        db.close()


def test_logout_revokes_existing_bearer_token():
    seed_admin(TEST_PASSWORD)
    token = _login("admin@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200, logout.text
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_collaborator_cannot_read_or_change_another_users_quotation_children(monkeypatch, tmp_path: Path):
    seed_admin(TEST_PASSWORD)
    db = SessionLocal()
    try:
        collaborator = db.query(User).filter(User.email == "collab@example.com").one()
        other_collaborator = User(
            id=str(uuid.uuid4()),
            email=f"other-{uuid.uuid4()}@example.com",
            hashed_password="unused-test-hash",
            full_name="Other collaborator",
            role=collaborator.role,
            is_active=True,
        )
        db.add(other_collaborator)
        db.commit()
        other_user_id = other_collaborator.id
    finally:
        db.close()

    quotation_id, article_id = _create_quotation(other_user_id)
    token = _login("collab@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    pdf_path = tmp_path / "private.pdf"
    pdf_path.write_bytes(b"private test pdf")

    import app.routers.quotations as quotation_routes

    monkeypatch.setattr(quotation_routes, "generate_pdf", lambda _quotation: str(pdf_path))

    assert client.get(f"/api/v1/quotations/{quotation_id}", headers=headers).status_code == 403
    assert client.get(f"/api/v1/quotations/{quotation_id}/history", headers=headers).status_code == 403
    assert client.get(f"/api/v1/quotations/{quotation_id}/pdf", headers=headers).status_code == 403
    assert client.post(f"/api/v1/quotations/{quotation_id}/generate-pdf", headers=headers).status_code == 403
    assert client.get(f"/api/v1/quotations/{quotation_id}/reminders", headers=headers).status_code == 403
    assert client.post(
        f"/api/v1/quotations/{quotation_id}/articles",
        headers=headers,
        json={"designation": "Unauthorized", "quantity": 1, "unit": "u", "unit_price": 1},
    ).status_code == 403
    assert client.put(
        f"/api/v1/quotations/{quotation_id}/articles/{article_id}",
        headers=headers,
        json={"designation": "Unauthorized", "quantity": 1, "unit": "u", "unit_price": 1},
    ).status_code == 403


def test_user_responses_never_include_password_hashes():
    seed_admin(TEST_PASSWORD)
    token = _login("admin@example.com")
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert all("hashed_password" not in user for user in response.json())


def test_pdf_reference_cannot_escape_storage_filename():
    sanitized = _sanitize_reference("../../private\\secret.pdf")
    assert "/" not in sanitized
    assert "\\" not in sanitized
    assert sanitized not in (".", "..")
