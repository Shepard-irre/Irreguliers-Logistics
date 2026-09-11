import sqlite3
from unittest.mock import MagicMock

from uex_library import UEXManager


def _fresh_manager(tmp_path):
    mgr = UEXManager()
    mgr.db_path = str(tmp_path / "test.db")
    mgr.init_db()
    return mgr


def test_get_mining_sessions_filtered_by_participant_sees_own_and_crewed_sessions(tmp_path):
    mgr = _fresh_manager(tmp_path)
    with sqlite3.connect(mgr.db_path) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO mining_sessions (id, numero, star_system, status, created_by) "
            "VALUES (1, 'MIN001', 'Stanton', 'open', 'Shepard40')"
        )
        c.execute(
            "INSERT INTO mining_sessions (id, numero, star_system, status, created_by) "
            "VALUES (2, 'MIN002', 'Pyro', 'open', 'Camus68')"
        )
        c.execute(
            "INSERT INTO mining_sessions (id, numero, star_system, status, created_by) "
            "VALUES (3, 'MIN003', 'Nyx', 'open', 'Camus68')"
        )
        c.execute("INSERT INTO session_ships (id, session_id, ship_name, ship_role) VALUES (1, 2, 'Prospector', 'mining')")
        c.execute("INSERT INTO session_crew (ship_id, username) VALUES (1, 'Darkias')")
        conn.commit()

    sessions = mgr.get_mining_sessions(participant='Darkias')

    assert sorted(s['numero'] for s in sessions.to_dict('records')) == ['MIN002']


def test_get_wp_members_delegates_to_wp_auth(monkeypatch):
    import uex_library
    fake_wp_auth = MagicMock()
    fake_wp_auth.get_members.return_value = [{"username": "Darkias", "display_name": "Darkias"}]
    monkeypatch.setattr(uex_library, "_wp_auth", fake_wp_auth)

    mgr = UEXManager()

    assert mgr.get_wp_members() == [{"username": "Darkias", "display_name": "Darkias"}]


def test_get_wp_members_returns_empty_list_without_wp_auth(monkeypatch):
    import uex_library
    monkeypatch.setattr(uex_library, "_wp_auth", None)

    mgr = UEXManager()

    assert mgr.get_wp_members() == []


def test_headers_include_browser_user_agent():
    mgr = UEXManager()
    assert "User-Agent" in mgr.headers
    assert "python-requests" not in mgr.headers["User-Agent"]


def test_headers_read_token_from_process_env_without_env_file(monkeypatch):
    monkeypatch.setenv("UEX_BEARER_TOKEN", "token-from-process-env")
    monkeypatch.setenv("UEX_SECRET_KEY", "secret-from-process-env")
    mgr = UEXManager()
    assert mgr.headers["Authorization"] == "Bearer token-from-process-env"
    assert mgr.headers["secret-key"] == "secret-from-process-env"


def test_financial_summary_includes_personal_stock_from_this_session_and_transport_crew(tmp_path):
    mgr = _fresh_manager(tmp_path)
    with sqlite3.connect(mgr.db_path) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO mining_sessions (id, numero, star_system, status, created_by) "
            "VALUES (1, 'MIN001', 'Stanton', 'open', 'Shepard40')"
        )
        c.execute("INSERT INTO session_ships (id, session_id, ship_name, ship_role) VALUES (1, 1, 'Prospector', 'mining')")
        c.execute("INSERT INTO session_ships (id, session_id, ship_name, ship_role) VALUES (2, 1, 'Cutlass', 'transport')")
        c.execute("INSERT INTO session_crew (ship_id, username) VALUES (1, 'Shepard40')")
        c.execute("INSERT INTO session_crew (ship_id, username) VALUES (2, 'Darkias')")
        # Confirming a job to "personnel" writes to personal_stock, not transport_orders
        # (confirm_job only creates a transport_order for vente/stock_federal).
        c.execute(
            "INSERT INTO refinery_jobs "
            "(id, user, commodity_id, commodity_name, terminal_id, terminal_name, method, "
            "quantity_raw, quantity_estimated, yield_rate, status, session_id) "
            "VALUES (1, 'Shepard40', 5, 'Quantainium', 1, 'HDMS-Hadley', 'cormack', "
            "100, 100, 100, 'confirmed', 1)"
        )
        c.execute(
            "INSERT INTO personal_stock (owner, commodity_name, quantity, quality, refinery_job_id, status) "
            "VALUES ('Shepard40', 'Quantainium', 100, 500, 1, 'active')"
        )
        # A refinery job from a DIFFERENT session must not leak into this one's settlement.
        c.execute(
            "INSERT INTO refinery_jobs "
            "(id, user, commodity_id, commodity_name, terminal_id, terminal_name, method, "
            "quantity_raw, quantity_estimated, yield_rate, status, session_id) "
            "VALUES (2, 'Shepard40', 5, 'Agricium', 1, 'HDMS-Hadley', 'cormack', "
            "50, 50, 100, 'confirmed', 2)"
        )
        c.execute(
            "INSERT INTO personal_stock (owner, commodity_name, quantity, quality, refinery_job_id, status) "
            "VALUES ('Shepard40', 'Agricium', 50, 500, 2, 'active')"
        )
        conn.commit()

    summary = mgr.get_session_financial_summary(1)

    assert summary["orders_personnel"] == [
        {"commodity_name": "Quantainium", "quantity": 100.0, "quality": 500}
    ]
    assert summary["transport_crew"] == ["Darkias"]
