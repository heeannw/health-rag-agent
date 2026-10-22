CREATE TABLE IF NOT EXISTS benefit (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('central', 'local')),
    source_service_id TEXT NOT NULL,
    name TEXT NOT NULL,
    target_text TEXT,
    summary_text TEXT,
    criteria_text TEXT,
    source_url TEXT,
    provider_province TEXT,
    provider_municipality TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    benefit_text TEXT,
    detail_collected_at TIMESTAMPTZ,
    UNIQUE (source, source_service_id)
);

SELECT * FROM benefit LIMIT 100;

ALTER TABLE benefit ADD COLUMN IF NOT EXISTS application_start_date DATE;
ALTER TABLE benefit ADD COLUMN IF NOT EXISTS application_deadline DATE;
ALTER TABLE benefit ADD COLUMN IF NOT EXISTS application_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (application_status IN ('unknown', 'scheduled', 'open', 'closed'));
ALTER TABLE benefit ADD COLUMN IF NOT EXISTS application_period_text TEXT;
ALTER TABLE benefit ADD COLUMN IF NOT EXISTS status_checked_at TIMESTAMPTZ;

CREATE OR REPLACE FUNCTION refresh_benefit_application_status()
RETURNS void LANGUAGE sql AS $$
    UPDATE benefit SET application_status = CASE
        WHEN application_start_date IS NULL OR application_deadline IS NULL THEN 'unknown'
        WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date < application_start_date THEN 'scheduled'
        WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date > application_deadline THEN 'closed'
        ELSE 'open' END,
        status_checked_at = CURRENT_TIMESTAMP;
$$;
