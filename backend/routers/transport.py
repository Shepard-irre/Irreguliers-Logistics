import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from deps import get_uex, records_without_nan

router = APIRouter(prefix="/transport", tags=["transport"])


def require_transport_access(user: dict = Depends(get_current_user)) -> dict:
    permissions = user.get("permissions", [])
    if "page_transport" not in permissions and "admin_panel" not in permissions:
        raise HTTPException(status_code=403, detail="Permission refusée")
    return user


@router.get("/orders")
def list_orders(
    status: str,
    user: dict = Depends(require_transport_access),
    uex=Depends(get_uex),
):
    is_admin = "admin_panel" in user.get("permissions", [])
    df = uex.get_transport_orders(assignee=None if is_admin else user["username"], status=status)
    return records_without_nan(df)


def _assert_order_assigned_to(uex, user: dict, order_id: int) -> None:
    """Raise 404 unless order_id is currently assigned to the requester (admins exempt).

    Mirrors the app's original behaviour: a non-admin only ever sees their own
    assigned orders (list_orders scopes by assignee), so they could never click
    take/deliver on someone else's order. The API has no such built-in scoping,
    so it's enforced here. 404 (not 403) to avoid confirming another user's order
    exists.
    """
    if "admin_panel" in user.get("permissions", []):
        return
    orders = uex.get_transport_orders()
    match = orders[orders["id"] == order_id] if not orders.empty else orders
    if match.empty or match.iloc[0]["assigned_to"] != user["username"]:
        raise HTTPException(status_code=404, detail="Bon introuvable")


@router.post("/orders/{order_id}/take")
def take_order(
    order_id: int,
    user: dict = Depends(require_transport_access),
    uex=Depends(get_uex),
):
    _assert_order_assigned_to(uex, user, order_id)

    uex.update_transport_status(order_id, "in_progress", user["username"])
    return {"ok": True}


@router.post("/orders/{order_id}/deliver")
def deliver_order(
    order_id: int,
    user: dict = Depends(require_transport_access),
    uex=Depends(get_uex),
):
    _assert_order_assigned_to(uex, user, order_id)

    uex.update_transport_status(order_id, "delivered", user["username"])
    return {"ok": True}
