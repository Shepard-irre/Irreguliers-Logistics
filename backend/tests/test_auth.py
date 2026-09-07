import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import auth

FAKE_USER = {
    "id": 12,
    "username": "Shepard40",
    "email": "shepard40@example.com",
    "roles": [{"id": "um_custom_role_5", "name": "Mineur"}],
    "permissions": ["page_raffineries", "page_commerce"],
}


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(auth.router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_login_success(monkeypatch, client):
    monkeypatch.setattr(auth._wp, "authenticate", lambda u, p: FAKE_USER)

    resp = client.post("/auth/login", json={"username": "Shepard40", "password": "whatever"})

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["username"] == "Shepard40"
    assert body["user"]["permissions"] == ["page_raffineries", "page_commerce"]


def test_login_invalid_credentials(monkeypatch, client):
    monkeypatch.setattr(auth._wp, "authenticate", lambda u, p: None)

    resp = client.post("/auth/login", json={"username": "Shepard40", "password": "wrong"})

    assert resp.status_code == 401


def test_sso_success(monkeypatch, client):
    monkeypatch.setattr(auth._wp, "authenticate_with_token", lambda t: FAKE_USER)

    resp = client.post("/auth/sso", json={"token": "some-wp-sso-token"})

    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "Shepard40"


def test_sso_invalid_token(monkeypatch, client):
    monkeypatch.setattr(auth._wp, "authenticate_with_token", lambda t: None)

    resp = client.post("/auth/sso", json={"token": "bad-token"})

    assert resp.status_code == 401


def test_require_permission_allows_when_present():
    user_payload = {"permissions": ["page_raffineries"]}
    checker = auth.require_permission("page_raffineries")

    # require_permission's inner checker takes the resolved user as a plain arg
    # when called directly (outside FastAPI's Depends resolution).
    assert checker(user=user_payload) == user_payload


def test_require_permission_rejects_when_missing():
    user_payload = {"permissions": ["page_commerce"]}
    checker = auth.require_permission("page_raffineries")

    with pytest.raises(HTTPException) as exc_info:
        checker(user=user_payload)

    assert exc_info.value.status_code == 403
