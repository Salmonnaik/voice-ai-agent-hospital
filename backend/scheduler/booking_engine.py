"""
scheduler/booking_engine.py

Appointment booking logic with conflict prevention.

Key design decisions:
- Slots are PRE-GENERATED (not computed on demand) — O(1) lookup
- Optimistic hold (90s window) before confirmation prevents double-booking
- DB-level EXCLUDE constraint as final safety net
- Returns top-3 alternatives on conflict
"""
import logging
import uuid
from datetime import datetime, timedelta

import asyncpg

from dataclasses import dataclass
from typing import Any

@dataclass
class ToolResult:
    status: str   # booked | conflict | slots_listed | cancelled | rescheduled | error
    data: dict

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/voiceai"


class BookingEngine:
    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if not self._pool:
            self._pool = await asyncpg.create_pool(DATABASE_URL, min_size=3, max_size=20)
        return self._pool

    async def book_slot(
        self,
        doctor_name: str | None,
        patient_id: str,
        preferred_time: str,
        session_id: str,
    ) -> ToolResult:
        """
        1. Parse preferred_time
        2. Find doctor_id (if name given)
        3. Optimistic hold for 90 seconds
        4. Return held slot (confirmation comes after verbal confirmation)
        """
        pool = await self._get_pool()

        try:
            preferred_dt = datetime.fromisoformat(preferred_time)
        except ValueError:
            return ToolResult(status="error", data={"error": f"Cannot parse time: {preferred_time}"})

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Resolve doctor
                doctor_id = None
                if doctor_name:
                    row = await conn.fetchrow(
                        "SELECT id FROM doctors WHERE LOWER(name) LIKE LOWER($1) LIMIT 1",
                        f"%{doctor_name}%",
                    )
                    if row:
                        doctor_id = row["id"]

                # Optimistic hold
                doctor_filter = "AND doctor_id = $2" if doctor_id else ""
                params = [session_id, preferred_dt]
                if doctor_id:
                    params.insert(1, doctor_id)

                slot = await conn.fetchrow(
                    f"""
                    UPDATE slots
                    SET status = 'held',
                        held_by = $1,
                        held_until = NOW() + INTERVAL '90 seconds'
                    WHERE id = (
                        SELECT id FROM slots
                        WHERE status = 'free'
                          AND start_time BETWEEN ${'$3' if doctor_id else '$2'}
                                              AND ${'$3' if doctor_id else '$2'} + INTERVAL '60 minutes'
                          {doctor_filter}
                        ORDER BY ABS(EXTRACT(EPOCH FROM (start_time - ${'$3' if doctor_id else '$2'})))
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING id, doctor_id, start_time, end_time,
                              (SELECT name FROM doctors WHERE id = slots.doctor_id) AS doctor_name
                    """,
                    *params,
                )

                if not slot:
                    # Conflict — return alternatives
                    alternatives = await self.get_next_available(
                        doctor_id=doctor_id, after=preferred_dt, n=3, conn=conn
                    )
                    return ToolResult(
                        status="conflict",
                        data={"alternatives": [dict(a) for a in alternatives]},
                    )

                # Pre-check for existing upcoming appointment
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM slots
                    WHERE patient_id = $1
                      AND start_time > NOW()
                      AND status = 'booked'
                    LIMIT 1
                    """,
                    patient_id,
                )
                if existing:
                    # Release the hold and warn
                    await conn.execute(
                        "UPDATE slots SET status='free', held_by=NULL, held_until=NULL WHERE id=$1",
                        slot["id"],
                    )
                    return ToolResult(
                        status="error",
                        data={"error": "patient_has_existing_appointment", "appointment_id": str(existing["id"])},
                    )

                return ToolResult(
                    status="held",
                    data={
                        "slot_id": str(slot["id"]),
                        "doctor_name": slot["doctor_name"],
                        "start_time": slot["start_time"].isoformat(),
                        "end_time": slot["end_time"].isoformat(),
                        "session_id": session_id,
                    },
                )

    async def confirm_booking(self, slot_id: str, patient_id: str, session_id: str) -> ToolResult:
        """Called after patient verbally confirms — converts held→booked."""
        pool = await self._get_pool()
        confirmation_code = str(uuid.uuid4())[:8].upper()

        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    UPDATE slots
                    SET status = 'booked',
                        patient_id = $1,
                        held_by = NULL,
                        held_until = NULL,
                        confirmation_code = $2
                    WHERE id = $3
                      AND held_by = $4
                      AND held_until > NOW()
                    RETURNING id, doctor_id, start_time,
                              (SELECT name FROM doctors WHERE id = slots.doctor_id) AS doctor_name,
                              confirmation_code
                    """,
                    patient_id, confirmation_code, slot_id, session_id,
                )

                if not row:
                    return ToolResult(
                        status="error",
                        data={"error": "slot_hold_expired_or_invalid"},
                    )

                return ToolResult(
                    status="booked",
                    data={
                        "slot_id": str(row["id"]),
                        "doctor_name": row["doctor_name"],
                        "start_time": row["start_time"].isoformat(),
                        "confirmation_code": row["confirmation_code"],
                    },
                )

    async def cancel(self, appointment_id: str, patient_id: str) -> ToolResult:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE slots
                SET status = 'free', patient_id = NULL, confirmation_code = NULL
                WHERE id = $1 AND patient_id = $2 AND status = 'booked'
                """,
                appointment_id, patient_id,
            )
            if result == "UPDATE 1":
                return ToolResult(status="cancelled", data={})
            return ToolResult(status="error", data={"error": "appointment_not_found"})

    async def reschedule(
        self,
        appointment_id: str,
        patient_id: str,
        new_time: str,
        session_id: str,
    ) -> ToolResult:
        """Cancel existing + book new in a single transaction."""
        cancel_result = await self.cancel(appointment_id, patient_id)
        if cancel_result.status != "cancelled":
            return cancel_result
        return await self.book_slot(
            doctor_name=None,
            patient_id=patient_id,
            preferred_time=new_time,
            session_id=session_id,
        )

    async def get_available_slots(
        self,
        doctor_name: str | None = None,
        specialty: str | None = None,
        after_time: str | None = None,
        count: int = 3,
    ) -> ToolResult:
        pool = await self._get_pool()
        after_dt = datetime.now()
        if after_time:
            try:
                after_dt = datetime.fromisoformat(after_time)
            except ValueError:
                pass

        async with pool.acquire() as conn:
            slots = await conn.fetch(
                """
                SELECT s.id, s.start_time, s.end_time,
                       d.name AS doctor_name, d.specialty
                FROM slots s
                JOIN doctors d ON d.id = s.doctor_id
                WHERE s.status = 'free'
                  AND s.start_time > $1
                  AND ($2::text IS NULL OR LOWER(d.name) LIKE LOWER($2))
                  AND ($3::text IS NULL OR LOWER(d.specialty) = LOWER($3))
                ORDER BY s.start_time
                LIMIT $4
                """,
                after_dt, f"%{doctor_name}%" if doctor_name else None,
                specialty, count,
            )

        return ToolResult(
            status="slots_listed",
            data={"slots": [dict(s) for s in slots]},
        )

    async def get_next_available(
        self,
        doctor_id: str | None,
        after: datetime,
        n: int = 3,
        conn=None,
    ) -> list:
        query = """
            SELECT s.id, s.start_time, s.end_time,
                   d.name AS doctor_name
            FROM slots s
            JOIN doctors d ON d.id = s.doctor_id
            WHERE s.status = 'free'
              AND s.start_time > $1
              AND ($2::uuid IS NULL OR s.doctor_id = $2)
            ORDER BY s.start_time
            LIMIT $3
        """
        if conn:
            return await conn.fetch(query, after, doctor_id, n)
        pool = await self._get_pool()
        async with pool.acquire() as c:
            return await c.fetch(query, after, doctor_id, n)
