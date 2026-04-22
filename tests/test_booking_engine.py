"""
tests/test_booking_engine.py

Unit tests for the booking engine conflict logic.
Uses an in-memory SQLite-compatible test setup.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.scheduler.booking_engine import BookingEngine
from backend.tool_dispatcher import ToolResult


@pytest.mark.asyncio
async def test_book_slot_success():
    """Happy path: free slot available, booking succeeds."""
    engine = BookingEngine()

    mock_slot = {
        "id": "slot-123",
        "doctor_name": "Dr. Ananya Sharma",
        "start_time": "2025-01-15T10:00:00+05:30",
        "end_time": "2025-01-15T10:15:00+05:30",
    }

    with patch.object(engine, "_get_pool") as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_slot
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_pool.return_value.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await engine.book_slot(
            doctor_name="Dr. Ananya",
            patient_id="patient-456",
            preferred_time="2025-01-15T10:00:00",
            session_id="session-789",
        )

    assert result.status == "held"
    assert result.data["doctor_name"] == "Dr. Ananya Sharma"


@pytest.mark.asyncio
async def test_book_slot_conflict():
    """When slot is taken, should return alternatives."""
    engine = BookingEngine()

    alternatives = [
        {"start_time": "2025-01-15T10:30:00", "doctor_name": "Dr. Ananya Sharma"},
        {"start_time": "2025-01-15T11:00:00", "doctor_name": "Dr. Ananya Sharma"},
    ]

    with patch.object(engine, "_get_pool") as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # slot not found
        mock_conn.fetch.return_value = alternatives
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_pool.return_value.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await engine.book_slot(
            doctor_name=None,
            patient_id="patient-456",
            preferred_time="2025-01-15T10:00:00",
            session_id="session-789",
        )

    assert result.status == "conflict"
    assert len(result.data["alternatives"]) == 2


@pytest.mark.asyncio
async def test_cancel_appointment():
    """Cancellation should free the slot."""
    engine = BookingEngine()

    with patch.object(engine, "_get_pool") as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"
        mock_pool.return_value.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await engine.cancel(
            appointment_id="slot-123",
            patient_id="patient-456",
        )

    assert result.status == "cancelled"
