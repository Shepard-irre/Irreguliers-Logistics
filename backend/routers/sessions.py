import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_permission
from deps import get_uex, records_without_nan

router = APIRouter(prefix="/raffineries/sessions", tags=["sessions"])


class CreateSessionIn(BaseModel):
    star_system: str


class AddShipIn(BaseModel):
    ship_name: str
    ship_role: str = "mining"


class AddCrewIn(BaseModel):
    username: str


class AddExpenseIn(BaseModel):
    description: str
    amount_auec: float


def _clean_commodity_key(name: str) -> str:
    return name.lower().replace(" (ore)", "").replace(" (raw)", "").strip()


def _estimate_revenue(orders, comm_name_map, system_name, uex):
    total = 0
    lines = []
    for order in orders:
        name_clean = _clean_commodity_key(order["commodity_name"])
        comm_id = comm_name_map.get(name_clean)
        best_price = 0
        if comm_id:
            prices = uex.get_prices_for_item(int(comm_id))
            buyers_sys = [
                p for p in prices
                if p.get("price_sell", 0) > 0 and p.get("star_system_name") == system_name
            ]
            if not buyers_sys:
                buyers_sys = [p for p in prices if p.get("price_sell", 0) > 0]
            best_price = max((p["price_sell"] for p in buyers_sys), default=0)
        rev = best_price * order["quantity"]
        total += rev
        lines.append({
            "commodity_name": order["commodity_name"],
            "quantity": order["quantity"],
            "price_per_scu": best_price,
            "estimated_revenue": rev,
        })
    return total, lines


def _settlement(orders, payer, nb_crew, transport_participates, comm_name_map, system_name, uex, expenses=0):
    if not orders:
        return None
    recette, lines = _estimate_revenue(orders, comm_name_map, system_name, uex)
    part_fed = recette * 0.20
    part_transport = recette * 0.15 if transport_participates else 0
    reste = recette - part_fed - part_transport - expenses
    return {
        "payer": payer,
        "recette": recette,
        "part_federation": part_fed,
        "part_transport": part_transport,
        "expenses": expenses,
        "reste": reste,
        "salaire_par_joueur": reste / nb_crew if nb_crew > 0 else 0,
        "lines": lines,
    }


@router.get("")
def list_sessions(
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_mining_sessions())


@router.get("/{session_id}")
def get_session(
    session_id: int,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    session = uex.get_mining_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return session


@router.post("")
def create_session(
    body: CreateSessionIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    return uex.create_mining_session(user["username"], body.star_system)


@router.post("/{session_id}/close")
def close_session(
    session_id: int,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    uex.set_session_status(session_id, "completed")
    return {"ok": True}


@router.post("/{session_id}/ships")
def add_ship(
    session_id: int,
    body: AddShipIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    ship_id = uex.add_session_ship(session_id, body.ship_name, body.ship_role)
    return {"id": ship_id}


@router.delete("/ships/{ship_id}")
def remove_ship(
    ship_id: int,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    uex.remove_session_ship(ship_id)
    return {"ok": True}


@router.post("/ships/{ship_id}/crew")
def add_crew_member(
    ship_id: int,
    body: AddCrewIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    uex.add_crew_member(ship_id, body.username)
    return {"ok": True}


@router.delete("/crew/{crew_id}")
def remove_crew_member(
    crew_id: int,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    uex.remove_crew_member(crew_id)
    return {"ok": True}


@router.post("/{session_id}/expenses")
def add_expense(
    session_id: int,
    body: AddExpenseIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    expense_id = uex.add_session_expense(session_id, body.description, body.amount_auec)
    return {"id": expense_id}


@router.delete("/expenses/{expense_id}")
def remove_expense(
    expense_id: int,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    uex.remove_session_expense(expense_id)
    return {"ok": True}


@router.get("/{session_id}/financial-summary")
def financial_summary(
    session_id: int,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    summary = uex.get_session_financial_summary(session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Session introuvable")

    all_comms = uex.get_commodities() or []
    comm_name_map = {}
    for c in all_comms:
        name = c.get("name", "")
        name_lower = name.lower()
        clean = _clean_commodity_key(name)
        if clean == name_lower:
            comm_name_map[clean] = c.get("id")
        elif clean not in comm_name_map:
            comm_name_map[clean] = c.get("id")

    system_name = summary["session"]["star_system"]
    total_exp = summary["total_expenses"]
    nb = summary["nb_joueurs"]
    transport_participates = bool(summary.get("transport_crew"))

    vente_settlement = _settlement(
        summary["orders_vente"], "Transporteurs",
        nb, transport_participates, comm_name_map, system_name, uex,
    )
    personnel_settlement = _settlement(
        summary.get("orders_personnel", []), summary["session"].get("created_by"),
        nb, transport_participates, comm_name_map, system_name, uex,
    )
    federal_settlement = _settlement(
        summary["orders_stock_fed"], "Fédération",
        nb, transport_participates, comm_name_map, system_name, uex,
    )

    settlements = [s for s in (vente_settlement, personnel_settlement, federal_settlement) if s]
    # Les frais de session (carburant, réparations) sont avancés par le créateur de la
    # session — ils doivent être remboursés sur la recette globale avant le partage entre
    # membres, pas déduits d'un règlement individuel (sinon il les paierait deux fois).
    cout_total_membres = sum(s["reste"] for s in settlements) - total_exp
    recap_global = {
        "recette_globale": sum(s["recette"] for s in settlements),
        "participation_federation": sum(s["part_federation"] for s in settlements),
        "part_transporteurs": sum(s["part_transport"] for s in settlements),
        "cout_entretien": total_exp,
        "cout_total_membres": cout_total_membres,
        "salaire_global_membre": cout_total_membres / nb if nb > 0 else 0,
    }

    return {
        "total_expenses": total_exp,
        "nb_joueurs": nb,
        "crew": summary["crew"],
        "has_orders": bool(summary["orders_vente"] or summary["orders_stock_fed"] or summary.get("orders_personnel")),
        "vente_settlement": vente_settlement,
        "personnel_settlement": personnel_settlement,
        "federal_settlement": federal_settlement,
        "recap_global": recap_global,
    }
