-- =============================================================================
-- Voice AI Platform — Database Schema
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- required for EXCLUDE constraint

-- -----------------------------------------------------------------------------
-- Doctors
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctors (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    specialty   TEXT NOT NULL,
    phone       TEXT,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_doctors_name ON doctors USING gin(to_tsvector('english', name));
CREATE INDEX idx_doctors_specialty ON doctors (LOWER(specialty));

-- -----------------------------------------------------------------------------
-- Patients
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    preferred_name  TEXT,
    phone           TEXT UNIQUE NOT NULL,
    preferred_lang  TEXT DEFAULT 'en' CHECK (preferred_lang IN ('en', 'hi', 'ta')),
    preferred_doctor UUID REFERENCES doctors(id),
    timezone        TEXT DEFAULT 'Asia/Kolkata',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_patients_phone ON patients (phone);

-- -----------------------------------------------------------------------------
-- Slots (pre-generated appointment slots)
-- Conflict prevention via DB-level EXCLUDE constraint — impossible to double-book
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS slots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id       UUID NOT NULL REFERENCES doctors(id),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    duration_min    INTEGER DEFAULT 15,

    -- Status state machine: free → held → booked | free → blocked
    status          TEXT NOT NULL DEFAULT 'free'
                    CHECK (status IN ('free', 'held', 'booked', 'blocked')),

    -- Hold management (90-second optimistic window)
    held_by         TEXT,           -- session_id
    held_until      TIMESTAMPTZ,

    -- Booking data
    patient_id      UUID REFERENCES patients(id),
    confirmation_code TEXT,

    -- Reminder tracking
    reminder_sent_24h  BOOLEAN DEFAULT FALSE,
    reminder_sent_2h   BOOLEAN DEFAULT FALSE,

    created_at      TIMESTAMPTZ DEFAULT NOW(),

    -- CRITICAL: DB-level double-booking prevention
    CONSTRAINT no_overlap EXCLUDE USING gist (
        doctor_id WITH =,
        tstzrange(start_time, end_time, '[)') WITH &&
    ) WHERE (status IN ('held', 'booked'))
);

CREATE INDEX idx_slots_doctor_status_time ON slots (doctor_id, status, start_time);
CREATE INDEX idx_slots_patient ON slots (patient_id) WHERE patient_id IS NOT NULL;
CREATE INDEX idx_slots_held_until ON slots (held_until) WHERE status = 'held';
CREATE INDEX idx_slots_reminders ON slots (start_time) WHERE status = 'booked';

-- -----------------------------------------------------------------------------
-- Outbound call log
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outbound_call_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_sid        TEXT,
    patient_id      UUID REFERENCES patients(id),
    appointment_id  UUID REFERENCES slots(id),
    attempt         INTEGER DEFAULT 0,
    status          TEXT,   -- dialed | answered | no_answer | busy | failed | sms_sent
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outbound_patient ON outbound_call_log (patient_id);

-- -----------------------------------------------------------------------------
-- Background task: expire stale holds every 30 seconds
-- (Complement to Celery beat task — belt and suspenders)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION expire_stale_holds() RETURNS void AS $$
BEGIN
    UPDATE slots
    SET status = 'free', held_by = NULL, held_until = NULL
    WHERE status = 'held'
      AND held_until < NOW();
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Seed data: sample doctors
-- -----------------------------------------------------------------------------
INSERT INTO doctors (name, specialty) VALUES
    ('Dr. Ananya Sharma', 'General Medicine'),
    ('Dr. Rajesh Kumar', 'Cardiology'),
    ('Dr. Priya Nair', 'Gynecology'),
    ('Dr. Suresh Patel', 'Orthopedics'),
    ('Dr. Meena Iyer', 'Pediatrics')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- Seed data: pre-generate slots for the next 30 days
-- 9am–5pm, 15-min slots, Mon–Sat, all doctors
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    doc RECORD;
    slot_date DATE;
    slot_time TIMESTAMPTZ;
    slot_hour INTEGER;
    slot_min INTEGER;
BEGIN
    FOR doc IN SELECT id FROM doctors LOOP
        FOR day_offset IN 1..30 LOOP
            slot_date := CURRENT_DATE + day_offset;
            -- Skip Sundays
            IF EXTRACT(DOW FROM slot_date) = 0 THEN CONTINUE; END IF;

            FOR slot_hour IN 9..16 LOOP
                FOR slot_min IN 0, 15, 30, 45 LOOP
                    slot_time := (slot_date + (slot_hour || ':' || slot_min || ':00')::TIME)
                                 AT TIME ZONE 'Asia/Kolkata';
                    INSERT INTO slots (doctor_id, start_time, end_time, status)
                    VALUES (
                        doc.id,
                        slot_time,
                        slot_time + INTERVAL '15 minutes',
                        'free'
                    )
                    ON CONFLICT DO NOTHING;
                END LOOP;
            END LOOP;
        END LOOP;
    END LOOP;
END $$;
