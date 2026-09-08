import sqlite3

from uex_library import UEXManager


def _fresh_manager(tmp_path):
    mgr = UEXManager()
    mgr.db_path = str(tmp_path / "test.db")
    mgr.init_db()
    return mgr


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


def test_financial_summary_includes_personnel_orders_and_transport_crew(tmp_path):
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
        c.execute(
            "INSERT INTO transport_orders "
            "(id, created_by, commodity_name, quantity, quality, pickup_location, delivery_location, "
            "destination, status, session_id) "
            "VALUES (1, 'Shepard40', 'Quantainium', 100, 500, 'A', 'B', 'personnel', 'delivered', 1)"
        )
        conn.commit()

    summary = mgr.get_session_financial_summary(1)

    assert summary["orders_personnel"] == [
        {
            "id": 1,
            "commodity_name": "Quantainium",
            "quantity": 100.0,
            "quality": 500,
            "destination": "personnel",
            "status": "delivered",
            "lot_id": None,
            "commodity_id": None,
        }
    ]
    assert summary["transport_crew"] == ["Darkias"]
