import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from security import create_access_token, decode_access_token


def test_create_and_decode_access_token_roundtrip():
    user = {
        "id": 12,
        "username": "Shepard40",
        "email": "shepard40@example.com",
        "roles": [{"id": "um_custom_role_5", "name": "Mineur"}],
        "permissions": ["page_raffineries", "page_commerce"],
    }

    token = create_access_token(user)
    payload = decode_access_token(token)

    assert payload["sub"] == "12"
    assert payload["username"] == "Shepard40"
    assert payload["roles"] == ["um_custom_role_5"]
    assert payload["permissions"] == ["page_raffineries", "page_commerce"]
