import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_permission
from deps import get_uex, records_without_nan

router = APIRouter(prefix="/crafting", tags=["crafting"])


def _has_stock_view(user: dict) -> bool:
    return "crafting_stock_view" in user.get("permissions", [])


def _analyze_ingredients(uex, ingredients: list) -> dict:
    rows = []
    all_ok = True
    any_missing = False
    for ing in ingredients:
        name = ing.get("name", "")
        required = float(ing.get("quantity_scu", 0))
        min_q = int(ing.get("min_quality", 0) or 0)
        lots = uex.get_lots_for_ingredient(name)

        if not lots.empty:
            mask_qual = (lots["Qualité"] >= min_q) if min_q > 0 else True
            available_ok = float(lots[(lots["Bloqué"] == 0) & mask_qual]["SCU"].sum())
            available_total = float(lots[lots["Bloqué"] == 0]["SCU"].sum())
        else:
            available_ok = 0.0
            available_total = 0.0

        if available_ok >= required:
            status = "ok"
        elif available_total > 0:
            status = "insufficient_quality"
        else:
            status = "missing"
            any_missing = True

        if available_ok < required:
            all_ok = False

        rows.append({
            "slot": ing.get("slot", "—"),
            "name": name,
            "required": required,
            "min_quality": min_q if min_q > 0 else None,
            "available_ok": available_ok,
            "available_total": available_total,
            "status": status,
        })

    badge = "ok" if all_ok else ("missing" if any_missing else "partial")
    return {"stock_badge": badge, "rows": rows}


@router.get("/blueprints")
def search_blueprints(
    search: str = "",
    limit: int = 20,
    user: dict = Depends(require_permission("page_crafting")),
    uex=Depends(get_uex),
):
    data = uex.get_blueprints_from_api(search=search, limit=limit)
    can_see_stock = _has_stock_view(user)

    for bp in data.get("items", []):
        bp["stock_analysis"] = (
            _analyze_ingredients(uex, bp.get("ingredients", [])) if can_see_stock else None
        )
    return data


@router.get("/lots-for-ingredient")
def lots_for_ingredient(
    name: str,
    user: dict = Depends(require_permission("page_crafting")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_lots_for_ingredient(name))


class ToggleBlockIn(BaseModel):
    is_blocked: bool


@router.post("/lots/{lot_id}/toggle-block")
def toggle_lot_blocked(
    lot_id: int,
    body: ToggleBlockIn,
    user: dict = Depends(require_permission("page_crafting")),
    uex=Depends(get_uex),
):
    if not _has_stock_view(user) and "admin_panel" not in user.get("permissions", []):
        raise HTTPException(status_code=403, detail="Permission refusée")
    uex.toggle_lot_blocked(lot_id, body.is_blocked, user["username"])
    return {"ok": True}


@router.get("/blocked-lots")
def blocked_lots(
    user: dict = Depends(require_permission("page_crafting")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_blocked_lots())
