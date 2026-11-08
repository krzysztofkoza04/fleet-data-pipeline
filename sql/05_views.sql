
-- =====================================================
-- FLEET DATA PIPELINE
-- 05_views.sql
-- Reporting and monitoring views
-- =====================================================


-- =====================================================
-- 1. VEHICLE OVERVIEW
-- Summarize telemetry statistics for each vehicle
-- =====================================================

CREATE OR REPLACE VIEW fleet.v_vehicle_overview AS

SELECT
    v.vehicle_id,
    v.registration_number,
    v.vehicle_type,
    v.is_active,

    COUNT(g.event_id) AS total_events,

    ROUND(AVG(g.speed_kmh), 2) AS avg_speed_kmh,

    MAX(g.speed_kmh) AS max_speed_kmh,

    ROUND(AVG(g.fuel_level), 2) AS avg_fuel_level,

    MAX(g.timestamp) AS last_event_at

FROM fleet.vehicles v

LEFT JOIN fleet.gps_events g
    ON v.vehicle_id = g.vehicle_id

GROUP BY
    v.vehicle_id,
    v.registration_number,
    v.vehicle_type,
    v.is_active;


-- =====================================================
-- 2. LATEST VEHICLE POSITION
-- Return the most recent GPS event per vehicle
-- =====================================================

CREATE OR REPLACE VIEW fleet.v_latest_vehicle_position AS

SELECT DISTINCT ON (g.vehicle_id)
    g.vehicle_id,
    v.registration_number,
    v.vehicle_type,

    g.timestamp AS last_event_at,
    g.latitude,
    g.longitude,
    g.speed_kmh,
    g.fuel_level,
    g.heading_degrees

FROM fleet.gps_events g

JOIN fleet.vehicles v
    ON g.vehicle_id = v.vehicle_id

ORDER BY
    g.vehicle_id,
    g.timestamp DESC,
    g.event_id DESC;


-- =====================================================
-- 3. DAILY FLEET PERFORMANCE
-- Expose precomputed daily KPIs for reporting
-- =====================================================

CREATE OR REPLACE VIEW fleet.v_daily_fleet_performance AS

SELECT
    d.vehicle_id,
    v.registration_number,
    v.vehicle_type,

    d.report_date,
    d.event_count,
    d.avg_speed_kmh,
    d.max_speed_kmh,

    d.total_stop_seconds,

    ROUND(
        d.total_stop_seconds / 60.0,
        2
    ) AS total_stop_minutes,

    d.total_fuel_consumed_pct_points,
    d.refueling_count,
    d.updated_at

FROM fleet.daily_vehicle_stats d

JOIN fleet.vehicles v
    ON d.vehicle_id = v.vehicle_id;


-- =====================================================
-- 4. TELEMETRY GAPS
-- Detect intervals longer than 60 seconds
-- =====================================================

CREATE OR REPLACE VIEW fleet.v_telemetry_gaps AS

WITH event_history AS (

    SELECT
        vehicle_id,
        timestamp,

        LAG(timestamp) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_timestamp

    FROM fleet.gps_events
),

time_differences AS (

    SELECT
        vehicle_id,
        previous_timestamp,
        timestamp,

        EXTRACT(
            EPOCH FROM (
                timestamp - previous_timestamp
            )
        ) AS gap_seconds

    FROM event_history
)

SELECT
    vehicle_id,
    previous_timestamp,
    timestamp AS current_timestamp,
    gap_seconds

FROM time_differences

WHERE gap_seconds > 60;


-- =====================================================
-- 5. REFUELING EVENTS
-- Detect fuel level increases greater than 10 points
-- =====================================================

CREATE OR REPLACE VIEW fleet.v_refueling_events AS

WITH fuel_history AS (

    SELECT
        vehicle_id,
        timestamp,
        fuel_level,

        LAG(fuel_level) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_fuel_level

    FROM fleet.gps_events
),

fuel_changes AS (

    SELECT
        vehicle_id,
        timestamp,
        fuel_level,
        previous_fuel_level,

        fuel_level - previous_fuel_level
            AS fuel_change

    FROM fuel_history
)

SELECT
    vehicle_id,
    timestamp,
    previous_fuel_level,
    fuel_level,
    fuel_change

FROM fuel_changes

WHERE fuel_change > 10;


-- =====================================================
-- 6. ANOMALY OVERVIEW
-- Combine anomaly records with vehicle information
-- =====================================================

CREATE OR REPLACE VIEW fleet.v_anomaly_overview AS

SELECT
    a.anomaly_id,
    a.vehicle_id,

    v.registration_number,
    v.vehicle_type,

    a.event_id,
    a.run_id,

    a.anomaly_type,
    a.detected_at,
    a.anomaly_value,
    a.threshold_value,
    a.description,
    a.created_at

FROM fleet.fleet_anomalies a

JOIN fleet.vehicles v
    ON a.vehicle_id = v.vehicle_id;


-- =====================================================
-- 7. ETL MONITORING
-- Monitor pipeline executions and processing metrics
-- =====================================================

CREATE OR REPLACE VIEW fleet.v_etl_monitoring AS

SELECT
    run_id,
    started_at,
    finished_at,
    status,

    total_records,
    valid_records,
    rejected_records,
    duplicate_records,

    ROUND(
        valid_records * 100.0
        / NULLIF(total_records, 0),
        2
    ) AS valid_percent,

    ROUND(
        rejected_records * 100.0
        / NULLIF(total_records, 0),
        2
    ) AS rejected_percent,

    EXTRACT(
        EPOCH FROM (
            finished_at - started_at
        )
    ) AS duration_seconds,

    error_message

FROM fleet.etl_runs;
