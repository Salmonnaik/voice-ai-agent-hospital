"""
scheduler/main.py

FastAPI scheduler service — slot management and booking.
"""
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .booking_engine import BookingEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scheduler Service")
engine = BookingEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "scheduler"}


class BookRequest(BaseModel):
    doctor_name: str | None = None
    patient_id: str
    preferred_time: str
    session_id: str


class ConfirmRequest(BaseModel):
    slot_id: str
    patient_id: str
    session_id: str


class CancelRequest(BaseModel):
    appointment_id: str
    patient_id: str


class SlotsQuery(BaseModel):
    doctor_name: str | None = None
    specialty: str | None = None
    after_time: str | None = None
    count: int = 3


@app.post("/slots/hold")
async def hold_slot(req: BookRequest):
    result = await engine.book_slot(
        doctor_name=req.doctor_name,
        patient_id=req.patient_id,
        preferred_time=req.preferred_time,
        session_id=req.session_id,
    )
    return {"status": result.status, "data": result.data}


@app.post("/slots/confirm")
async def confirm_booking(req: ConfirmRequest):
    result = await engine.confirm_booking(
        slot_id=req.slot_id,
        patient_id=req.patient_id,
        session_id=req.session_id,
    )
    return {"status": result.status, "data": result.data}


@app.post("/slots/cancel")
async def cancel_booking(req: CancelRequest):
    result = await engine.cancel(
        appointment_id=req.appointment_id,
        patient_id=req.patient_id,
    )
    return {"status": result.status, "data": result.data}


@app.post("/slots/available")
async def available_slots(req: SlotsQuery):
    result = await engine.get_available_slots(
        doctor_name=req.doctor_name,
        specialty=req.specialty,
        after_time=req.after_time,
        count=req.count,
    )
    return {"status": result.status, "data": result.data}
