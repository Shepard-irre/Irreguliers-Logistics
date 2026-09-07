import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt as pyjwt
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)

# Réutilise IRR_JWT_SECRET (déjà utilisé côté WP pour le SSO) sauf si un secret
# dédié à l'API est fourni — évite d'avoir un 3e secret à gérer dans les envs.
SECRET = os.getenv('APP_JWT_SECRET') or os.getenv('IRR_JWT_SECRET', '')
ALGORITHM = 'HS256'
EXPIRE_HOURS = 12

if not SECRET:
    raise RuntimeError(
        "APP_JWT_SECRET ou IRR_JWT_SECRET doit être défini dans .env pour signer les tokens API."
    )


def create_access_token(user: dict) -> str:
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "email": user.get("email", ""),
        "roles": [r["id"] for r in user.get("roles", [])],
        "permissions": user.get("permissions", []),
        "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS),
    }
    return pyjwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return pyjwt.decode(token, SECRET, algorithms=[ALGORITHM])
