import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.seed import seed_admin

client = TestClient(app)


def test_auth_me_requires_token():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_login_and_me_flow():
    seed_admin("admin123")
    login = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    assert login.status_code == 200
    data = login.json()
    assert "access_token" in data
    token = data["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["email"] == "admin@example.com"
    assert me_data["role"] == "ADMIN"
