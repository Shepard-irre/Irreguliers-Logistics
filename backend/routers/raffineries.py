import sys
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel

from auth import require_permission
from deps import get_uex, records_without_nan

router = APIRouter(prefix="/raffineries", tags=["raffineries"])

_DELIVERY_LOCATIONS = {
    "vente": "Marché (à définir)",
    "stock_federal": "Stock Fédération",
    "personnel": "Personnel",
}


class ConfirmJobIn(BaseModel):
    quantity_actual: float
    quality: int
    destination: Literal["vente", "stock_federal", "personnel"]
    pickup_location: Optional[str] = None
    personal_location: Optional[str] = None
    notes: Optional[str] = None


def _assert_owns_pending_job(uex, user: dict, job_id: int) -> None:
    """Raise 404 unless job_id is one of the requester's own pending jobs (admins exempt).

    404 rather than 403 on purpose: a non-owner gets the same response whether
    the job doesn't exist or just isn't theirs, so this endpoint can't be used
    to enumerate other users' job ids.
    """
    if "admin_panel" in user.get("permissions", []):
        return
    own_jobs = uex.get_pending_refinery_jobs(user=user["username"])
    if own_jobs.empty or job_id not in own_jobs["id"].values:
        raise HTTPException(status_code=404, detail="Job introuvable")


@router.get("/reference-data")
def reference_data(
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    sessions_df = uex.get_mining_sessions(status="open")
    return {
        "commodities": uex.get_refinable_commodities(),
        "terminals": uex.get_refinery_terminals(),
        "methods": uex.get_refinery_methods(),
        "sessions": records_without_nan(sessions_df),
    }


class EstimateIn(BaseModel):
    commodity_id: int
    terminal_id: int
    method_code: str
    quantity: float


@router.post("/estimate")
def estimate(
    body: EstimateIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    return uex.calculate_refinery_estimate(
        body.commodity_id, body.terminal_id, body.method_code, body.quantity
    )


class CreateJobIn(BaseModel):
    commodity_id: int
    commodity_name: str
    terminal_id: int
    terminal_name: str
    method: str
    quantity_raw: float
    quantity_estimated: float
    yield_rate: float
    confidence: str
    audit_count: int
    quality: int = 500
    session_id: Optional[int] = None
    processing_time_minutes: Optional[int] = None


@router.post("/jobs")
def create_job(
    body: CreateJobIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    job_id = uex.create_refinery_job(
        user["username"],
        body.commodity_id,
        body.commodity_name,
        body.terminal_id,
        body.terminal_name,
        body.method,
        body.quantity_raw,
        body.quantity_estimated,
        body.yield_rate,
        body.confidence,
        body.audit_count,
        session_id=body.session_id,
        quality=body.quality,
        processing_time_minutes=body.processing_time_minutes,
    )
    return {"id": job_id}


@router.get("/jobs")
def list_jobs(
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    is_admin = "admin_panel" in user.get("permissions", [])
    df = uex.get_pending_refinery_jobs(user=None if is_admin else user["username"])
    return records_without_nan(df)


@router.post("/jobs/{job_id}/confirm")
def confirm_job(
    job_id: int,
    body: ConfirmJobIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    _assert_owns_pending_job(uex, user, job_id)

    result = uex.confirm_refinery_job(job_id, body.quantity_actual, body.quality)
    if not result:
        raise HTTPException(status_code=404, detail="Job introuvable")

    job = result["job"]
    commodity_name = result["commodity_name"]

    if body.destination == "personnel":
        uex.add_personal_stock(
            owner=user["username"],
            commodity_name=commodity_name,
            quantity=body.quantity_actual,
            quality=body.quality,
            refinery_job_id=job_id,
            location=body.personal_location,
        )
    else:
        default_pickup = job["terminal_name"].split(" (")[0]
        session_id = job.get("session_id")
        uex.create_transport_order(
            created_by=user["username"],
            assigned_to="Camus68",
            commodity_name=commodity_name,
            quantity=body.quantity_actual,
            quality=body.quality,
            pickup_location=body.pickup_location or default_pickup,
            delivery_location=_DELIVERY_LOCATIONS[body.destination],
            refinery_job_id=job_id,
            lot_id=result["lot_id"],
            notes=body.notes,
            session_id=session_id,
            destination=body.destination,
        )

    return {"ok": True, "destination": body.destination}


@router.delete("/jobs/{job_id}")
def cancel_job(
    job_id: int,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    _assert_owns_pending_job(uex, user, job_id)

    uex.cancel_refinery_job(job_id)
    return {"ok": True}


@router.get("/lots")
def list_lots(
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_commodity_lots())


class ToggleLotBlockIn(BaseModel):
    is_blocked: bool


@router.post("/lots/{lot_id}/toggle-block")
def toggle_lot_blocked(
    lot_id: int,
    body: ToggleLotBlockIn,
    user: dict = Depends(require_permission("page_gestion_stock")),
    uex=Depends(get_uex),
):
    uex.toggle_lot_blocked(lot_id, body.is_blocked, user["username"])
    return {"ok": True}


@router.get("/personal-stock")
def get_personal_stock(
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    return records_without_nan(uex.get_personal_stock(user["username"]))


class RelocatePersonalStockIn(BaseModel):
    location: str


@router.post("/personal-stock/{stock_id}/relocate")
def relocate_personal_stock(
    stock_id: int,
    body: RelocatePersonalStockIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    uex.update_personal_stock_location(stock_id, body.location)
    return {"ok": True}


class ConsumePersonalStockIn(BaseModel):
    reason: str


@router.post("/personal-stock/{stock_id}/consume")
def consume_personal_stock(
    stock_id: int,
    body: ConsumePersonalStockIn,
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    uex.consume_personal_stock(stock_id, body.reason)
    return {"ok": True}


@router.get("/all-terminals")
def all_terminals(
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    return uex.get_all_terminals()


@router.post("/analyze-screenshot")
async def analyze_screenshot(
    screenshot: UploadFile,
    session_id: int = Form(...),
    user: dict = Depends(require_permission("page_raffineries")),
    uex=Depends(get_uex),
):
    image_bytes = await screenshot.read()
    result = uex.analyze_refinery_screenshot(image_bytes)
    result["duplicate_screenshot"] = uex.register_session_screenshot(
        session_id, screenshot.filename, user["username"]
    )
    return result
