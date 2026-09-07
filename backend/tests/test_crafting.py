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
from routers import crafting

MEMBRE = {"sub": "12", "username": "Shepard40", "permissions": ["page_crafting"]}
CRAFTEUR = {"sub": "3", "username": "Darkias", "permissions": ["page_crafting", "crafting_stock_view"]}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(crafting.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    return app


@pytest.fixture
def client_as(app):
    def _client_as(user):
        app.dependency_overrides[auth.get_current_user] = lambda: user
        return TestClient(app)
    return _client_as


def test_search_blueprints_without_stock_view_has_no_analysis(fake_uex, client_as):
    fake_uex.get_blueprints_from_api.return_value = {
        "items": [{"id": 1, "name": "Sniper Rifle", "ingredients": [{"name": "Laranite", "quantity_scu": 2, "min_quality": 500}]}],
        "pagination": {"total": 1},
    }
    client = client_as(MEMBRE)

    resp = client.get("/crafting/blueprints?search=sniper")

    assert resp.status_code == 200
    fake_uex.get_blueprints_from_api.assert_called_once_with(search="sniper", limit=20)
    body = resp.json()
    assert body["items"][0]["stock_analysis"] is None


def test_search_blueprints_with_stock_view_analyzes_ingredients(fake_uex, client_as):
    fake_uex.get_blueprints_from_api.return_value = {
        "items": [{
            "id": 1, "name": "Sniper Rifle",
            "ingredients": [{"slot": "A", "name": "Laranite", "quantity_scu": 2, "min_quality": 500}],
        }],
        "pagination": {"total": 1},
    }
    fake_uex.get_lots_for_ingredient.return_value = pd.DataFrame(
        [{"id": 1, "Minerai": "Laranite", "SCU": 5.0, "Qualité": 700, "Bloqué": 0}]
    )
    client = client_as(CRAFTEUR)

    resp = client.get("/crafting/blueprints?search=sniper")

    assert resp.status_code == 200
    fake_uex.get_lots_for_ingredient.assert_called_once_with("Laranite")
    analysis = resp.json()["items"][0]["stock_analysis"]
    assert analysis["stock_badge"] == "ok"
    assert analysis["rows"] == [{
        "slot": "A", "name": "Laranite", "required": 2.0, "min_quality": 500,
        "available_ok": 5.0, "available_total": 5.0, "status": "ok",
    }]


def test_lots_for_ingredient(fake_uex, client_as):
    fake_uex.get_lots_for_ingredient.return_value = pd.DataFrame(
        [{"id": 1, "Minerai": "Laranite", "SCU": 5.0, "Qualité": 700, "Bloqué": 0}]
    )
    client = client_as(CRAFTEUR)

    resp = client.get("/crafting/lots-for-ingredient?name=Laranite")

    assert resp.status_code == 200
    fake_uex.get_lots_for_ingredient.assert_called_once_with("Laranite")
    assert resp.json()[0]["Minerai"] == "Laranite"


def test_toggle_lot_blocked_requires_stock_view(fake_uex, client_as):
    client = client_as(MEMBRE)

    resp = client.post("/crafting/lots/1/toggle-block", json={"is_blocked": True})

    assert resp.status_code == 403
    fake_uex.toggle_lot_blocked.assert_not_called()


def test_toggle_lot_blocked(fake_uex, client_as):
    client = client_as(CRAFTEUR)

    resp = client.post("/crafting/lots/1/toggle-block", json={"is_blocked": True})

    assert resp.status_code == 200
    fake_uex.toggle_lot_blocked.assert_called_once_with(1, True, "Darkias")


def test_blocked_lots(fake_uex, client_as):
    fake_uex.get_blocked_lots.return_value = pd.DataFrame(
        [{"id": 1, "Minerai": "Laranite", "SCU": 2.0, "Qualité": 700, "Bloqué par": "Darkias"}]
    )
    client = client_as(MEMBRE)

    resp = client.get("/crafting/blocked-lots")

    assert resp.status_code == 200
    assert resp.json()[0]["Bloqué par"] == "Darkias"
