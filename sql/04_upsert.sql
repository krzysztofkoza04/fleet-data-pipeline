
-- =====================================================
-- FLEET DATA PIPELINE
-- 04_upsert.sql
-- Idempotent vehicle, GPS, and daily KPI upserts
-- =====================================================

BEGIN;


-- =====================================================
-- 1. UPSERT VEHICLES
-- Insert new vehicles or update changed attributes
-- =====================================================

INSERT INTO fleet.vehicles (
    vehicle_id,
    registration_number,
    vehicle_type,
    fuel_capacity_liters,
    is_active
)
VALUES
    ('TRUCK_001', 'RZ10001', 'Volvo FH', 600, TRUE),
    ('TRUCK_006', 'RZ10006', 'Iveco S-Way', 550, TRUE)

ON CONFLICT (vehicle_id)
DO UPDATE SET
    registration_number = EXCLUDED.registration_number,
    vehicle_type = EXCLUDED.vehicle_type,
    fuel_capacity_liters = EXCLUDED.fuel_capacity_liters,
    is_active = EXCLUDED.is_active

WHERE (
    vehicles.registration_number,
    vehicles.vehicle_type,
    vehicles.fuel_capacity_liters,
    vehicles.is_active
) IS DISTINCT FROM (
    EXCLUDED.registration_number,
    EXCLUDED.vehicle_type,
    EXCLUDED.fuel_capacity_liters,
    EXCLUDED.is_active
);


-- =====================================================
-- 2. UPSERT GPS EVENTS
-- Prevent duplicates and update corrected measurements
-- =====================================================

INSERT INTO fleet.gps_events (
    vehicle_id,
    timestamp,
    latitude,
    longitude,
    speed_kmh,
    fuel_level,
    heading_degrees
)
VALUES
    (
        'TRUCK_001',
        '2026-11-07 08:02:00+00',
        50.0490, 22.0080, 70, 78, 95
    ),
    (
        'TRUCK_006',
        '2026-11-07 08:00:00+00',
        50.5000, 22.5000, 45, 90, 100
    ),
    (
        'TRUCK_006',
        '2026-11-07 08:01:00+00',
        50.5030, 22.5030, 50, 89, 102
    ),
    (
        'TRUCK_006',
        '2026-11-07 08:02:00+00',
        50.5060, 22.5060, 55, 88, 105
    )

ON CONFLICT (vehicle_id, timestamp)
DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    speed_kmh = EXCLUDED.speed_kmh,
    fuel_level = EXCLUDED.fuel_level,
    heading_degrees = EXCLUDED.heading_degrees

WHERE (
    gps_events.latitude,
    gps_events.longitude,
    gps_events.speed_kmh,
    gps_events.fuel_level,
    gps_events.heading_degrees
) IS DISTINCT FROM (
    EXCLUDED.latitude,
    EXCLUDED.longitude,
    EXCLUDED.speed_kmh,
    EXCLUDED.fuel_level,
    EXCLUDED.heading_degrees
);


-- =====================================================
-- 3. CALCULATE DAILY VEHICLE STATISTICS
-- Use chronological measurements for each vehicle
-- =====================================================

WITH event_history AS (

    SELECT
        vehicle_id,
        timestamp,
        speed_kmh,
        fuel_level,

        LAG(timestamp) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_timestamp,

        LAG(speed_kmh) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_speed,

        LAG(fuel_level) OVER (
            PARTITION BY vehicle_id
            ORDER BY timestamp
        ) AS previous_fuel

    FROM fleet.gps_events
),

daily_aggregates AS (

    SELECT
        vehicle_id,

        (timestamp AT TIME ZONE 'UTC')::DATE AS report_date,

        COUNT(*)::INTEGER AS event_count,

        ROUND(AVG(speed_kmh), 2) AS avg_speed_kmh,

        MAX(speed_kmh) AS max_speed_kmh,

        SUM(
            CASE
                WHEN speed_kmh = 0
                 AND previous_speed = 0
                 AND timestamp > previous_timestamp
                THEN EXTRACT(
                    EPOCH FROM (timestamp - previous_timestamp)
                )
                ELSE 0
            END
        ) AS total_stop_seconds,

        SUM(
            CASE
                WHEN fuel_level < previous_fuel
                THEN previous_fuel - fuel_level
                ELSE 0
            END
        ) AS total_fuel_consumed_pct_points,

        COUNT(*) FILTER (
            WHERE fuel_level - previous_fuel > 10
        )::INTEGER AS refueling_count

    FROM event_history

    GROUP BY
        vehicle_id,
        (timestamp AT TIME ZONE 'UTC')::DATE
)

-- =====================================================
-- 4. UPSERT DAILY VEHICLE STATISTICS
-- Update rows only when calculated values change
-- =====================================================

INSERT INTO fleet.daily_vehicle_stats (
    vehicle_id,
    report_date,
    event_count,
    avg_speed_kmh,
    max_speed_kmh,
    total_stop_seconds,
    total_fuel_consumed_pct_points,
    refueling_count
)

SELECT
    vehicle_id,
    report_date,
    event_count,
    avg_speed_kmh,
    max_speed_kmh,
    total_stop_seconds,
    total_fuel_consumed_pct_points,
    refueling_count

FROM daily_aggregates

ON CONFLICT (vehicle_id, report_date)
DO UPDATE SET
    event_count = EXCLUDED.event_count,
    avg_speed_kmh = EXCLUDED.avg_speed_kmh,
    max_speed_kmh = EXCLUDED.max_speed_kmh,
    total_stop_seconds = EXCLUDED.total_stop_seconds,
    total_fuel_consumed_pct_points =
        EXCLUDED.total_fuel_consumed_pct_points,
    refueling_count = EXCLUDED.refueling_count,
    updated_at = CURRENT_TIMESTAMP

WHERE (
    daily_vehicle_stats.event_count,
    daily_vehicle_stats.avg_speed_kmh,
    daily_vehicle_stats.max_speed_kmh,
    daily_vehicle_stats.total_stop_seconds,
    daily_vehicle_stats.total_fuel_consumed_pct_points,
    daily_vehicle_stats.refueling_count
) IS DISTINCT FROM (
    EXCLUDED.event_count,
    EXCLUDED.avg_speed_kmh,
    EXCLUDED.max_speed_kmh,
    EXCLUDED.total_stop_seconds,
    EXCLUDED.total_fuel_consumed_pct_points,
    EXCLUDED.refueling_count
);


COMMIT;
