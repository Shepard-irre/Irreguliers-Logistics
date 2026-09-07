import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import deps
from routers import commerce_federation

USER = {"sub": "12", "username": "Shepard40", "permissions": ["page_commerce_federation"]}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(commerce_federation.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    app.dependency_overrides[auth.get_current_user] = lambda: USER
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_fed_prices_combines_commodities_with_set_prices(fake_uex, client):
    fake_uex.get_commodities.return_value = [{"id": 1, "name": "Quantainium"}, {"id": 2, "name": "Agricium"}]
    fake_uex.get_all_fed_prices.return_value = {1: 45.0}

    resp = client.get("/commerce-federation/fed-prices")

    assert resp.status_code == 200
    assert resp.json() == [
        {"commodity_id": 1, "name": "Quantainium", "price_fed": 45.0},
        {"commodity_id": 2, "name": "Agricium", "price_fed": 0.0},
    ]


def test_set_fed_price(fake_uex, client):
    resp = client.post("/commerce-federation/fed-prices", json={"commodity_id": 1, "price": 50})

    assert resp.status_code == 200
    fake_uex.set_fed_price.assert_called_once_with(1, 50)


def test_best_price_returns_max_sell_price(fake_uex, client):
    fake_uex.get_prices_for_item.return_value = [
        {"price_sell": 40, "terminal_name": "A"},
        {"price_sell": 60, "terminal_name": "B"},
        {"price_sell": 0, "terminal_name": "C"},
    ]

    resp = client.get("/commerce-federation/best-price?commodity_id=1")

    assert resp.status_code == 200
    assert resp.json() == {"price_sell": 60}
