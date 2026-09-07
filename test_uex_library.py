from uex_library import UEXManager


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
