import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends

from auth import require_permission
from deps import get_uex, records_without_nan

router = APIRouter(prefix="/stock-federation", tags=["stock-federation"])


def _can_see_hidden(user: dict) -> bool:
    return "page_gestion_stock" in user.get("permissions", [])


@router.get("/summary")
def summary(
    user: dict = Depends(require_permission("page_stock_federation")),
    uex=Depends(get_uex),
):
    inventory_df = uex.get_full_inventory(can_see_hidden=True)
    total_components = int(inventory_df["Qté"].sum()) if not inventory_df.empty else 0

    lots_df = uex.get_commodity_lots()
    total_minerals = (
        round(lots_df[lots_df["Bloqué"] == 0]["SCU"].sum(), 1) if not lots_df.empty else 0
    )

    wallet = uex.get_wallet()
    return {
        "total_components": total_components,
        "total_minerals": total_minerals,
        "fed_balance": wallet.get("balance", 0),
    }


@router.get("/inventory")
def inventory(
    user: dict = Depends(require_permission("page_stock_federation")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_full_inventory(can_see_hidden=_can_see_hidden(user)))


@router.get("/lots")
def lots(
    user: dict = Depends(require_permission("page_stock_federation")),
    uex=Depends(get_uex),
):
    lots_df = uex.get_commodity_lots()
    if lots_df.empty:
        return []
    return records_without_nan(lots_df[lots_df["Bloqué"] == 0])


@router.get("/logs")
def logs(
    user: dict = Depends(require_permission("page_stock_federation")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_logs())
