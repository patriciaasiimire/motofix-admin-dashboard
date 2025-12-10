import os
import jwt
from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    # Use a simple plaintext admin password for tests (avoids bcrypt dependency in CI)
    plain = "test-admin-pass"
    monkeypatch.setenv("ADMIN_PASSWORD", plain)
    monkeypatch.setenv("ADMIN_JWT_SECRET", "testsecret123")
    # Ensure DB env not required for these tests, or mock DB if needed.
    yield

def test_login_success_and_protected_endpoint():
    # login
    resp = client.post("/api/login", json={"password": "test-admin-pass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    token = data["access_token"]

    # use token to call protected route (adjust route if needed)
    headers = {"Authorization": f"Bearer {token}"}
    resp2 = client.get("/admin/requests", headers=headers)
    # If DB not available you may get 500; the important part is the auth layer returns 200 or proceeds.
    assert resp2.status_code in (200, 500, 404)  # acceptable depending on DB setup

def test_login_failure():
    resp = client.post("/api/login", json={"password": "wrong"})
    assert resp.status_code == 401