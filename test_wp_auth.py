from unittest.mock import MagicMock, patch

from wp_auth import WPAuth


def test_get_members_calls_irr_members_endpoint_with_api_key(monkeypatch):
    monkeypatch.setenv("IRR_JWT_SECRET", "shared-secret")
    wp = WPAuth(wp_url="https://lesirreguliers.fr")

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = [
        {"username": "Shepard40", "display_name": "Shepard40"},
        {"username": "Darkias", "display_name": "Darkias"},
    ]
    with patch("requests.get", return_value=fake_resp) as mock_get:
        members = wp.get_members()

    mock_get.assert_called_once_with(
        "https://lesirreguliers.fr/wp-json/irr/v1/members",
        headers={"X-Irr-Api-Key": "shared-secret"},
        timeout=10,
    )
    assert members == [
        {"username": "Shepard40", "display_name": "Shepard40"},
        {"username": "Darkias", "display_name": "Darkias"},
    ]


def test_get_members_returns_empty_list_on_error(monkeypatch):
    monkeypatch.setenv("IRR_JWT_SECRET", "shared-secret")
    wp = WPAuth(wp_url="https://lesirreguliers.fr")

    fake_resp = MagicMock()
    fake_resp.status_code = 403
    with patch("requests.get", return_value=fake_resp):
        members = wp.get_members()

    assert members == []
