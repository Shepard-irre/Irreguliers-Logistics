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
ADMIN_USER = {"sub": "1", "username": "Darkias", "permissions": ["page_raffineries", "admin_panel"]}


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


@pytest.fixture
def client_as(app):
    def _client_as(user):
        app.dependency_overrides[auth.get_current_user] = lambda: user
        return TestClient(app)
    return _client_as


def test_list_members_for_crew_autocomplete(fake_uex, client):
    fake_uex.get_wp_members.return_value = [
        {"username": "Shepard40", "display_name": "Shepard40"},
        {"username": "Darkias", "display_name": "Darkias"},
    ]

    resp = client.get("/raffineries/sessions/members")

    assert resp.status_code == 200
    assert resp.json() == [
        {"username": "Shepard40", "display_name": "Shepard40"},
        {"username": "Darkias", "display_name": "Darkias"},
    ]


def test_create_session_calls_uex_with_requester_and_star_system(fake_uex, client):
    fake_uex.create_mining_session.return_value = {"id": 4, "numero": "MIN004"}

    resp = client.post("/raffineries/sessions", json={"star_system": "Pyro"})

    assert resp.status_code == 200
    fake_uex.create_mining_session.assert_called_once_with("Shepard40", "Pyro")
    assert resp.json() == {"id": 4, "numero": "MIN004"}


def test_list_sessions_scoped_to_own_username_for_non_admin(fake_uex, client):
    fake_uex.get_mining_sessions.return_value = pd.DataFrame(
        [{"id": 4, "numero": "MIN004", "star_system": "Pyro", "status": "open"}]
    )

    resp = client.get("/raffineries/sessions")

    assert resp.status_code == 200
    fake_uex.get_mining_sessions.assert_called_once_with(participant="Shepard40")
    assert resp.json() == [{"id": 4, "numero": "MIN004", "star_system": "Pyro", "status": "open"}]


def test_list_sessions_sees_everyone_for_admin(fake_uex, client_as):
    fake_uex.get_mining_sessions.return_value = pd.DataFrame(
        [{"id": 4, "numero": "MIN004", "star_system": "Pyro", "status": "open"}]
    )
    client = client_as(ADMIN_USER)

    resp = client.get("/raffineries/sessions")

    assert resp.status_code == 200
    fake_uex.get_mining_sessions.assert_called_once_with(participant=None)


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


def test_get_session_detail_404_for_non_participant(fake_uex, client):
    fake_uex.get_mining_session.return_value = {
        "id": 4,
        "numero": "MIN004",
        "star_system": "Pyro",
        "status": "open",
        "created_by": "Camus68",
        "ships": [{"id": 1, "crew": [{"username": "Nispi1"}]}],
        "expenses": [],
        "jobs": [],
    }

    resp = client.get("/raffineries/sessions/4")

    assert resp.status_code == 404


def test_get_session_detail_visible_to_crew_member_not_creator(fake_uex, client):
    fake_uex.get_mining_session.return_value = {
        "id": 4,
        "numero": "MIN004",
        "star_system": "Pyro",
        "status": "open",
        "created_by": "Camus68",
        "ships": [{"id": 1, "crew": [{"username": "Shepard40"}]}],
        "expenses": [],
        "jobs": [],
    }

    resp = client.get("/raffineries/sessions/4")

    assert resp.status_code == 200


def test_get_session_detail_visible_to_admin_regardless(fake_uex, client_as):
    fake_uex.get_mining_session.return_value = {
        "id": 4,
        "numero": "MIN004",
        "star_system": "Pyro",
        "status": "open",
        "created_by": "Camus68",
        "ships": [],
        "expenses": [],
        "jobs": [],
    }
    resp = client_as(ADMIN_USER).get("/raffineries/sessions/4")

    assert resp.status_code == 200


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


def test_financial_summary_vente_settlement_not_charged_ship_maintenance(fake_uex, client):
    """Session expenses (frais d'entretien) are mining-ship costs the session creator
    fronted out of pocket (fuel, repairs) — they must not be deducted from the
    transporters' vente settlement (they'll get their own tool for that), but they
    DO need to come off the top of recap_global so that money gets reimbursed before
    the remaining pot is split among the crew."""
    fake_uex.get_session_financial_summary.return_value = {
        "session": {"id": 4, "star_system": "Stanton", "created_by": "Shepard40"},
        "crew": ["Shepard40", "Darkias"],
        "nb_joueurs": 2,
        "transport_crew": ["Nispi1"],
        "expenses": [{"description": "Carburant", "amount_auec": 1000}],
        "total_expenses": 1000,
        "orders_vente": [{"commodity_name": "Quantainium", "quantity": 100}],
        "orders_stock_fed": [],
        "orders_personnel": [],
    }
    fake_uex.get_commodities.return_value = [{"id": 5, "name": "Quantainium"}]
    fake_uex.get_prices_for_item.return_value = [
        {"price_sell": 50, "star_system_name": "Stanton"},
        {"price_sell": 999, "star_system_name": "Pyro"},
    ]

    resp = client.get("/raffineries/sessions/4/financial-summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["vente_settlement"] == {
        "payer": "Transporteurs",
        "recette": 5000,
        "part_federation": 1000,
        "part_transport": 750,
        "expenses": 0,
        "reste": 3250,
        "salaire_par_joueur": 1625,
        "lines": [
            {"commodity_name": "Quantainium", "quantity": 100, "price_per_scu": 50, "estimated_revenue": 5000}
        ],
    }
    assert body["personnel_settlement"] is None
    assert body["federal_settlement"] is None
    assert body["recap_global"] == {
        "recette_globale": 5000,
        "participation_federation": 1000,
        "part_transporteurs": 750,
        "cout_entretien": 1000,
        "cout_total_membres": 2250,
        "salaire_global_membre": 1125,
    }


def test_financial_summary_recap_global_sums_all_three_settlements(fake_uex, client):
    fake_uex.get_session_financial_summary.return_value = {
        "session": {"id": 4, "star_system": "Stanton", "created_by": "Shepard40"},
        "crew": ["Shepard40", "Darkias"],
        "nb_joueurs": 2,
        "transport_crew": ["Camus68"],
        "expenses": [],
        "total_expenses": 0,
        "orders_vente": [{"commodity_name": "Quantainium", "quantity": 100}],
        "orders_stock_fed": [{"commodity_name": "Quantainium", "quantity": 100}],
        "orders_personnel": [{"commodity_name": "Quantainium", "quantity": 100}],
    }
    fake_uex.get_commodities.return_value = [{"id": 5, "name": "Quantainium"}]
    fake_uex.get_prices_for_item.return_value = [{"price_sell": 50, "star_system_name": "Stanton"}]

    resp = client.get("/raffineries/sessions/4/financial-summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["recap_global"] == {
        "recette_globale": 15000,
        "participation_federation": 3000,
        "part_transporteurs": 2250,
        "cout_entretien": 0,
        "cout_total_membres": 9750,
        "salaire_global_membre": 4875,
    }


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
        "expenses": 0,
        "reste": 3250,
        "salaire_par_joueur": 1625,
        "lines": [
            {"commodity_name": "Quantainium", "quantity": 100, "price_per_scu": 50, "estimated_revenue": 5000}
        ],
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
        "expenses": 0,
        "reste": 4000,
        "salaire_par_joueur": 2000,
        "lines": [
            {"commodity_name": "Quantainium", "quantity": 100, "price_per_scu": 50, "estimated_revenue": 5000}
        ],
    }
    assert body["personnel_settlement"] is None


def test_financial_summary_404_when_session_missing(fake_uex, client):
    fake_uex.get_session_financial_summary.return_value = None

    resp = client.get("/raffineries/sessions/999/financial-summary")

    assert resp.status_code == 404


def test_financial_summary_forbidden_for_users_outside_allowlist(fake_uex, client_as):
    # Temporary: financial data is restricted to Shepard40 (Yann) and Darkias until
    # a proper role-based permission exists for it.
    other_user = {"sub": "9", "username": "Nispi1", "permissions": ["page_raffineries"]}
    fake_uex.get_session_financial_summary.return_value = {
        "session": {"id": 4, "star_system": "Stanton", "created_by": "Shepard40"},
        "crew": [], "nb_joueurs": 0, "transport_crew": [],
        "expenses": [], "total_expenses": 0,
        "orders_vente": [], "orders_stock_fed": [], "orders_personnel": [],
    }

    resp = client_as(other_user).get("/raffineries/sessions/4/financial-summary")

    assert resp.status_code == 403


def test_financial_summary_allowed_for_darkias(fake_uex, client_as):
    fake_uex.get_session_financial_summary.return_value = {
        "session": {"id": 4, "star_system": "Stanton", "created_by": "Shepard40"},
        "crew": [], "nb_joueurs": 0, "transport_crew": [],
        "expenses": [], "total_expenses": 0,
        "orders_vente": [], "orders_stock_fed": [], "orders_personnel": [],
    }

    resp = client_as(ADMIN_USER).get("/raffineries/sessions/4/financial-summary")

    assert resp.status_code == 200
