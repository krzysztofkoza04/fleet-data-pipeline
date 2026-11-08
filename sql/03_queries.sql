
-- =====================================================
-- FLEET DATA PIPELINE
-- 03_queries.sql
-- Fleet telemetry analytics and data quality queries
-- =====================================================

-- =====================================================
-- 1. FLEET OVERVIEW
-- Basic vehicle telemetry statistics
-- =====================================================

SELECT
    v.vehicle_id,
    v.registration_number,
    v.vehicle_type,
    COUNT(g.event_id) AS total_events,
    ROUND(AVG(g.speed_kmh), 2) AS avg_speed_kmh,
    MAX(g.speed_kmh) AS max_speed_kmh,
    MIN(g.fuel_level) AS min_fuel_level,
    MAX(g.timestamp) AS last_event_at
FROM fleet.vehicles v
LEFT JOIN fleet.gps_events g
    ON v.vehicle_id = g.vehicle_id
GROUP BY
    v.vehicle_id,
    v.registration_number,
    v.vehicle_type
ORDER BY v.vehicle_id;


-- =====================================================
-- 2. DAILY VEHICLE STATISTICS
-- Aggregate GPS events by vehicle and UTC date
-- =====================================================

SELECT
    vehicle_id,
    (timestamp AT TIME ZONE 'UTC')::DATE AS report_date,
    COUNT(*) AS event_count,
    ROUND(AVG(speed_kmh), 2) AS avg_speed_kmh,
    MAX(speed_kmh) AS max_speed_kmh,
    MIN(speed_kmh) AS min_speed_kmh,
    ROUND(AVG(fuel_level), 2) AS avg_fuel_level
FROM fleet.gps_events
GROUP BY
    vehicle_id,
    (timestamp AT TIME ZONE 'UTC')::DATE
ORDER BY vehicle_id, report_date;


-- =====================================================
-- 3. LATEST EVENT PER VEHICLE
-- Select the most recent GPS record
-- =====================================================

WITH ranked_events AS (
    SELECT
        vehicle_id,
        timestamp,
        speed_kmh,
        fuel_level,
        latitude,
        longitude,
        ROW_NUMBER() OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp DESC
        ) AS row_num
    FROM fleet.gps_events
)

SELECT
    vehicle_id,
    timestamp,
    speed_kmh,
    fuel_level,
    latitude,
    longitude
FROM ranked_events
WHERE row_num = 1
ORDER BY vehicle_id;


-- =====================================================
-- 4. SPEED CHANGES
-- Compare each measurement with the previous one
-- =====================================================

WITH speed_history AS (
    SELECT
        vehicle_id,
        timestamp,
        speed_kmh,
        LAG(speed_kmh) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_speed
    FROM fleet.gps_events
)

SELECT
    vehicle_id,
    timestamp,
    speed_kmh,
    previous_speed,
    speed_kmh - previous_speed AS speed_change_kmh,
    ABS(speed_kmh - previous_speed) AS absolute_speed_change
FROM speed_history
ORDER BY vehicle_id, timestamp;


-- =====================================================
-- 5. SUDDEN SPEED CHANGES
-- Detect changes greater than 30 km/h
-- =====================================================

WITH speed_history AS (
    SELECT
        vehicle_id,
        timestamp,
        speed_kmh,
        LAG(speed_kmh) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_speed
    FROM fleet.gps_events
),

speed_changes AS (
    SELECT
        vehicle_id,
        timestamp,
        speed_kmh,
        previous_speed,
        speed_kmh - previous_speed AS speed_change_kmh
    FROM speed_history
)

SELECT
    vehicle_id,
    timestamp,
    speed_kmh,
    previous_speed,
    speed_change_kmh,
    CASE
        WHEN speed_change_kmh > 0 THEN 'acceleration'
        ELSE 'deceleration'
    END AS change_type
FROM speed_changes
WHERE ABS(speed_change_kmh) > 30
ORDER BY vehicle_id, timestamp;


-- =====================================================
-- 6. TELEMETRY GAPS
-- Detect intervals greater than 60 seconds
-- =====================================================

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
        timestamp,
        previous_timestamp,
        EXTRACT(
            EPOCH FROM (timestamp - previous_timestamp)
        ) AS gap_seconds
    FROM event_history
)

SELECT
    vehicle_id,
    previous_timestamp,
    timestamp,
    gap_seconds
FROM time_differences
WHERE gap_seconds > 60
ORDER BY gap_seconds DESC;


-- =====================================================
-- 7. VEHICLE STOP TIME
-- Count intervals where both speeds equal zero
-- =====================================================

WITH event_history AS (
    SELECT
        vehicle_id,
        timestamp,
        speed_kmh,
        LAG(timestamp) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_timestamp,
        LAG(speed_kmh) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_speed
    FROM fleet.gps_events
),

stop_intervals AS (
    SELECT
        vehicle_id,
        CASE
            WHEN speed_kmh = 0
             AND previous_speed = 0
             AND timestamp > previous_timestamp
            THEN EXTRACT(
                EPOCH FROM (timestamp - previous_timestamp)
            )
            ELSE 0
        END AS stop_seconds
    FROM event_history
)

SELECT
    vehicle_id,
    SUM(stop_seconds) AS total_stop_seconds
FROM stop_intervals
GROUP BY vehicle_id
ORDER BY total_stop_seconds DESC;


-- =====================================================
-- 8. FUEL CHANGES AND REFUELING
-- Detect consumption and increases in fuel level
-- =====================================================

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
        fuel_level - previous_fuel_level AS fuel_change
    FROM fuel_history
)

SELECT
    vehicle_id,
    timestamp,
    fuel_level,
    previous_fuel_level,
    fuel_change,
    CASE
        WHEN fuel_change < 0
        THEN ABS(fuel_change)
        WHEN fuel_change IS NULL
        THEN NULL
        ELSE 0
    END AS fuel_consumed,
    CASE
        WHEN fuel_change > 10 THEN TRUE
        ELSE FALSE
    END AS is_refueling
FROM fuel_changes
ORDER BY vehicle_id, timestamp;


-- =====================================================
-- 9. DATA QUALITY CHECKS
-- Verify basic completeness and value ranges
-- =====================================================

SELECT
    COUNT(*) AS total_events,

    COUNT(*) FILTER (
        WHERE vehicle_id IS NULL
    ) AS missing_vehicle_id,

    COUNT(*) FILTER (
        WHERE timestamp IS NULL
    ) AS missing_timestamp,

    COUNT(*) FILTER (
        WHERE fuel_level IS NULL
    ) AS missing_fuel_level,

    COUNT(*) FILTER (
        WHERE speed_kmh < 0 OR speed_kmh > 180
    ) AS invalid_speed,

    COUNT(*) FILTER (
        WHERE latitude NOT BETWEEN -90 AND 90
           OR longitude NOT BETWEEN -180 AND 180
    ) AS invalid_coordinates

FROM fleet.gps_events;


-- =====================================================
-- 10. ETL EXECUTION HISTORY
-- Monitor processing status and record counts
-- =====================================================

SELECT
    run_id,
    started_at,
    finished_at,
    status,
    total_records,
    valid_records,
    rejected_records,
    duplicate_records,
    EXTRACT(
        EPOCH FROM (finished_at - started_at)
    ) AS duration_seconds,
    error_message
FROM fleet.etl_runs
ORDER BY started_at DESC, run_id DESC;


-- =====================================================
-- 11. ETL STATUS SUMMARY
-- Count runs by execution status
-- =====================================================

SELECT
    status,
    COUNT(*) AS run_count,
    SUM(total_records) AS total_processed,
    SUM(valid_records) AS total_valid,
    SUM(rejected_records) AS total_rejected,
    SUM(duplicate_records) AS total_duplicates
FROM fleet.etl_runs
GROUP BY status
ORDER BY status;
