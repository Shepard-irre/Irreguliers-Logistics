from uex_library import UEXManager


def test_headers_include_browser_user_agent():
    mgr = UEXManager()
    assert "User-Agent" in mgr.headers
    assert "python-requests" not in mgr.headers["User-Agent"]
