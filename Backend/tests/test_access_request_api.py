from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_access_request_success():
    payload = {
        "nomComplet": "Jean Dupont",
        "email": "jean.dupont@gmail.com",
        "motDePasse": "secret-request-123",
        "profilSouhaite": "COMMERCIAL",
    }

    response = client.post("/api/v1/access-requests", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["nomComplet"] == "Jean Dupont"
    assert data["email"] == "jean.dupont@gmail.com"
    assert "motDePasse" not in data
    assert data["profilSouhaite"] == "COMMERCIAL"
    assert "id" in data


def test_create_access_request_rejects_invalid_profile():
    payload = {
        "nomComplet": "Jean Dupont",
        "email": "jean.dupont@gmail.com",
        "motDePasse": "secret-request-123",
        "profilSouhaite": "ADMINISTRATEUR",
    }

    response = client.post("/api/v1/access-requests", json=payload)

    assert response.status_code == 422
