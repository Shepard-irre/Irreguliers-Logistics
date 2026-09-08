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
from routers import sessions

MINEUR_USER = {"sub": "12", "username": "Shepard40", "permissions": ["page_raffineries"]}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(sessions.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    app.dependency_overrides[auth.get_current_user] = lambda: MINEUR_USER
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_create_session_calls_uex_with_requester_and_star_system(fake_uex, client):
    fake_uex.create_mining_session.return_value = {"id": 4, "numero": "MIN004"}

    resp = client.post("/raffineries/sessions", json={"star_system": "Pyro"})

    assert resp.status_code == 200
    fake_uex.create_mining_session.assert_called_once_with("Shepard40", "Pyro")
    assert resp.json() == {"id": 4, "numero": "MIN004"}


def test_list_sessions_returns_uex_result_as_records(fake_uex, client):
    fake_uex.get_mining_sessions.return_value = pd.DataFrame(
        [{"id": 4, "numero": "MIN004", "star_system": "Pyro", "status": "open"}]
    )

    resp = client.get("/raffineries/sessions")

    assert resp.status_code == 200
    fake_uex.get_mining_sessions.assert_called_once_with()
    assert resp.json() == [{"id": 4, "numero": "MIN004", "star_system": "Pyro", "status": "open"}]


def test_get_session_detail_returns_uex_result(fake_uex, client):
    fake_uex.get_mining_session.return_value = {
        "id": 4,
        "numero": "MIN004",
        "star_system": "Pyro",
        "status": "open",
        "created_by": "Shepard40",
        "ships": [],
        "expenses": [],
        "jobs": [],
    }

    resp = client.get("/raffineries/sessions/4")

    assert resp.status_code == 200
    fake_uex.get_mining_session.assert_called_once_with(4)
    assert resp.json()["numero"] == "MIN004"


def test_get_session_detail_404_when_missing(fake_uex, client):
    fake_uex.get_mining_session.return_value = None

    resp = client.get("/raffineries/sessions/999")

    assert resp.status_code == 404


def test_close_session(fake_uex, client):
    resp = client.post("/raffineries/sessions/4/close")

    assert resp.status_code == 200
    fake_uex.set_session_status.assert_called_once_with(4, "completed")


def test_add_ship(fake_uex, client):
    fake_uex.add_session_ship.return_value = 9

    resp = client.post(
        "/raffineries/sessions/4/ships",
        json={"ship_name": "Prospector", "ship_role": "mining"},
    )

    assert resp.status_code == 200
    fake_uex.add_session_ship.assert_called_once_with(4, "Prospector", "mining")
    assert resp.json() == {"id": 9}


def test_remove_ship(fake_uex, client):
    resp = client.delete("/raffineries/sessions/ships/9")

    assert resp.status_code == 200
    fake_uex.remove_session_ship.assert_called_once_with(9)


def test_add_crew_member(fake_uex, client):
    resp = client.post("/raffineries/sessions/ships/9/crew", json={"username": "Darkias"})

    assert resp.status_code == 200
    fake_uex.add_crew_member.assert_called_once_with(9, "Darkias")


def test_remove_crew_member(fake_uex, client):
    resp = client.delete("/raffineries/sessions/crew/22")

    assert resp.status_code == 200
    fake_uex.remove_crew_member.assert_called_once_with(22)


def test_add_expense(fake_uex, client):
    fake_uex.add_session_expense.return_value = 6

    resp = client.post(
        "/raffineries/sessions/4/expenses",
        json={"description": "Carburant Prospector", "amount_auec": 1500},
    )

    assert resp.status_code == 200
    fake_uex.add_session_expense.assert_called_once_with(4, "Carburant Prospector", 1500)
    assert resp.json() == {"id": 6}


def test_remove_expense(fake_uex, client):
    resp = client.delete("/raffineries/sessions/expenses/6")

    assert resp.status_code == 200
    fake_uex.remove_session_expense.assert_called_once_with(6)


def test_financial_summary_computes_shares_from_best_matching_market_price(fake_uex, client):
    fake_uex.get_session_financial_summary.return_value = {
        "session": {"id": 4, "star_system": "Stanton"},
        "crew": ["Shepard40", "Darkias", "Camus68"],
        "nb_joueurs": 3,
        "expenses": [{"description": "Carburant", "amount_auec": 1000}],
        "total_expenses": 1000,
        "orders_vente": [{"commodity_name": "Quantainium", "quantity": 100}],
        "orders_stock_fed": [],
    }
    fake_uex.get_commodities.return_value = [{"id": 5, "name": "Quantainium"}]
    fake_uex.get_prices_for_item.return_value = [
        {"price_sell": 50, "star_system_name": "Stanton"},
        {"price_sell": 999, "star_system_name": "Pyro"},
    ]

    resp = client.get("/raffineries/sessions/4/financial-summary")

    assert resp.status_code == 200
    fake_uex.get_prices_for_item.assert_called_once_with(5)
    body = resp.json()
    assert body["total_vente_auec"] == 5000
    assert body["part_federation"] == 1000
    assert body["part_transport"] == 750
    assert body["reste_a_partager"] == 2250
    assert body["salaire_par_joueur"] == 750
    assert body["vente_lines"] == [
        {"commodity_name": "Quantainium", "quantity": 100, "price_per_scu": 50, "estimated_revenue": 5000}
    ]


def test_financial_summary_computes_personnel_settlement(fake_uex, client):
    fake_uex.get_session_financial_summary.return_value = {
        "session": {"id": 4, "star_system": "Stanton", "created_by": "Shepard40"},
        "crew": ["Shepard40", "Darkias"],
        "nb_joueurs": 2,
        "transport_crew": ["Camus68"],
        "expenses": [],
        "total_expenses": 0,
        "orders_vente": [],
        "orders_stock_fed": [],
        "orders_personnel": [{"commodity_name": "Quantainium", "quantity": 100}],
    }
    fake_uex.get_commodities.return_value = [{"id": 5, "name": "Quantainium"}]
    fake_uex.get_prices_for_item.return_value = [{"price_sell": 50, "star_system_name": "Stanton"}]

    resp = client.get("/raffineries/sessions/4/financial-summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["personnel_settlement"] == {
        "payer": "Shepard40",
        "recette": 5000,
        "part_federation": 1000,
        "part_transport": 750,
        "reste": 3250,
        "salaire_par_joueur": 1625,
    }
    assert body["federal_settlement"] is None
    assert body["has_orders"] is True


def test_financial_summary_computes_federal_settlement_without_transport_cost(fake_uex, client):
    fake_uex.get_session_financial_summary.return_value = {
        "session": {"id": 4, "star_system": "Stanton", "created_by": "Shepard40"},
        "crew": ["Shepard40", "Darkias"],
        "nb_joueurs": 2,
        "transport_crew": [],
        "expenses": [],
        "total_expenses": 0,
        "orders_vente": [],
        "orders_stock_fed": [{"commodity_name": "Quantainium", "quantity": 100}],
        "orders_personnel": [],
    }
    fake_uex.get_commodities.return_value = [{"id": 5, "name": "Quantainium"}]
    fake_uex.get_prices_for_item.return_value = [{"price_sell": 50, "star_system_name": "Stanton"}]

    resp = client.get("/raffineries/sessions/4/financial-summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["federal_settlement"] == {
        "payer": "Fédération",
        "recette": 5000,
        "part_federation": 1000,
        "part_transport": 0,
        "reste": 4000,
        "salaire_par_joueur": 2000,
    }
    assert body["personnel_settlement"] is None


def test_financial_summary_404_when_session_missing(fake_uex, client):
    fake_uex.get_session_financial_summary.return_value = None

    resp = client.get("/raffineries/sessions/999/financial-summary")

    assert resp.status_code == 404
