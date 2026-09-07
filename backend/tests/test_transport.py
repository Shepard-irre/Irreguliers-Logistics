import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import deps
from routers import transport

TRANSPORTEUR = {"sub": "12", "username": "Camus68", "permissions": ["page_transport"]}
ADMIN = {"sub": "1", "username": "Darkias", "permissions": ["page_transport", "admin_panel"]}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(transport.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    return app


@pytest.fixture
def client_as(app):
    def _client_as(user):
        app.dependency_overrides[auth.get_current_user] = lambda: user
        return TestClient(app)
    return _client_as


def test_list_orders_scopes_to_assignee_for_non_admin(fake_uex, client_as):
    fake_uex.get_transport_orders.return_value = pd.DataFrame([{"id": 1, "status": "pending"}])
    client = client_as(TRANSPORTEUR)

    resp = client.get("/transport/orders?status=pending")

    assert resp.status_code == 200
    fake_uex.get_transport_orders.assert_called_once_with(assignee="Camus68", status="pending")


def test_list_orders_sees_everyone_for_admin(fake_uex, client_as):
    fake_uex.get_transport_orders.return_value = pd.DataFrame([{"id": 1, "status": "pending"}])
    client = client_as(ADMIN)

    resp = client.get("/transport/orders?status=pending")

    assert resp.status_code == 200
    fake_uex.get_transport_orders.assert_called_once_with(assignee=None, status="pending")


def test_take_order_rejects_order_assigned_to_someone_else(fake_uex, client_as):
    other_transporteur = {"sub": "9", "username": "Nispi", "permissions": ["page_transport"]}
    fake_uex.get_transport_orders.return_value = pd.DataFrame(
        [{"id": 5, "assigned_to": "Camus68", "status": "pending"}]
    )
    client = client_as(other_transporteur)

    resp = client.post("/transport/orders/5/take")

    assert resp.status_code == 404
    fake_uex.update_transport_status.assert_not_called()


def test_take_order_by_assignee(fake_uex, client_as):
    fake_uex.get_transport_orders.return_value = pd.DataFrame(
        [{"id": 5, "assigned_to": "Camus68", "status": "pending"}]
    )
    client = client_as(TRANSPORTEUR)

    resp = client.post("/transport/orders/5/take")

    assert resp.status_code == 200
    fake_uex.update_transport_status.assert_called_once_with(5, "in_progress", "Camus68")


def test_deliver_order_by_assignee(fake_uex, client_as):
    fake_uex.get_transport_orders.return_value = pd.DataFrame(
        [{"id": 5, "assigned_to": "Camus68", "status": "in_progress"}]
    )
    client = client_as(TRANSPORTEUR)

    resp = client.post("/transport/orders/5/deliver")

    assert resp.status_code == 200
    fake_uex.update_transport_status.assert_called_once_with(5, "delivered", "Camus68")


def test_deliver_order_rejects_order_assigned_to_someone_else(fake_uex, client_as):
    other_transporteur = {"sub": "9", "username": "Nispi", "permissions": ["page_transport"]}
    fake_uex.get_transport_orders.return_value = pd.DataFrame(
        [{"id": 5, "assigned_to": "Camus68", "status": "in_progress"}]
    )
    client = client_as(other_transporteur)

    resp = client.post("/transport/orders/5/deliver")

    assert resp.status_code == 404
    fake_uex.update_transport_status.assert_not_called()


def test_take_order_admin_bypasses_ownership_check(fake_uex, client_as):
    client = client_as(ADMIN)

    resp = client.post("/transport/orders/5/take")

    assert resp.status_code == 200
    fake_uex.get_transport_orders.assert_not_called()
    fake_uex.update_transport_status.assert_called_once_with(5, "in_progress", "Darkias")
