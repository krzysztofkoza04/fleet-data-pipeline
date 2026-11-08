
-- =====================================================
-- FLEET DATA PIPELINE
-- 02_seed.sql
-- Initial test data for PostgreSQL
-- =====================================================

BEGIN;

-- =====================================================
-- 1. INSERT VEHICLES
-- =====================================================

INSERT INTO fleet.vehicles (
    vehicle_id,
    registration_number,
    vehicle_type,
    fuel_capacity_liters
)
VALUES
    ('TRUCK_001', 'RZ10001', 'Volvo FH', 600),
    ('TRUCK_002', 'RZ10002', 'Scania R450', 500),
    ('TRUCK_003', 'RZ10003', 'MAN TGX', 550),
    ('TRUCK_004', 'RZ10004', 'DAF XF', 650),
    ('TRUCK_005', 'RZ10005', 'Mercedes Actros', 600)
ON CONFLICT (vehicle_id) DO NOTHING;


-- =====================================================
-- 2. INSERT SAMPLE GPS EVENTS
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

-- TRUCK_001: Normal driving and a fuel increase
('TRUCK_001', '2026-11-07 08:00:00+00', 50.0413, 21.9990, 60, 80, 90),
('TRUCK_001', '2026-11-07 08:01:00+00', 50.0450, 22.0030, 65, 79, 92),
('TRUCK_001', '2026-11-07 08:02:00+00', 50.0490, 22.0080, 70, 78, 95),
('TRUCK_001', '2026-11-07 08:03:00+00', 50.0520, 22.0120, 0, 77, 95),
('TRUCK_001', '2026-11-07 08:04:00+00', 50.0520, 22.0120, 0, 95, 95),

-- TRUCK_002: Normal driving
('TRUCK_002', '2026-11-07 08:00:00+00', 50.1000, 22.1000, 50, 90, 180),
('TRUCK_002', '2026-11-07 08:01:00+00', 50.1050, 22.1050, 55, 89, 182),
('TRUCK_002', '2026-11-07 08:02:00+00', 50.1100, 22.1100, 60, 88, 185),
('TRUCK_002', '2026-11-07 08:03:00+00', 50.1150, 22.1150, 65, 87, 188),

-- TRUCK_003: Sudden speed change
('TRUCK_003', '2026-11-07 08:00:00+00', 50.2000, 22.2000, 40, 70, 270),
('TRUCK_003', '2026-11-07 08:01:00+00', 50.2050, 22.2050, 45, 69, 272),
('TRUCK_003', '2026-11-07 08:02:00+00', 50.2100, 22.2100, 100, 68, 275),
('TRUCK_003', '2026-11-07 08:03:00+00', 50.2150, 22.2150, 50, 67, 278),

-- TRUCK_004: Vehicle stop
('TRUCK_004', '2026-11-07 08:00:00+00', 50.3000, 22.3000, 35, 85, 90),
('TRUCK_004', '2026-11-07 08:01:00+00', 50.3030, 22.3030, 0, 84, 90),
('TRUCK_004', '2026-11-07 08:02:00+00', 50.3030, 22.3030, 0, 84, 90),
('TRUCK_004', '2026-11-07 08:03:00+00', 50.3030, 22.3030, 0, 84, 90),

-- TRUCK_005: Telemetry gap
('TRUCK_005', '2026-11-07 08:00:00+00', 50.4000, 22.4000, 60, 75, 180),
('TRUCK_005', '2026-11-07 08:01:00+00', 50.4050, 22.4050, 65, 74, 182),
('TRUCK_005', '2026-11-07 08:10:00+00', 50.4100, 22.4100, 70, 73, 185)

ON CONFLICT (vehicle_id, timestamp) DO NOTHING;


-- =====================================================
-- 3. INSERT SAMPLE ETL RUN
-- =====================================================

INSERT INTO fleet.etl_runs (
    started_at,
    finished_at,
    status,
    total_records,
    valid_records,
    rejected_records,
    duplicate_records
)
SELECT
    '2026-11-07 08:00:00+00',
    '2026-11-07 08:15:00+00',
    'SUCCESS',
    20,
    20,
    0,
    0
WHERE NOT EXISTS (
    SELECT 1
    FROM fleet.etl_runs
    WHERE started_at = '2026-11-07 08:00:00+00'
      AND status = 'SUCCESS'
      AND error_message IS NULL
);

COMMIT;
