import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_permission
from deps import get_uex, records_without_nan

router = APIRouter(prefix="/gestion-stock", tags=["gestion-stock"])

CAT_MAP = {
    "Moteurs Quantum (QT Drive)": [22, 86],
    "Boucliers (Shields)": [23],
    "Générateurs (Power Plants)": [21, 83],
    "Armement Vaisseaux": [32, 70, 79, 90],
    "Minage (Lasers & Modules)": [29, 30, 74],
    "Avionique & Radar": [82, 65],
}


@router.get("/categories")
def list_categories(
    user: dict = Depends(require_permission("page_gestion_stock")),
):
    return [{"label": label, "category_ids": ids} for label, ids in CAT_MAP.items()]


@router.get("/items")
def list_items(
    category_ids: str,
    user: dict = Depends(require_permission("page_gestion_stock")),
    uex=Depends(get_uex),
):
    items = []
    for cid in category_ids.split(","):
        items.extend(uex.get_items_by_category(int(cid)))
    return items


@router.get("/items/{item_id}/prices")
def item_prices(
    item_id: int,
    user: dict = Depends(require_permission("page_gestion_stock")),
    uex=Depends(get_uex),
):
    return uex.get_item_prices_by_id(item_id)


class AddStockIn(BaseModel):
    item_id: int
    name: str
    category: str
    size: str
    quantity: int


@router.post("/stock")
def add_to_stock(
    body: AddStockIn,
    user: dict = Depends(require_permission("page_gestion_stock")),
    uex=Depends(get_uex),
):
    uex.update_stock(user["username"], body.item_id, body.name, body.category, body.size, body.quantity)
    return {"ok": True}


@router.get("/inventory")
def inventory(
    user: dict = Depends(require_permission("page_gestion_stock")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_full_inventory(can_see_hidden=True))


class VisibilityIn(BaseModel):
    is_hidden: bool


@router.post("/items/{item_id}/visibility")
def set_visibility(
    item_id: int,
    body: VisibilityIn,
    user: dict = Depends(require_permission("page_gestion_stock")),
    uex=Depends(get_uex),
):
    uex.toggle_item_hidden(item_id, body.is_hidden)
    return {"ok": True}


@router.get("/logs")
def logs(
    user: dict = Depends(require_permission("page_gestion_stock")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_logs())
