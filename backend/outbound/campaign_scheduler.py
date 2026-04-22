"""
outbound/campaign_scheduler.py

Campaign scheduling — determines which patients get reminder calls and when.
"""
import logging
from datetime import datetime, timedelta

import asyncpg

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/voiceai"


class CampaignScheduler:
    """Synchronous DB access for Celery tasks (Celery workers are not async)."""

    def get_appointments_due_reminder(self, hours_ahead: int) -> list[dict]:
        import psycopg2
        import psycopg2.extras

        target_start = datetime.now() + timedelta(hours=hours_ahead - 1)
        target_end = datetime.now() + timedelta(hours=hours_ahead + 1)

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT s.id, s.patient_id, s.start_time,
                           d.name AS doctor_name
                    FROM slots s
                    JOIN doctors d ON d.id = s.doctor_id
                    WHERE s.status = 'booked'
                      AND s.start_time BETWEEN %s AND %s
                      AND s.reminder_sent_%sh IS NOT TRUE
                    """,
                    (target_start, target_end, hours_ahead),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_patient(self, patient_id: str) -> dict | None:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM patients WHERE id = %s", (patient_id,)
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def get_appointment(self, appointment_id: str) -> dict | None:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT s.*, d.name AS doctor_name
                    FROM slots s JOIN doctors d ON d.id = s.doctor_id
                    WHERE s.id = %s
                    """,
                    (appointment_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def record_call_attempt(self, **kwargs):
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO outbound_call_log
                      (call_sid, patient_id, appointment_id, attempt, status, created_at)
                    VALUES (%(call_sid)s, %(patient_id)s, %(appointment_id)s,
                            %(attempt)s, %(status)s, NOW())
                    """,
                    kwargs,
                )
            conn.commit()
        finally:
            conn.close()
