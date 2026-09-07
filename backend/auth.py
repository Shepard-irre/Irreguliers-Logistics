import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from wp_auth import WPAuth

from security import create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)
_wp = WPAuth()


class LoginIn(BaseModel):
    username: str
    password: str


class SSOIn(BaseModel):
    token: str


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email", ""),
        "roles": user["roles"],
        "permissions": user["permissions"],
    }


@router.post("/login")
def login(body: LoginIn):
    user = _wp.authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    return {"access_token": create_access_token(user), "user": _public_user(user)}


@router.post("/sso")
def sso(body: SSOIn):
    user = _wp.authenticate_with_token(body.token)
    if not user:
        raise HTTPException(status_code=401, detail="Token SSO invalide")
    return {"access_token": create_access_token(user), "user": _public_user(user)}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Non authentifié")
    try:
        return decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


def require_permission(permission: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if permission not in user.get("permissions", []):
            raise HTTPException(status_code=403, detail="Permission refusée")
        return user

    return checker
