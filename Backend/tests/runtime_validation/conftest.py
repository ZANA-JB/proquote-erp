import os
import uuid
from datetime import date, timedelta

import httpx
import pytest


API_BASE_URL = os.getenv("RUNTIME_API_URL")
ADMIN_EMAIL = os.getenv("RUNTIME_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("RUNTIME_ADMIN_PASSWORD")


@pytest.fixture(scope="session")
def api_client():
    if not API_BASE_URL:
        pytest.skip("Set RUNTIME_API_URL to run live integration tests.")
    with httpx.Client(base_url=f"{API_BASE_URL.rstrip('/')}/api/v1", timeout=60) as client:
        yield client


@pytest.fixture(scope="session")
def admin_headers(api_client):
    if not ADMIN_PASSWORD:
        pytest.skip("Set RUNTIME_ADMIN_PASSWORD to run authenticated integration tests.")
    response = api_client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_quotation(api_client, headers):
    unique = uuid.uuid4().hex[:10]
    response = api_client.post(
        "/quotations/",
        headers=headers,
        json={
            "client_name": f"Runtime Client {unique}",
            "client_email": f"runtime-{unique}@example.com",
            "client_address": "Integration test address",
            "client_reference": f"runtime-{unique}",
            "validity_date": (date.today() + timedelta(days=30)).isoformat(),
            "delivery_duration": "5 jours",
            "incoterm": "CLIENT",
            "special_conditions": "Runtime integration test",
            "articles": [
                {
                    "designation": "Runtime PDF verification service",
                    "quantity": 2,
                    "unit": "u",
                    "unit_price": 1250,
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
