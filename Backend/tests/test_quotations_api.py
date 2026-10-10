import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.seed import seed_admin
from app.services.pdf_service import generate_pdf, _number_to_words_fr

client = TestClient(app)


def test_create_quotation_missing_required_fields_returns_422():
    seed_admin("admin123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "client_name": "Client Test",
        "client_email": "client@test.com",
        "articles": [
            {
                "designation": "Service",
                "quantity": 1,
                "unit": "h",
                "unit_price": 100,
            }
        ],
    }

    response = client.post(
        "/api/v1/quotations/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422
    assert any(
        error["loc"][-1] == "validity_date" for error in response.json()["detail"]
    )
    assert any(
        error["loc"][-1] == "delivery_duration" for error in response.json()["detail"]
    )
    assert any(
        error["loc"][-1] == "incoterm" for error in response.json()["detail"]
    )


def test_generate_pdf_requires_weasyprint(monkeypatch):
    class FakeQuotation:
        reference = "Q-TEST-001"

    monkeypatch.setattr("app.services.pdf_service.WEASYPRINT_AVAILABLE", False)
    monkeypatch.setattr("app.services.pdf_service.HTML", None)

    with pytest.raises(RuntimeError, match="WeasyPrint"):
        generate_pdf(FakeQuotation())


def test_number_to_words_handles_large_amounts():
    text = _number_to_words_fr(2517000)
    assert "deux" in text.lower()
    assert "mille" in text.lower()
    assert "fcfa" in text.lower()


def test_create_quotation_persists_incoterm_value():
    seed_admin("admin123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {
        "client_name": "Client DDP",
        "client_email": "ddp@example.com",
        "validity_date": "2026-12-31",
        "delivery_duration": "15 jours",
        "incoterm": "DDP",
        "articles": [
            {
                "designation": "Produit A",
                "quantity": 2,
                "unit": "u",
                "unit_price": 100,
            }
        ],
    }

    response = client.post(
        "/api/v1/quotations/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["incoterm"] == "DDP"


def test_pdf_renders_incoterm_value_instead_of_approval_block():
    from app.services.pdf_service import render_quotation_html
    from app.models.quotation import QuotationStatus

    quotation = type(
        "QuotationStub",
        (),
        {
            "reference": "Q-INCOTERM-001",
            "client_name": "Client X",
            "client_email": "client@example.com",
            "creation_date": "2026-09-01",
            "validity_date": "2026-12-31",
            "delivery_duration": "15 jours",
            "incoterm": "EXW",
            "status": QuotationStatus.ENVOYEE,
            "articles": [
                type(
                    "ArticleStub",
                    (),
                    {"designation": "Produit", "quantity": 1, "unit": "u", "unit_price": 120.0, "line_total": 120.0},
                )()
            ],
            "total_amount": 120.0,
        },
    )()

    html = render_quotation_html(quotation)
    assert "Incoterm" in html
    assert "EXW" in html
    assert "Bon pour accord" not in html


def test_auth_me_returns_current_user_profile_for_each_role():
    seed_admin("admin123")
    for email, full_name, expected_role in [
        ("admin@example.com", "Admin", "ADMIN"),
        ("manager@example.com", "Manager", "RESPONSABLE"),
        ("collab@example.com", "Collaborateur", "COLLABORATEUR"),
    ]:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "admin123"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["email"] == email
        assert payload["full_name"] == full_name
        assert payload["role"] == expected_role


def test_change_password_rejects_wrong_old_password_and_updates_after_confirmation():
    seed_admin("admin123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": "admin123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    bad_old = client.patch(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "wrongpass",
            "new_password": "NouveauMotDePasse123",
            "confirm_password": "NouveauMotDePasse123",
        },
    )
    assert bad_old.status_code == 400
    assert "Ancien mot de passe" in bad_old.json()["detail"]

    valid_change = client.patch(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "admin123",
            "new_password": "NouveauMotDePasse123",
            "confirm_password": "NouveauMotDePasse123",
        },
    )
    assert valid_change.status_code == 200, valid_change.text
    assert valid_change.json()["message"] == "Mot de passe modifié avec succès."

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": "admin123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": "NouveauMotDePasse123"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]


def test_change_password_requires_confirmation_match():
    seed_admin("admin123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "collab@example.com", "password": "admin123"},
    )
    token = login.json()["access_token"]

    response = client.patch(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "admin123",
            "new_password": "Password12345",
            "confirm_password": "Password54321",
        },
    )

    assert response.status_code == 400
    assert "confirmation" in response.json()["detail"].lower()
