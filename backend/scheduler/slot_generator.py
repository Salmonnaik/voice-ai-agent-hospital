"""
scheduler/slot_generator.py

Pre-generates appointment slots for all doctors for the next N days.
Run daily via Celery beat or a cron job.

Design: slots are always pre-computed, never generated on-demand.
This ensures O(1) availability lookup at booking time.
"""
import asyncio
import logging
from datetime import datetime, timedelta, time

import asyncpg

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/voiceai"

# Working hours configuration
WORK_START_HOUR = 9       # 9:00 AM
WORK_END_HOUR = 17        # 5:00 PM (last slot starts at 4:45)
SLOT_DURATION_MIN = 15
SKIP_WEEKDAYS = {6}       # 0=Mon … 6=Sun; skip Sunday


async def generate_slots_for_doctor(conn, doctor_id: str, days_ahead: int = 30):
    """Generate free slots for a single doctor for the next N days."""
    today = datetime.now().date()
    created = 0

    for day_offset in range(1, days_ahead + 1):
        slot_date = today + timedelta(days=day_offset)
        if slot_date.weekday() in SKIP_WEEKDAYS:
            continue

        slot_hour = WORK_START_HOUR
        slot_min = 0

        while slot_hour < WORK_END_HOUR:
            start_naive = datetime.combine(slot_date, time(slot_hour, slot_min))
            end_naive = start_naive + timedelta(minutes=SLOT_DURATION_MIN)

            # Store in IST (Asia/Kolkata)
            import pytz
            ist = pytz.timezone("Asia/Kolkata")
            start_tz = ist.localize(start_naive)
            end_tz = ist.localize(end_naive)

            try:
                await conn.execute(
                    """
                    INSERT INTO slots (doctor_id, start_time, end_time, status)
                    VALUES ($1, $2, $3, 'free')
                    ON CONFLICT DO NOTHING
                    """,
                    doctor_id, start_tz, end_tz,
                )
                created += 1
            except Exception as e:
                logger.warning("Slot insert failed: %s", e)

            slot_min += SLOT_DURATION_MIN
            if slot_min >= 60:
                slot_min = 0
                slot_hour += 1

    return created


async def generate_all_slots(days_ahead: int = 30):
    """Generate slots for all active doctors."""
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
    async with pool.acquire() as conn:
        doctors = await conn.fetch("SELECT id, name FROM doctors WHERE active = TRUE")
        logger.info("Generating slots for %d doctors, %d days ahead", len(doctors), days_ahead)

        total = 0
        for doc in doctors:
            n = await generate_slots_for_doctor(conn, str(doc["id"]), days_ahead)
            logger.info("Doctor %s: %d slots created", doc["name"], n)
            total += n

    await pool.close()
    logger.info("Slot generation complete: %d total slots created", total)
    return total


if __name__ == "__main__":
    asyncio.run(generate_all_slots())
