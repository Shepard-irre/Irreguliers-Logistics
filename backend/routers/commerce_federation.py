import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_permission
from deps import get_uex

router = APIRouter(prefix="/commerce-federation", tags=["commerce-federation"])


@router.get("/fed-prices")
def fed_prices(
    user: dict = Depends(require_permission("page_commerce_federation")),
    uex=Depends(get_uex),
):
    commodities = uex.get_commodities()
    prices = uex.get_all_fed_prices()
    return [
        {"commodity_id": c["id"], "name": c["name"], "price_fed": prices.get(c["id"], 0.0)}
        for c in commodities
    ]


class SetFedPriceIn(BaseModel):
    commodity_id: int
    price: float


@router.post("/fed-prices")
def set_fed_price(
    body: SetFedPriceIn,
    user: dict = Depends(require_permission("page_commerce_federation")),
    uex=Depends(get_uex),
):
    uex.set_fed_price(body.commodity_id, body.price)
    return {"ok": True}


@router.get("/best-price")
def best_price(
    commodity_id: int,
    user: dict = Depends(require_permission("page_commerce_federation")),
    uex=Depends(get_uex),
):
    prices = uex.get_prices_for_item(commodity_id)
    buyers = [p for p in prices if p.get("price_sell", 0) > 0]
    best = max(buyers, key=lambda p: p["price_sell"]) if buyers else None
    return {"price_sell": best["price_sell"] if best else 0}
