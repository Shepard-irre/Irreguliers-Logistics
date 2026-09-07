import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends

from auth import require_permission
from deps import get_uex

router = APIRouter(prefix="/commerce", tags=["commerce"])


@router.get("/commodities")
def list_commodities(
    user: dict = Depends(require_permission("page_commerce")),
    uex=Depends(get_uex),
):
    return uex.get_commodities()


@router.get("/prices")
def prices(
    commodity_id: int,
    user: dict = Depends(require_permission("page_commerce")),
    uex=Depends(get_uex),
):
    all_prices = uex.get_prices_for_item(commodity_id)
    return [p for p in all_prices if p.get("price_sell", 0) > 0]
