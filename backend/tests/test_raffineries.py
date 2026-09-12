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
from routers import raffineries

MINEUR_USER = {"sub": "12", "username": "Shepard40", "permissions": ["page_raffineries"]}
ADMIN_USER = {"sub": "1", "username": "Darkias", "permissions": ["page_raffineries", "admin_panel"]}

JOB_ROW = {
    "id": 7,
    "user": "Shepard40",
    "commodity_id": 101,
    "commodity_name": "Quantainium (Raw)",
    "terminal_name": "HDMS-Hadley (microTech)",
    "session_id": 3,
    "status": "pending",
}


@pytest.fixture
def fake_uex():
    return MagicMock()


@pytest.fixture
def app(fake_uex):
    app = FastAPI()
    app.include_router(raffineries.router)
    app.dependency_overrides[deps.get_uex] = lambda: fake_uex
    return app


@pytest.fixture
def client_as(app):
    def _client_as(user):
        app.dependency_overrides[auth.get_current_user] = lambda: user
        return TestClient(app)
    return _client_as


def test_list_jobs_scopes_to_own_username_for_non_admin(fake_uex, client_as):
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([JOB_ROW])
    client = client_as(MINEUR_USER)

    resp = client.get("/raffineries/jobs")

    assert resp.status_code == 200
    fake_uex.get_pending_refinery_jobs.assert_called_once_with(user="Shepard40")
    assert resp.json()[0]["commodity_name"] == "Quantainium (Raw)"


def test_list_jobs_handles_null_quantity_actual_on_a_real_pending_job(fake_uex, client_as):
    # A genuinely pending job always has quantity_actual/session_id/date_confirmed
    # NULL in SQLite — pandas surfaces that as NaN, which the default JSON
    # encoder rejects. This reproduces the real shape, not a synthetic None.
    pending_row = {**JOB_ROW, "quantity_actual": float("nan"), "session_id": float("nan")}
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([pending_row])
    client = client_as(MINEUR_USER)

    resp = client.get("/raffineries/jobs")

    assert resp.status_code == 200
    assert resp.json()[0]["quantity_actual"] is None
    assert resp.json()[0]["session_id"] is None


def test_list_jobs_sees_everyone_for_admin(fake_uex, client_as):
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([JOB_ROW])
    client = client_as(ADMIN_USER)

    resp = client.get("/raffineries/jobs")

    assert resp.status_code == 200
    fake_uex.get_pending_refinery_jobs.assert_called_once_with(user=None)


def test_confirm_job_personnel_destination_adds_personal_stock(fake_uex, client_as):
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([JOB_ROW])
    fake_uex.confirm_refinery_job.return_value = {
        "job": JOB_ROW,
        "lot_id": 55,
        "commodity_name": "Quantainium",
    }
    client = client_as(MINEUR_USER)

    resp = client.post(
        "/raffineries/jobs/7/confirm",
        json={
            "quantity_actual": 260,
            "quality": 910,
            "destination": "personnel",
            "personal_location": "Aspis Station",
        },
    )

    assert resp.status_code == 200
    fake_uex.confirm_refinery_job.assert_called_once_with(7, 260, 910)
    fake_uex.add_personal_stock.assert_called_once_with(
        owner="Shepard40",
        commodity_name="Quantainium",
        quantity=260,
        quality=910,
        refinery_job_id=7,
        location="Aspis Station",
    )
    fake_uex.create_transport_order.assert_not_called()


def test_confirm_job_vente_destination_creates_transport_order(fake_uex, client_as):
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([JOB_ROW])
    fake_uex.confirm_refinery_job.return_value = {
        "job": JOB_ROW,
        "lot_id": 55,
        "commodity_name": "Quantainium",
    }
    client = client_as(MINEUR_USER)

    resp = client.post(
        "/raffineries/jobs/7/confirm",
        json={"quantity_actual": 260, "quality": 910, "destination": "vente"},
    )

    assert resp.status_code == 200
    fake_uex.create_transport_order.assert_called_once_with(
        created_by="Shepard40",
        assigned_to="Camus68",
        commodity_name="Quantainium",
        quantity=260,
        quality=910,
        pickup_location="HDMS-Hadley",
        delivery_location="Marché (à définir)",
        refinery_job_id=7,
        lot_id=55,
        notes=None,
        session_id=3,
        destination="vente",
    )
    fake_uex.add_personal_stock.assert_not_called()


def test_confirm_job_stock_federal_uses_matching_delivery_location(fake_uex, client_as):
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([JOB_ROW])
    fake_uex.confirm_refinery_job.return_value = {
        "job": JOB_ROW,
        "lot_id": 55,
        "commodity_name": "Quantainium",
    }
    client = client_as(MINEUR_USER)

    resp = client.post(
        "/raffineries/jobs/7/confirm",
        json={"quantity_actual": 260, "quality": 910, "destination": "stock_federal"},
    )

    assert resp.status_code == 200
    assert fake_uex.create_transport_order.call_args.kwargs["delivery_location"] == "Stock Fédération"


def test_confirm_job_unknown_job_returns_404(fake_uex, client_as):
    fake_uex.confirm_refinery_job.return_value = None
    client = client_as(MINEUR_USER)

    resp = client.post(
        "/raffineries/jobs/999/confirm",
        json={"quantity_actual": 10, "quality": 500, "destination": "vente"},
    )

    assert resp.status_code == 404


def test_confirm_job_rejects_job_owned_by_someone_else(fake_uex, client_as):
    # job 7 belongs to Shepard40 in JOB_ROW — a different non-admin requester
    # must not be able to confirm it, even though the job genuinely exists.
    other_user = {"sub": "3", "username": "Darkias", "permissions": ["page_raffineries"]}
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([])  # Darkias has no jobs of their own
    client = client_as(other_user)

    resp = client.post(
        "/raffineries/jobs/7/confirm",
        json={"quantity_actual": 260, "quality": 910, "destination": "vente"},
    )

    assert resp.status_code == 404
    fake_uex.confirm_refinery_job.assert_not_called()


def test_cancel_job(fake_uex, client_as):
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([JOB_ROW])
    client = client_as(MINEUR_USER)

    resp = client.delete("/raffineries/jobs/7")

    assert resp.status_code == 200
    fake_uex.cancel_refinery_job.assert_called_once_with(7)


def test_cancel_job_rejects_job_owned_by_someone_else(fake_uex, client_as):
    other_user = {"sub": "3", "username": "Darkias", "permissions": ["page_raffineries"]}
    fake_uex.get_pending_refinery_jobs.return_value = pd.DataFrame([])
    client = client_as(other_user)

    resp = client.delete("/raffineries/jobs/7")

    assert resp.status_code == 404
    fake_uex.cancel_refinery_job.assert_not_called()


def test_reference_data_returns_commodities_terminals_methods_and_open_sessions(fake_uex, client_as):
    fake_uex.get_refinable_commodities.return_value = [{"id": 1, "name": "Quantainium (Raw)"}]
    fake_uex.get_refinery_terminals.return_value = [{"id": 10, "name": "HDMS-Hadley", "star_system_name": "Stanton"}]
    fake_uex.get_refinery_methods.return_value = [{"name": "Cormack", "rating_yield": 1}]
    fake_uex.get_mining_sessions.return_value = pd.DataFrame(
        [{"id": 3, "numero": "MIN003", "star_system": "Stanton", "status": "open"}]
    )
    client = client_as(MINEUR_USER)

    resp = client.get("/raffineries/reference-data")

    assert resp.status_code == 200
    fake_uex.get_mining_sessions.assert_called_once_with(status="open")
    body = resp.json()
    assert body["commodities"] == [{"id": 1, "name": "Quantainium (Raw)"}]
    assert body["terminals"] == [{"id": 10, "name": "HDMS-Hadley", "star_system_name": "Stanton"}]
    assert body["methods"] == [{"name": "Cormack", "rating_yield": 1}]
    assert body["sessions"] == [{"id": 3, "numero": "MIN003", "star_system": "Stanton", "status": "open"}]


def test_estimate_calls_uex_with_given_params_and_returns_its_result(fake_uex, client_as):
    fake_uex.calculate_refinery_estimate.return_value = {
        "estimated_output": 84.0,
        "yield_pct": 84.0,
        "base_yield_pct": 80.0,
        "terminal_modifier": 4,
        "confidence": "Moyenne",
        "audit_count": 5,
        "local_count": 0,
    }
    client = client_as(MINEUR_USER)

    resp = client.post(
        "/raffineries/estimate",
        json={"commodity_id": 1, "terminal_id": 10, "method_code": "cormack", "quantity": 100},
    )

    assert resp.status_code == 200
    fake_uex.calculate_refinery_estimate.assert_called_once_with(1, 10, "cormack", 100)
    assert resp.json()["estimated_output"] == 84.0


def test_create_job_calls_uex_with_requesters_username_and_given_fields(fake_uex, client_as):
    fake_uex.create_refinery_job.return_value = 42
    client = client_as(MINEUR_USER)

    resp = client.post(
        "/raffineries/jobs",
        json={
            "commodity_id": 1,
            "commodity_name": "Quantainium (Raw)",
            "terminal_id": 10,
            "terminal_name": "HDMS-Hadley (Stanton)",
            "method": "cormack",
            "quantity_raw": 100,
            "quantity_estimated": 84,
            "yield_rate": 84.0,
            "confidence": "Moyenne",
            "audit_count": 5,
            "quality": 700,
            "session_id": 3,
        },
    )

    assert resp.status_code == 200
    fake_uex.create_refinery_job.assert_called_once_with(
        "Shepard40",
        1,
        "Quantainium (Raw)",
        10,
        "HDMS-Hadley (Stanton)",
        "cormack",
        100,
        84,
        84.0,
        "Moyenne",
        5,
        session_id=3,
        quality=700,
        processing_time_minutes=None,
    )
    assert resp.json() == {"id": 42}


def test_list_lots_returns_all_lots_blocked_and_unblocked(fake_uex, client_as):
    fake_uex.get_commodity_lots.return_value = pd.DataFrame([
        {"id": 1, "Minerai": "Quantainium", "SCU": 10.0, "Qualité": 700, "Bloqué": 0, "Bloqué par": None},
        {"id": 2, "Minerai": "Agricium", "SCU": 5.0, "Qualité": 500, "Bloqué": 1, "Bloqué par": "Darkias"},
    ])
    client = client_as(MINEUR_USER)

    resp = client.get("/raffineries/lots")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_toggle_lot_blocked_requires_gestion_stock_permission(fake_uex, client_as):
    client = client_as(MINEUR_USER)

    resp = client.post("/raffineries/lots/1/toggle-block", json={"is_blocked": True})

    assert resp.status_code == 403
    fake_uex.toggle_lot_blocked.assert_not_called()


def test_toggle_lot_blocked_by_gestionnaire(fake_uex, client_as):
    gestionnaire = {"sub": "1", "username": "Darkias", "permissions": ["page_raffineries", "page_gestion_stock"]}
    client = client_as(gestionnaire)

    resp = client.post("/raffineries/lots/1/toggle-block", json={"is_blocked": True})

    assert resp.status_code == 200
    fake_uex.toggle_lot_blocked.assert_called_once_with(1, True, "Darkias")


def test_get_personal_stock_scopes_to_requester(fake_uex, client_as):
    fake_uex.get_personal_stock.return_value = pd.DataFrame(
        [{"id": 5, "commodity_name": "Quantainium", "quantity": 100.0, "quality": 700, "location": None}]
    )
    client = client_as(MINEUR_USER)

    resp = client.get("/raffineries/personal-stock")

    assert resp.status_code == 200
    fake_uex.get_personal_stock.assert_called_once_with("Shepard40")
    assert resp.json()[0]["location"] is None


def test_relocate_personal_stock(fake_uex, client_as):
    client = client_as(MINEUR_USER)

    resp = client.post("/raffineries/personal-stock/5/relocate", json={"location": "Aspis Station"})

    assert resp.status_code == 200
    fake_uex.update_personal_stock_location.assert_called_once_with(5, "Aspis Station")


def test_consume_personal_stock(fake_uex, client_as):
    client = client_as(MINEUR_USER)

    resp = client.post("/raffineries/personal-stock/5/consume", json={"reason": "Vendu"})

    assert resp.status_code == 200
    fake_uex.consume_personal_stock.assert_called_once_with(5, "Vendu")


def test_all_terminals(fake_uex, client_as):
    fake_uex.get_all_terminals.return_value = [{"id": 1, "name": "Area18", "star_system_name": "Stanton"}]
    client = client_as(MINEUR_USER)

    resp = client.get("/raffineries/all-terminals")

    assert resp.status_code == 200
    assert resp.json() == [{"id": 1, "name": "Area18", "star_system_name": "Stanton"}]


def test_analyze_screenshot_passes_image_bytes_and_returns_result(fake_uex, client_as):
    fake_uex.analyze_refinery_screenshot.return_value = {
        "screen_type": "B",
        "lines": [{"commodity_name": "Quantainium", "quality": 700}],
    }
    fake_uex.register_session_screenshot.return_value = False
    client = client_as(MINEUR_USER)
    image_bytes = b"\x89PNG\r\n\x1a\nfake-png-bytes"

    resp = client.post(
        "/raffineries/analyze-screenshot",
        data={"session_id": "4"},
        files={"screenshot": ("shot.png", image_bytes, "image/png")},
    )

    assert resp.status_code == 200
    fake_uex.analyze_refinery_screenshot.assert_called_once_with(image_bytes)
    fake_uex.register_session_screenshot.assert_called_once_with(4, "shot.png", "Shepard40")
    body = resp.json()
    assert body["screen_type"] == "B"
    assert body["duplicate_screenshot"] is False


def test_analyze_screenshot_flags_duplicate_filename_in_same_session(fake_uex, client_as):
    fake_uex.analyze_refinery_screenshot.return_value = {"screen_type": "B", "lines": []}
    fake_uex.register_session_screenshot.return_value = True
    client = client_as(MINEUR_USER)

    resp = client.post(
        "/raffineries/analyze-screenshot",
        data={"session_id": "4"},
        files={"screenshot": ("shot.png", b"fake", "image/png")},
    )

    assert resp.status_code == 200
    assert resp.json()["duplicate_screenshot"] is True
