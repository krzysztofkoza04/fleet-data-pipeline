-- FLEET DATA PIPELINE
-- 01_schema.sql
-- PostgreSQL database schema

BEGIN;


-- 1. SCHEMA


CREATE SCHEMA IF NOT EXISTS fleet;


-- 2. VEHICLES


CREATE TABLE IF NOT EXISTS fleet.vehicles (

    vehicle_id VARCHAR(30) PRIMARY KEY,

    registration_number VARCHAR(20) NOT NULL UNIQUE,

    vehicle_type VARCHAR(30) NOT NULL,

    fuel_capacity_liters NUMERIC(8,2) NOT NULL
        CHECK (fuel_capacity_liters > 0),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

);


-- 3. ETL RUNS

CREATE TABLE IF NOT EXISTS fleet.etl_runs (

    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    finished_at TIMESTAMPTZ,

    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),

    total_records INTEGER NOT NULL DEFAULT 0
        CHECK (total_records >= 0),

    valid_records INTEGER NOT NULL DEFAULT 0
        CHECK (valid_records >= 0),

    rejected_records INTEGER NOT NULL DEFAULT 0
        CHECK (rejected_records >= 0),

    duplicate_records INTEGER NOT NULL DEFAULT 0
        CHECK (duplicate_records >= 0),

    error_message TEXT,

    CHECK (
        finished_at IS NULL
        OR finished_at >= started_at
    )

);


-- 4. GPS EVENTS


CREATE TABLE IF NOT EXISTS fleet.gps_events (

    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    vehicle_id VARCHAR(30) NOT NULL
        REFERENCES fleet.vehicles(vehicle_id),

    run_id BIGINT
        REFERENCES fleet.etl_runs(run_id),

    timestamp TIMESTAMPTZ NOT NULL,

    latitude DOUBLE PRECISION NOT NULL
        CHECK (latitude BETWEEN -90 AND 90),

    longitude DOUBLE PRECISION NOT NULL
        CHECK (longitude BETWEEN -180 AND 180),

    speed_kmh NUMERIC(7,2) NOT NULL
        CHECK (speed_kmh BETWEEN 0 AND 180),

    fuel_level NUMERIC(5,2)
        CHECK (fuel_level BETWEEN 0 AND 100),

    heading_degrees NUMERIC(6,2)
        CHECK (heading_degrees >= 0 AND heading_degrees < 360),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_gps_vehicle_timestamp
        UNIQUE (vehicle_id, timestamp)

);


-- 5. REJECTED EVENTS


CREATE TABLE IF NOT EXISTS fleet.rejected_events (

    rejected_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT
        REFERENCES fleet.etl_runs(run_id),

    vehicle_id VARCHAR(30),

    raw_data JSONB NOT NULL,

    rejection_reasons JSONB NOT NULL
        CHECK (jsonb_typeof(rejection_reasons) = 'array'),

    rejected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

);



-- 6. DAILY VEHICLE STATS


CREATE TABLE IF NOT EXISTS fleet.daily_vehicle_stats (

    vehicle_id VARCHAR(30) NOT NULL
        REFERENCES fleet.vehicles(vehicle_id),

    report_date DATE NOT NULL,

    event_count INTEGER NOT NULL DEFAULT 0
        CHECK (event_count >= 0),

    avg_speed_kmh NUMERIC(7,2)
        CHECK (avg_speed_kmh BETWEEN 0 AND 180),

    max_speed_kmh NUMERIC(7,2)
        CHECK (max_speed_kmh BETWEEN 0 AND 180),

    total_stop_seconds NUMERIC(12,2) NOT NULL DEFAULT 0
        CHECK (total_stop_seconds >= 0),

    total_fuel_consumed_pct_points NUMERIC(12,2) NOT NULL DEFAULT 0
        CHECK (total_fuel_consumed_pct_points >= 0),

    refueling_count INTEGER NOT NULL DEFAULT 0
        CHECK (refueling_count >= 0),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (vehicle_id, report_date)

);


-- 7. FLEET ANOMALIES


CREATE TABLE IF NOT EXISTS fleet.fleet_anomalies (

    anomaly_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    vehicle_id VARCHAR(30) NOT NULL
        REFERENCES fleet.vehicles(vehicle_id),

    event_id BIGINT
        REFERENCES fleet.gps_events(event_id),

    run_id BIGINT
        REFERENCES fleet.etl_runs(run_id),

    anomaly_type VARCHAR(50) NOT NULL,

    detected_at TIMESTAMPTZ NOT NULL,

    anomaly_value NUMERIC(14,4),

    threshold_value NUMERIC(14,4),

    description TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

);


-- 8. INDEXES

CREATE INDEX IF NOT EXISTS idx_gps_timestamp
ON fleet.gps_events (timestamp);

CREATE INDEX IF NOT EXISTS idx_gps_run_id
ON fleet.gps_events (run_id);

CREATE INDEX IF NOT EXISTS idx_etl_runs_status_started
ON fleet.etl_runs (status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_rejected_run_id
ON fleet.rejected_events (run_id);

CREATE INDEX IF NOT EXISTS idx_anomalies_vehicle_time
ON fleet.fleet_anomalies (vehicle_id, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_anomalies_type
ON fleet.fleet_anomalies (anomaly_type);

CREATE INDEX IF NOT EXISTS idx_daily_stats_date
ON fleet.daily_vehicle_stats (report_date);


COMMIT;
