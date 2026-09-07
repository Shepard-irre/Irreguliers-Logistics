import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

import auth
from main import app

client = TestClient(app)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_auth_router_is_mounted(monkeypatch):
    # Stub WPAuth so this stays a wiring check, not a live call to the WP staging site.
    monkeypatch.setattr(auth._wp, "authenticate", lambda u, p: None)
    resp = client.post("/auth/login", json={"username": "nobody", "password": "nope"})
    assert resp.status_code == 401


def test_raffineries_router_is_mounted():
    # No Authorization header — confirms raffineries.router is wired in and guarded.
    resp = client.get("/raffineries/jobs")
    assert resp.status_code == 401
