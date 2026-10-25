from decimal import Decimal
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PyPDF2 import PdfReader

from app.main import app
from app.core.config import settings
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
                "line_total": 0.01,
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
    assert response.json()["total_amount"] == 200
    assert Decimal(response.json()["articles"][0]["line_total"]) == Decimal("200.00")

    quotation_id = response.json()["id"]
    retrieved = client.get(
        f"/api/v1/quotations/{quotation_id}",
        headers=response.request.headers,
    )
    assert retrieved.status_code == 200, retrieved.text
    assert retrieved.json()["total_amount"] == 200


def test_create_quotation_persists_vat_and_payment_terms():
    seed_admin("admin123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post(
        "/api/v1/quotations/",
        headers=headers,
        json={
            "client_name": "Client TVA",
            "client_email": "tva@example.com",
            "validity_date": "2026-12-31",
            "delivery_duration": "10 jours",
            "incoterm": "DDP",
            "vat_mode": "avec_tva",
            "vat_code": "CODE-TEST",
            "vat_rate": 18,
            "payment_method": "Virement bancaire",
            "payment_terms": "30 jours",
            "articles": [
                {
                    "designation": "Prestation taxable",
                    "quantity": 2,
                    "unit": "u",
                    "unit_price": 100,
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["vat_mode"] == "avec_tva"
    assert data["vat_code"] == "CODE-TEST"
    assert Decimal(data["vat_rate"]) == Decimal("18.00")
    assert Decimal(data["vat_amount"]) == Decimal("36.00")
    assert Decimal(data["total_amount"]) == Decimal("200.00")
    assert Decimal(data["total_including_tax"]) == Decimal("236.00")
    assert data["payment_method"] == "Virement bancaire"
    assert data["payment_terms"] == "30 jours"

    rate_update = client.put(
        f"/api/v1/quotations/{data['id']}",
        headers=headers,
        json={"vat_rate": 12},
    )
    assert rate_update.status_code == 200, rate_update.text
    assert rate_update.json()["vat_code"] == "CODE-TEST"
    assert Decimal(rate_update.json()["vat_rate"]) == Decimal("12.00")
    assert Decimal(rate_update.json()["vat_amount"]) == Decimal("24.00")

    invalid_code_update = client.put(
        f"/api/v1/quotations/{data['id']}",
        headers=headers,
        json={"vat_code": "   "},
    )
    assert invalid_code_update.status_code == 422

    updated = client.put(
        f"/api/v1/quotations/{data['id']}",
        headers=headers,
        json={
            "vat_mode": "sans_tva",
            "payment_method": None,
            "payment_terms": None,
        },
    )

    assert updated.status_code == 200, updated.text
    updated_data = updated.json()
    assert updated_data["vat_mode"] == "sans_tva"
    assert updated_data["vat_code"] is None
    assert updated_data["vat_rate"] is None
    assert Decimal(updated_data["vat_amount"]) == Decimal("0.00")
    assert Decimal(updated_data["total_including_tax"]) == Decimal("200.00")
    assert updated_data["payment_method"] is None
    assert updated_data["payment_terms"] is None


def test_download_quotation_pdf_returns_generated_document(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "PDF_STORAGE_PATH", str(tmp_path))
    seed_admin("admin123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post(
        "/api/v1/quotations/",
        headers=headers,
        json={
            "client_name": "Client PDF API",
            "client_email": "client-pdf@example.com",
            "validity_date": "2026-12-31",
            "delivery_duration": "10 jours",
            "incoterm": "DDP",
            "articles": [
                {
                    "designation": "Prestation via route API",
                    "quantity": 2,
                    "unit": "h",
                    "unit_price": 1250,
                }
            ],
        },
    )
    assert created.status_code == 200, created.text

    downloaded = client.get(
        f"/api/v1/quotations/{created.json()['id']}/pdf",
        headers=headers,
    )

    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert downloaded.content.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(downloaded.content))
    text = " ".join(" ".join(page.extract_text() or "" for page in reader.pages).split())
    assert "Prestation via route API" in text
    assert "2 500 FCFA" in text


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
    assert "Sans TVA" in html
    assert "Total TTC" in html
    assert "Virement bancaire" not in html
    assert "À la commande" not in html
    assert "Total HT</span>" in html


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
