
-- ============================================
-- FLEET DATA PIPELINE
-- 02_seed.sql
-- Initial data for testing PostgreSQL
-- ============================================

BEGIN;

-- 1. Vehicles

INSERT INTO fleet.vehicles (
    vehicle_id,
    registration_number,
    vehicle_type,
    fuel_capacity_liters
)
VALUES
    ('TRUCK_001', 'RZ10001', 'Volvo FH', 600),
    ('TRUCK_002', 'RZ10002', 'Scania R450', 500),
    ('TRUCK_003', 'RZ10003', 'MAN TGX', 550)
ON CONFLICT (vehicle_id) DO NOTHING;


-- 2. Gps measurements

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
    ('TRUCK_001', '2026-11-07 08:00:00+00', 50.0413, 21.9990, 60, 80, 90),
    ('TRUCK_001', '2026-11-07 08:01:00+00', 50.0450, 22.0030, 65, 79, 92),
    ('TRUCK_001', '2026-11-07 08:02:00+00', 50.0490, 22.0080, 70, 78, 95),

    ('TRUCK_002', '2026-11-07 08:00:00+00', 50.1000, 22.1000, 50, 90, 180),
    ('TRUCK_002', '2026-11-07 08:01:00+00', 50.1050, 22.1050, 55, 89, 182),
    ('TRUCK_002', '2026-11-07 08:02:00+00', 50.1100, 22.1100, 60, 88, 185),

    ('TRUCK_003', '2026-11-07 08:00:00+00', 50.2000, 22.2000, 40, 70, 270),
    ('TRUCK_003', '2026-11-07 08:01:00+00', 50.2050, 22.2050, 45, 69, 272),
    ('TRUCK_003', '2026-11-07 08:02:00+00', 50.2100, 22.2100, 50, 68, 275)
ON CONFLICT (vehicle_id, timestamp) DO NOTHING;

COMMIT;
