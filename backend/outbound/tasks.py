"""
outbound/tasks.py

Celery tasks for outbound reminder calls.
Retry logic: 3 attempts with exponential backoff (15min, 1h, 4h).
Falls back to SMS if all call attempts fail.
"""
import logging
import os
from datetime import datetime

from celery import Celery
from celery.exceptions import MaxRetriesExceeded

from .sip_client import SIPClient, NoAnswer, Busy
from .campaign_scheduler import CampaignScheduler

logger = logging.getLogger(__name__)

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")

celery_app = Celery("outbound", broker=CELERY_BROKER_URL, backend=CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,           # re-queue on worker crash
    worker_prefetch_multiplier=1,  # fair dispatch
)

sip_client = SIPClient()
campaign = CampaignScheduler()


@celery_app.task(bind=True, max_retries=3, name="outbound.place_reminder_call")
def place_reminder_call(self, patient_id: str, appointment_id: str):
    """
    Place an outbound reminder call to a patient.
    Retries 3 times with exponential backoff before SMS fallback.
    """
    try:
        patient = campaign.get_patient(patient_id)
        appt = campaign.get_appointment(appointment_id)

        if not patient or not appt:
            logger.error("Patient or appointment not found: %s / %s", patient_id, appointment_id)
            return

        script_vars = {
            "name": patient["preferred_name"] or patient["name"],
            "doctor": appt["doctor_name"],
            "time": _localize_time(appt["start_time"], patient["timezone"]),
            "lang": patient["preferred_lang"],
            "hospital": "MedCare Hospital",
        }

        logger.info(
            "Placing reminder call: patient=%s appt=%s attempt=%d",
            patient_id, appointment_id, self.request.retries + 1
        )

        call_sid = sip_client.dial(
            to=patient["phone"],
            script_vars=script_vars,
            timeout_seconds=30,
        )

        campaign.record_call_attempt(
            call_sid=call_sid,
            patient_id=patient_id,
            appointment_id=appointment_id,
            attempt=self.request.retries,
            status="dialed",
        )

        logger.info("Call placed successfully: %s", call_sid)

    except (NoAnswer, Busy) as e:
        # Exponential backoff: 15min (900s), 1h (3600s), 4h (14400s)
        countdown = 900 * (4 ** self.request.retries)
        logger.warning(
            "Call failed (%s), retry %d in %ds",
            type(e).__name__, self.request.retries + 1, countdown
        )
        try:
            raise self.retry(exc=e, countdown=countdown)
        except MaxRetriesExceeded:
            logger.warning("Max retries exceeded for %s — sending SMS", patient_id)
            _send_sms_fallback(patient_id, appointment_id)

    except Exception as e:
        logger.error("Unexpected error in place_reminder_call: %s", e, exc_info=True)
        raise


@celery_app.task(name="outbound.schedule_daily_reminders")
def schedule_daily_reminders():
    """
    Celery Beat task — runs every hour.
    Enqueues reminder calls for appointments in 24h and 2h windows.
    """
    appointments_24h = campaign.get_appointments_due_reminder(hours_ahead=24)
    appointments_2h = campaign.get_appointments_due_reminder(hours_ahead=2)

    for appt in appointments_24h + appointments_2h:
        place_reminder_call.apply_async(
            args=[appt["patient_id"], appt["id"]],
            queue="outbound_calls",
        )

    logger.info(
        "Scheduled %d reminder calls (24h: %d, 2h: %d)",
        len(appointments_24h) + len(appointments_2h),
        len(appointments_24h),
        len(appointments_2h),
    )


def _send_sms_fallback(patient_id: str, appointment_id: str):
    """SMS fallback when all call attempts fail."""
    try:
        patient = campaign.get_patient(patient_id)
        appt = campaign.get_appointment(appointment_id)
        if patient and appt:
            sip_client.send_sms(
                to=patient["phone"],
                body=(
                    f"Reminder: Your appointment with {appt['doctor_name']} "
                    f"at MedCare Hospital is on "
                    f"{_localize_time(appt['start_time'], patient['timezone'])}. "
                    f"Call us to reschedule."
                ),
            )
    except Exception as e:
        logger.error("SMS fallback also failed: %s", e)


def _localize_time(iso_time: str, timezone: str) -> str:
    """Format appointment time in patient's local timezone."""
    try:
        import pytz
        dt = datetime.fromisoformat(iso_time)
        tz = pytz.timezone(timezone or "Asia/Kolkata")
        local_dt = dt.astimezone(tz)
        return local_dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        return iso_time


# Celery Beat schedule
celery_app.conf.beat_schedule = {
    "schedule-reminders-hourly": {
        "task": "outbound.schedule_daily_reminders",
        "schedule": 3600,  # every hour
    },
}
