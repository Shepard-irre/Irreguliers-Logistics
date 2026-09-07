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
from routers import stock_federation

MEMBRE_USER = {"sub": "12", "username": "Shepard40", "permissions": ["page_stock_federation"]}
GESTIONNAIRE_USER = {"sub": "1", "username": "Darkias", "permissions": ["page_stock_federation", "page_gestion_stock"]}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(stock_federation.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    return app


@pytest.fixture
def client_as(app):
    def _client_as(user):
        app.dependency_overrides[auth.get_current_user] = lambda: user
        return TestClient(app)
    return _client_as


def test_summary_combines_inventory_lots_and_wallet(fake_uex, client_as):
    fake_uex.get_full_inventory.return_value = pd.DataFrame([{"Qté": 5}, {"Qté": 3}])
    fake_uex.get_commodity_lots.return_value = pd.DataFrame(
        [{"SCU": 10.0, "Bloqué": 0}, {"SCU": 5.0, "Bloqué": 1}]
    )
    fake_uex.get_wallet.return_value = {"balance": 42000}
    client = client_as(MEMBRE_USER)

    resp = client.get("/stock-federation/summary")

    assert resp.status_code == 200
    assert resp.json() == {"total_components": 8, "total_minerals": 10.0, "fed_balance": 42000}


def test_inventory_hides_hidden_items_for_non_gestionnaire(fake_uex, client_as):
    fake_uex.get_full_inventory.return_value = pd.DataFrame([{"Nom": "X"}])
    client = client_as(MEMBRE_USER)

    resp = client.get("/stock-federation/inventory")

    assert resp.status_code == 200
    fake_uex.get_full_inventory.assert_called_once_with(can_see_hidden=False)


def test_inventory_shows_hidden_items_for_gestionnaire(fake_uex, client_as):
    fake_uex.get_full_inventory.return_value = pd.DataFrame([{"Nom": "X"}])
    client = client_as(GESTIONNAIRE_USER)

    resp = client.get("/stock-federation/inventory")

    assert resp.status_code == 200
    fake_uex.get_full_inventory.assert_called_once_with(can_see_hidden=True)


def test_lots_only_returns_unblocked(fake_uex, client_as):
    fake_uex.get_commodity_lots.return_value = pd.DataFrame(
        [{"Minerai": "A", "SCU": 10.0, "Qualité": 700, "Bloqué": 0},
         {"Minerai": "B", "SCU": 5.0, "Qualité": 500, "Bloqué": 1}]
    )
    client = client_as(MEMBRE_USER)

    resp = client.get("/stock-federation/lots")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["Minerai"] == "A"


def test_logs(fake_uex, client_as):
    fake_uex.get_logs.return_value = pd.DataFrame([{"Pilote": "Shepard40"}])
    client = client_as(MEMBRE_USER)

    resp = client.get("/stock-federation/logs")

    assert resp.status_code == 200
    assert resp.json()[0]["Pilote"] == "Shepard40"
