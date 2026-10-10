def test_login_profile_and_logout_invalidate_session(api_client):
    unauthenticated = api_client.get("/auth/me")
    assert unauthenticated.status_code == 401

    invalid_login = api_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "invalid-runtime-password"},
    )
    assert invalid_login.status_code == 401

    import os

    login = api_client.post(
        "/auth/login",
        json={
            "email": os.getenv("RUNTIME_ADMIN_EMAIL", "admin@example.com"),
            "password": os.environ["RUNTIME_ADMIN_PASSWORD"],
        },
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    profile = api_client.get("/auth/me", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["role"] == "ADMIN"

    logout = api_client.post("/auth/logout", headers=headers)
    assert logout.status_code == 200, logout.text
    assert api_client.get("/auth/me", headers=headers).status_code == 401
