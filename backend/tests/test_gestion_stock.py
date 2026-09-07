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
from routers import gestion_stock

GESTIONNAIRE_USER = {"sub": "12", "username": "Shepard40", "permissions": ["page_gestion_stock"]}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(gestion_stock.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    app.dependency_overrides[auth.get_current_user] = lambda: GESTIONNAIRE_USER
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_list_categories_returns_the_category_map(fake_uex, client):
    resp = client.get("/gestion-stock/categories")

    assert resp.status_code == 200
    body = resp.json()
    assert "Boucliers (Shields)" in [c["label"] for c in body]


def test_list_items_combines_all_category_ids(fake_uex, client):
    def fake_items(cat_id):
        return {22: [{"id": 1, "name": "Item22"}], 86: [{"id": 2, "name": "Item86"}]}.get(cat_id, [])
    fake_uex.get_items_by_category.side_effect = fake_items

    resp = client.get("/gestion-stock/items?category_ids=22,86")

    assert resp.status_code == 200
    assert resp.json() == [{"id": 1, "name": "Item22"}, {"id": 2, "name": "Item86"}]


def test_item_prices(fake_uex, client):
    fake_uex.get_item_prices_by_id.return_value = [{"terminal_name": "Area18", "price_buy": 5000}]

    resp = client.get("/gestion-stock/items/7/prices")

    assert resp.status_code == 200
    fake_uex.get_item_prices_by_id.assert_called_once_with(7)
    assert resp.json() == [{"terminal_name": "Area18", "price_buy": 5000}]


def test_add_to_stock_calls_update_stock_with_requester(fake_uex, client):
    resp = client.post(
        "/gestion-stock/stock",
        json={
            "item_id": 7,
            "name": "Shield Gen X",
            "category": "Boucliers (Shields)",
            "size": "2",
            "quantity": 3,
        },
    )

    assert resp.status_code == 200
    fake_uex.update_stock.assert_called_once_with(
        "Shepard40", 7, "Shield Gen X", "Boucliers (Shields)", "2", 3
    )


def test_inventory_returns_all_items_including_hidden(fake_uex, client):
    fake_uex.get_full_inventory.return_value = pd.DataFrame(
        [{"item_id": 1, "Nom": "Shield Gen X", "Type": "Boucliers", "Qté": 3, "Caché": 0}]
    )

    resp = client.get("/gestion-stock/inventory")

    assert resp.status_code == 200
    fake_uex.get_full_inventory.assert_called_once_with(can_see_hidden=True)
    assert resp.json()[0]["Nom"] == "Shield Gen X"


def test_toggle_visibility(fake_uex, client):
    resp = client.post("/gestion-stock/items/7/visibility", json={"is_hidden": True})

    assert resp.status_code == 200
    fake_uex.toggle_item_hidden.assert_called_once_with(7, True)


def test_logs(fake_uex, client):
    fake_uex.get_logs.return_value = pd.DataFrame(
        [{"Date": "2026-09-07 10:00:00", "Pilote": "Shepard40", "Action": "ENTRÉE", "Qté": 3, "Article": "Shield Gen X"}]
    )

    resp = client.get("/gestion-stock/logs")

    assert resp.status_code == 200
    assert resp.json()[0]["Pilote"] == "Shepard40"
