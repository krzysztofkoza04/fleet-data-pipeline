"""Create a realistic synthetic fleet dataset for Power BI demonstrations.

This script adds data to the existing fleet schema without deleting older rows.
Run it from the project root where .env contains PostgreSQL credentials.
"""

import math
import os
import random
from datetime import datetime, timedelta, timezone
from time import perf_counter

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


# Settings
TOTAL_GPS_EVENTS = 200_000
INVALID_EVENTS = 500
BATCH_SIZE = 1_000
RANDOM_SEED = 20261107

# Vehicle ID, registration, type, fuel tank size, active, event weight
VEHICLES = [
    ("IVECO_01", "RZ 101AA", "TRUCK", 380, True, 14),
    ("IVECO_02", "RZ 102AA", "TRUCK", 380, True, 12),
    ("IVECO_03", "RZ 103AA", "TRUCK", 380, False, 6),
    ("MAN_01", "RZ 201BB", "TRUCK", 600, True, 16),
    ("MAN_02", "RZ 202BB", "TRUCK", 600, True, 13),
    ("MAN_03", "RZ 203BB", "TRUCK", 600, False, 5),
    ("SCANIA_01", "RZ 301CC", "TRUCK", 650, True, 17),
    ("SCANIA_02", "RZ 302CC", "TRUCK", 650, True, 13),
    ("VOLVO_01", "RZ 401DD", "TRUCK", 600, True, 15),
    ("VOLVO_02", "RZ 402DD", "TRUCK", 600, False, 7),
    ("DAF_01", "RZ 501EE", "TRUCK", 550, True, 14),
    ("DAF_02", "RZ 502EE", "TRUCK", 550, True, 12),
    ("MERCEDES_01", "RZ 601FF", "VAN", 75, True, 11),
    ("MERCEDES_02", "RZ 602FF", "VAN", 75, True, 10),
    ("RENAULT_01", "RZ 701GG", "VAN", 80, True, 10),
    ("RENAULT_02", "RZ 702GG", "VAN", 80, False, 5),
    ("FORD_01", "RZ 801HH", "VAN", 80, True, 9),
    ("FORD_02", "RZ 802HH", "VAN", 80, True, 8),
    ("SKODA_01", "RZ 901JJ", "CAR", 55, True, 8),
    ("SKODA_02", "RZ 902JJ", "CAR", 55, False, 5),
]


# Use the same environment variables as the existing Python application.
def get_connection():
    load_dotenv()

    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    for name in required:
        if not os.getenv(name):
            raise ValueError(f"Missing .env setting: {name}")

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
    )


def allocate_event_counts(total_events):
    weights_sum = 0
    for vehicle in VEHICLES:
        weights_sum += vehicle[5]

    counts = []
    for vehicle in VEHICLES:
        count = total_events * vehicle[5] // weights_sum
        counts.append(count)

    remaining = total_events - sum(counts)
    index = 0
    while remaining > 0:
        counts[index] += 1
        remaining -= 1
        index += 1
        if index == len(counts):
            index = 0

    return counts


def register_vehicles(connection):
    query = """
        INSERT INTO fleet.vehicles (
            vehicle_id, registration_number, vehicle_type,
            fuel_capacity_liters, is_active
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (vehicle_id)
        DO UPDATE SET
            registration_number = EXCLUDED.registration_number,
            vehicle_type = EXCLUDED.vehicle_type,
            fuel_capacity_liters = EXCLUDED.fuel_capacity_liters,
            is_active = EXCLUDED.is_active
    """

    with connection.cursor() as cursor:
        for vehicle in VEHICLES:
            cursor.execute(query, vehicle[:5])


def generate_vehicle_events(vehicle, event_count, random_generator):
    vehicle_id = vehicle[0]
    vehicle_type = vehicle[2]
    tank_capacity = vehicle[3]
    is_active = vehicle[4]

    # Different vehicles begin and end their histories at different times.
    start_day = random_generator.randint(0, 9)
    current_time = datetime(2026, 10, 1, 6, tzinfo=timezone.utc)
    current_time += timedelta(days=start_day)

    latitude = 49.7 + random_generator.random() * 0.9
    longitude = 21.0 + random_generator.random() * 2.4
    heading = random_generator.uniform(0, 359)
    fuel_liters = tank_capacity * random_generator.uniform(0.67, 0.94)
    trip_minutes = 0
    idle_minutes = 0

    if vehicle_type == "TRUCK":
        typical_speed = random_generator.uniform(55, 75)
        fuel_per_100km = random_generator.uniform(25, 33)
    elif vehicle_type == "VAN":
        typical_speed = random_generator.uniform(40, 65)
        fuel_per_100km = random_generator.uniform(8, 12)
    else:
        typical_speed = random_generator.uniform(35, 60)
        fuel_per_100km = random_generator.uniform(5, 8)

    for index in range(event_count):
        # Most measurements occur every two minutes, with occasional gaps.
        interval_minutes = 2
        if random_generator.random() < 0.003:
            interval_minutes = random_generator.randint(12, 40)
        current_time += timedelta(minutes=interval_minutes)

        hour = current_time.hour
        is_night = hour < 5 or hour >= 22

        # Build realistic variation in driving and stopping periods.
        if trip_minutes <= 0 and idle_minutes <= 0:
            if is_night or random_generator.random() < 0.3:
                idle_minutes = random_generator.randint(10, 100)
            else:
                trip_minutes = random_generator.randint(30, 240)

        if idle_minutes > 0:
            speed = 0.0
            idle_minutes -= interval_minutes
        else:
            speed = max(5, random_generator.gauss(typical_speed, 13))
            trip_minutes -= interval_minutes

        max_normal_speed = 85 if vehicle_type == "TRUCK" else 110
        speed = min(speed, max_normal_speed)

        # A few valid records represent unusually high speeds.
        if speed > 0 and random_generator.random() < 0.004:
            speed = random_generator.uniform(105, 125)

        # Use distance travelled to update approximate GPS coordinates.
        distance_km = speed * interval_minutes / 60
        heading += random_generator.uniform(-8, 8)
        heading = heading % 360
        angle = math.radians(heading)
        latitude += math.cos(angle) * distance_km / 111
        longitude += math.sin(angle) * distance_km / 72

        # Keep the simulated vehicles within Poland-like coordinates.
        if latitude < 49.0 or latitude > 54.0:
            heading = (180 - heading) % 360
            latitude = min(54.0, max(49.0, latitude))
        if longitude < 18.0 or longitude > 24.0:
            heading = (360 - heading) % 360
            longitude = min(24.0, max(18.0, longitude))

        fuel_liters -= distance_km * fuel_per_100km / 100
        fuel_liters = max(0, fuel_liters)

        # Refuelling happens while the vehicle is stopped.
        if fuel_liters < tank_capacity * 0.2 and speed == 0:
            fuel_liters = tank_capacity * random_generator.uniform(0.85, 0.98)

        # An occasional missing fuel reading is allowed by the database.
        fuel_level = round(fuel_liters / tank_capacity * 100, 2)
        if random_generator.random() < 0.002:
            fuel_level = None

        event = (
            vehicle_id,
            current_time,
            round(latitude, 6),
            round(longitude, 6),
            round(speed, 2),
            fuel_level,
            round(heading, 2) % 360
        )
        yield event


def save_events(connection, run_id, random_generator):
    query = """
        INSERT INTO fleet.gps_events (
            vehicle_id, run_id, timestamp, latitude, longitude,
            speed_kmh, fuel_level, heading_degrees
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (vehicle_id, timestamp)
        DO UPDATE SET
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            speed_kmh = EXCLUDED.speed_kmh,
            fuel_level = EXCLUDED.fuel_level,
            heading_degrees = EXCLUDED.heading_degrees
        WHERE (
            gps_events.latitude, gps_events.longitude,
            gps_events.speed_kmh, gps_events.fuel_level,
            gps_events.heading_degrees
        ) IS DISTINCT FROM (
            EXCLUDED.latitude, EXCLUDED.longitude,
            EXCLUDED.speed_kmh, EXCLUDED.fuel_level,
            EXCLUDED.heading_degrees
        )
    """

    counts = allocate_event_counts(TOTAL_GPS_EVENTS)
    total_affected = 0
    all_vehicle_ids = []

    with connection.cursor() as cursor:
        for index in range(len(VEHICLES)):
            vehicle = VEHICLES[index]
            count = counts[index]
            all_vehicle_ids.append(vehicle[0])
            batch = []

            for event in generate_vehicle_events(vehicle, count, random_generator):
                row = (event[0], run_id) + event[1:]
                batch.append(row)

                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(query, batch)
                    total_affected += cursor.rowcount
                    batch = []

            if batch:
                cursor.executemany(query, batch)
                total_affected += cursor.rowcount

            print(f"  {vehicle[0]}: {count:,} generated events", flush=True)

    return total_affected, all_vehicle_ids


def save_rejected_events(connection, run_id):
    query = """
        INSERT INTO fleet.rejected_events (
            run_id, vehicle_id, raw_data, rejection_reasons
        )
        VALUES (%s, %s, %s, %s)
    """

    with connection.cursor() as cursor:
        for index in range(INVALID_EVENTS):
            vehicle_id = VEHICLES[index % len(VEHICLES)][0]

            if index % 4 == 0:
                raw_data = {"vehicle_id": vehicle_id, "speed_kmh": -20}
                reasons = ["Negative speed", "Missing timestamp"]
            elif index % 4 == 1:
                raw_data = {"vehicle_id": vehicle_id, "latitude": 120}
                reasons = ["Latitude outside valid range", "Missing timestamp"]
            elif index % 4 == 2:
                raw_data = {"vehicle_id": vehicle_id, "fuel_level": 140}
                reasons = ["Fuel level above 100 percent", "Missing timestamp"]
            else:
                raw_data = {"vehicle_id": vehicle_id, "timestamp": "invalid-date"}
                reasons = ["Invalid timestamp"]

            cursor.execute(
                query,
                (run_id, vehicle_id, Jsonb(raw_data), Jsonb(reasons)),
            )


def save_anomalies(connection, vehicle_ids):
    # Save speed violations as examples for the anomaly dashboard.
    query = """
        INSERT INTO fleet.fleet_anomalies (
            vehicle_id, event_id, run_id, anomaly_type, detected_at,
            anomaly_value, threshold_value, description
        )
        SELECT
            g.vehicle_id,
            g.event_id,
            g.run_id,
            'OVERSPEED',
            g.timestamp,
            g.speed_kmh,
            CASE WHEN v.vehicle_type = 'TRUCK' THEN 90 ELSE 100 END,
            'Synthetic overspeed event for demo reporting'
        FROM fleet.gps_events g
        JOIN fleet.vehicles v ON v.vehicle_id = g.vehicle_id
        WHERE g.vehicle_id = ANY(%s)
          AND g.speed_kmh > CASE
              WHEN v.vehicle_type = 'TRUCK' THEN 90 ELSE 100 END
          AND NOT EXISTS (
              SELECT 1
              FROM fleet.fleet_anomalies a
              WHERE a.event_id = g.event_id
                AND a.anomaly_type = 'OVERSPEED'
          )
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (vehicle_ids,))
        return cursor.rowcount


def update_daily_statistics(connection, vehicle_ids):
    # Recalculate daily KPIs from the raw GPS measurements.
    query = """
        WITH ordered_events AS (
            SELECT
                vehicle_id,
                (timestamp AT TIME ZONE 'UTC')::date AS report_date,
                timestamp,
                speed_kmh,
                fuel_level,
                LAG(timestamp) OVER (
                    PARTITION BY vehicle_id ORDER BY timestamp
                ) AS previous_timestamp,
                LAG(speed_kmh) OVER (
                    PARTITION BY vehicle_id ORDER BY timestamp
                ) AS previous_speed,
                LAG(fuel_level) OVER (
                    PARTITION BY vehicle_id ORDER BY timestamp
                ) AS previous_fuel
            FROM fleet.gps_events
            WHERE vehicle_id = ANY(%s)
        ),
        daily AS (
            SELECT
                vehicle_id,
                report_date,
                COUNT(*) AS event_count,
                ROUND(AVG(speed_kmh), 2) AS avg_speed_kmh,
                MAX(speed_kmh) AS max_speed_kmh,
                SUM(
                    CASE
                        WHEN speed_kmh < 1
                         AND previous_speed < 1
                         AND timestamp - previous_timestamp <= INTERVAL '5 minutes'
                        THEN EXTRACT(EPOCH FROM timestamp - previous_timestamp)
                        ELSE 0
                    END
                ) AS total_stop_seconds,
                ROUND(SUM(
                    CASE
                        WHEN previous_fuel IS NOT NULL
                         AND fuel_level IS NOT NULL
                         AND previous_fuel > fuel_level
                         AND previous_fuel - fuel_level < 20
                        THEN previous_fuel - fuel_level
                        ELSE 0
                    END
                ), 2) AS total_fuel_consumed_pct_points,
                COUNT(*) FILTER (
                    WHERE previous_fuel IS NOT NULL
                      AND fuel_level IS NOT NULL
                      AND fuel_level - previous_fuel > 10
                ) AS refueling_count
            FROM ordered_events
            GROUP BY vehicle_id, report_date
        )
        INSERT INTO fleet.daily_vehicle_stats (
            vehicle_id, report_date, event_count, avg_speed_kmh,
            max_speed_kmh, total_stop_seconds,
            total_fuel_consumed_pct_points, refueling_count, updated_at
        )
        SELECT
            vehicle_id, report_date, event_count, avg_speed_kmh,
            max_speed_kmh, total_stop_seconds,
            total_fuel_consumed_pct_points, refueling_count, CURRENT_TIMESTAMP
        FROM daily
        ON CONFLICT (vehicle_id, report_date)
        DO UPDATE SET
            event_count = EXCLUDED.event_count,
            avg_speed_kmh = EXCLUDED.avg_speed_kmh,
            max_speed_kmh = EXCLUDED.max_speed_kmh,
            total_stop_seconds = EXCLUDED.total_stop_seconds,
            total_fuel_consumed_pct_points = EXCLUDED.total_fuel_consumed_pct_points,
            refueling_count = EXCLUDED.refueling_count,
            updated_at = CURRENT_TIMESTAMP
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (vehicle_ids,))
        return cursor.rowcount


def main():
    start = perf_counter()
    random_generator = random.Random(RANDOM_SEED)

    print("Creating a demo fleet with 20 vehicles and 200,000 GPS events...")
    print("Existing vehicles and benchmark data will NOT be deleted.")

    with get_connection() as connection:
        register_vehicles(connection)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO fleet.etl_runs (status, total_records)
                VALUES ('RUNNING', %s)
                RETURNING run_id
                """,
                (TOTAL_GPS_EVENTS + INVALID_EVENTS,),
            )
            run_id = cursor.fetchone()[0]

        affected, vehicle_ids = save_events(connection, run_id, random_generator)
        save_rejected_events(connection, run_id)
        anomalies = save_anomalies(connection, vehicle_ids)
        daily_rows = update_daily_statistics(connection, vehicle_ids)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE fleet.etl_runs
                SET status = 'SUCCESS',
                    finished_at = CURRENT_TIMESTAMP,
                    valid_records = %s,
                    rejected_records = %s,
                    duplicate_records = 0
                WHERE run_id = %s
                """,
                (TOTAL_GPS_EVENTS, INVALID_EVENTS, run_id),
            )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM fleet.gps_events
                WHERE vehicle_id = ANY(%s)
                """,
                (vehicle_ids,),
            )
            stored = cursor.fetchone()[0]

        if stored != TOTAL_GPS_EVENTS:
            raise ValueError(
                f"Expected {TOTAL_GPS_EVENTS} demo GPS events, found {stored}"
            )

    duration = perf_counter() - start
    print("\nDONE")
    print(f"Demo vehicles: {len(VEHICLES)}")
    print(f"GPS events in demo fleet: {stored:,}")
    print(f"Inserted or updated GPS events: {affected:,}")
    print(f"Rejected test records: {INVALID_EVENTS:,}")
    print(f"New overspeed anomalies: {anomalies:,}")
    print(f"Daily KPI rows refreshed: {daily_rows:,}")
    print(f"ETL run ID: {run_id}")
    print(f"Total execution time: {duration:.2f} s")


if __name__ == "__main__":
    main()
