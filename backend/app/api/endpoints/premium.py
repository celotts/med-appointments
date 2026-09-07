"""Premium features: Telemedicine, Prescriptions, Billing."""

from typing import Any

from dependencies import get_current_user, get_db
from dependencies_i18n import get_language, I18nResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from models.user import User as UserModel
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["Premium Features"])


# ============================================================================
# TELEMEDICINE
# ============================================================================


class TelemedicineSessionRequest(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int


@router.post(
    "/telemedicine/session",
    summary="Create a telemedicine session",
)
async def create_telemedicine_session(
    *,
    db: AsyncSession = Depends(get_db),
    request: TelemedicineSessionRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Creates a telemedicine session for a virtual appointment."""
    import uuid
    from datetime import datetime

    session_id = str(uuid.uuid4())[:8]
    join_url = f"https://meet.medappointments.com/session/{session_id}"

    return {
        "session_id": session_id,
        "appointment_id": request.appointment_id,
        "join_url": join_url,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "instructions": {
            "patient": f"Join the video consultation using: {join_url}",
            "doctor": f"Log in at: {join_url}",
        },
        "note": "In production, integrate with WebRTC or video service (Zoom, Daily, etc.)",
    }


@router.get(
    "/telemedicine/session/{session_id}",
    summary="Get telemedicine session status",
)
async def get_telemedicine_session(
    *,
    session_id: str,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns the status of a telemedicine session."""
    return {
        "session_id": session_id,
        "status": "active",
        "participants": 0,
        "duration_minutes": 0,
        "recording_enabled": False,
    }


# ============================================================================
# PRESCRIPTIONS
# ============================================================================


class PrescriptionItem(BaseModel):
    medication: str
    dosage: str
    frequency: str
    duration: str
    instructions: str = ""


class PrescriptionRequest(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    diagnosis: str
    medications: list[PrescriptionItem]
    observations: str = ""


@router.post(
    "/prescriptions",
    status_code=201,
    summary="Create a medical prescription",
)
async def create_prescription(
    *,
    db: AsyncSession = Depends(get_db),
    request: PrescriptionRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Creates a medical prescription for a patient."""
    i18n = I18nResponse(language)
    from datetime import datetime

    # Get patient and doctor info
    result_pat = await db.execute(
        text(
            """
            SELECT id, CONCAT(first_name, ' ', last_name) AS name, email
            FROM patients WHERE id = :id
            """
        ),
        {"id": request.patient_id},
    )
    patient = result_pat.mappings().first()

    result_med = await db.execute(
        text(
            """
            SELECT id, CONCAT(first_name, ' ', last_name) AS name, professional_license
            FROM doctors WHERE id = :id
            """
        ),
        {"id": request.doctor_id},
    )
    doctor = result_med.mappings().first()

    if not patient or not doctor:
        raise i18n.error("not_found", status_code=404)

    prescription_id = f"RX-{datetime.now().strftime('%Y%m%d')}-{request.appointment_id}"

    return {
        "prescription_id": prescription_id,
        "appointment_id": request.appointment_id,
        "patient": patient["name"],
        "doctor": doctor["name"],
        "doctor_license": doctor["professional_license"],
        "date": datetime.now().isoformat(),
        "diagnosis": request.diagnosis,
        "medications": [dict(m) for m in request.medications],
        "observations": request.observations,
        "pdf_url": f"/api/v1/prescriptions/{prescription_id}/pdf",
        "note": "In production, generate PDF with official formula.",
    }


@router.get(
    "/prescriptions/{prescription_id}",
    summary="Get prescription details",
)
async def get_prescription(
    *,
    prescription_id: str,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns prescription details."""
    return {
        "prescription_id": prescription_id,
        "status": "generated",
        "download_url": f"/api/v1/prescriptions/{prescription_id}/pdf",
    }


# ============================================================================
# BILLING
# ============================================================================


class BillingItem(BaseModel):
    concept: str
    quantity: int = 1
    unit_price: float


class BillingRequest(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    items: list[BillingItem]
    discount: float = 0
    payment_method: str = "cash"


@router.post(
    "/billing/invoice",
    status_code=201,
    summary="Generate an invoice",
)
async def generate_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    request: BillingRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Generates an invoice for medical services."""
    from datetime import datetime

    # Calculate totals
    subtotal = sum(item.quantity * item.unit_price for item in request.items)
    iva = subtotal * 0.16  # 16% IVA Mexico
    total = subtotal + iva - request.discount

    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{request.appointment_id}"

    return {
        "invoice_number": invoice_number,
        "appointment_id": request.appointment_id,
        "date": datetime.now().isoformat(),
        "items": [
            {
                "concept": item.concept,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.quantity * item.unit_price,
            }
            for item in request.items
        ],
        "subtotal": subtotal,
        "iva": iva,
        "discount": request.discount,
        "total": total,
        "payment_method": request.payment_method,
        "pdf_url": f"/api/v1/billing/invoice/{invoice_number}/pdf",
        "note": "In production, integrate with billing system (CFDI for Mexico).",
    }


@router.get(
    "/billing/invoice/{invoice_number}",
    summary="Get invoice details",
)
async def get_invoice(
    *,
    invoice_number: str,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns invoice details."""
    return {
        "invoice_number": invoice_number,
        "status": "generated",
        "download_url": f"/api/v1/billing/invoice/{invoice_number}/pdf",
    }


@router.get(
    "/billing/summary",
    summary="Get billing summary",
)
async def get_billing_summary(
    *,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns billing summary for the period."""
    i18n = I18nResponse(language)
    # This would connect to a billing table in production
    return {
        "period": i18n.get("last_days", days=days),
        "total_billed": 0,
        "total_collected": 0,
        "pending_collection": 0,
        "payment_methods": {
            "cash": 0,
            "card": 0,
            "insurance": 0,
        },
        "note": "Connect to billing table in production.",
    }
