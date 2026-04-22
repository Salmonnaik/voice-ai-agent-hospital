"""
orchestrator/tool_dispatcher.py

Maps intent labels to async tool functions.
Each tool function calls the scheduler-service via gRPC.
"""
import logging
from dataclasses import dataclass
from typing import Any

import grpc

from scheduler.booking_engine import BookingEngine

logger = logging.getLogger(__name__)

booking_engine = BookingEngine()


@dataclass
class ToolResult:
    status: str   # booked | conflict | slots_listed | cancelled | rescheduled | error
    data: dict


async def tool_book(entities: dict, patient_id: str, session_id: str) -> ToolResult:
    """Book an appointment slot."""
    doctor_name = entities.get("doctor_name")
    preferred_time = entities.get("preferred_time")

    if not preferred_time:
        return ToolResult(
            status="error",
            data={"error": "preferred_time entity missing from intent"},
        )

    try:
        result = await booking_engine.book_slot(
            doctor_name=doctor_name,
            patient_id=patient_id,
            preferred_time=preferred_time,
            session_id=session_id,
        )
        return result
    except Exception as e:
        logger.error("book_slot failed: %s", e)
        return ToolResult(status="error", data={"error": str(e)})


async def tool_reschedule(entities: dict, patient_id: str, session_id: str) -> ToolResult:
    """Reschedule an existing appointment."""
    appointment_id = entities.get("appointment_id")
    preferred_time = entities.get("preferred_time")

    if not appointment_id or not preferred_time:
        return ToolResult(
            status="error",
            data={"error": "appointment_id or preferred_time missing"},
        )

    try:
        result = await booking_engine.reschedule(
            appointment_id=appointment_id,
            patient_id=patient_id,
            new_time=preferred_time,
            session_id=session_id,
        )
        return result
    except Exception as e:
        logger.error("reschedule failed: %s", e)
        return ToolResult(status="error", data={"error": str(e)})


async def tool_cancel(entities: dict, patient_id: str, session_id: str) -> ToolResult:
    """Cancel an appointment."""
    appointment_id = entities.get("appointment_id")

    if not appointment_id:
        return ToolResult(
            status="error",
            data={"error": "appointment_id missing"},
        )

    try:
        result = await booking_engine.cancel(
            appointment_id=appointment_id,
            patient_id=patient_id,
        )
        return result
    except Exception as e:
        logger.error("cancel failed: %s", e)
        return ToolResult(status="error", data={"error": str(e)})


async def tool_check_slots(entities: dict, patient_id: str, session_id: str) -> ToolResult:
    """Check available appointment slots."""
    doctor_name = entities.get("doctor_name")
    specialty = entities.get("specialty")
    preferred_time = entities.get("preferred_time")

    try:
        result = await booking_engine.get_available_slots(
            doctor_name=doctor_name,
            specialty=specialty,
            after_time=preferred_time,
            count=3,
        )
        return result
    except Exception as e:
        logger.error("check_slots failed: %s", e)
        return ToolResult(status="error", data={"error": str(e)})


# Intent label → async tool function
TOOL_MAP: dict[str, Any] = {
    "book": tool_book,
    "reschedule": tool_reschedule,
    "cancel": tool_cancel,
    "check_slots": tool_check_slots,
}
