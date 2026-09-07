import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import deps
from routers import commerce

MEMBRE_USER = {"sub": "12", "username": "Shepard40", "permissions": ["page_commerce"]}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(commerce.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    app.dependency_overrides[auth.get_current_user] = lambda: MEMBRE_USER
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_list_commodities_returns_uex_result(fake_uex, client):
    fake_uex.get_commodities.return_value = [{"id": 1, "name": "Quantainium"}]

    resp = client.get("/commerce/commodities")

    assert resp.status_code == 200
    assert resp.json() == [{"id": 1, "name": "Quantainium"}]


def test_prices_returns_only_sellers_with_a_positive_price(fake_uex, client):
    fake_uex.get_prices_for_item.return_value = [
        {"terminal_name": "Port Olisar", "price_sell": 12, "star_system_name": "Stanton"},
        {"terminal_name": "Nowhere", "price_sell": 0, "star_system_name": "Stanton"},
    ]

    resp = client.get("/commerce/prices?commodity_id=1")

    assert resp.status_code == 200
    fake_uex.get_prices_for_item.assert_called_once_with(1)
    assert resp.json() == [{"terminal_name": "Port Olisar", "price_sell": 12, "star_system_name": "Stanton"}]
