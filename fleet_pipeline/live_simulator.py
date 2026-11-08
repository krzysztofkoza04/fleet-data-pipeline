"""Generate live GPS batches and monitor ETL executions in PostgreSQL.

Run from the project root:
    python -m fleet_pipeline.live_simulator

This is a demonstration runner. It uses real PostgreSQL transactions,
while keeping the generation and validation logic intentionally simple.
"""

import json
import random
import time
from datetime import datetime, timedelta, timezone

from .database import get_database_connection

VALID_EVENTS_PER_RUN = 200
INVALID_EVENTS_PER_RUN = 5
RUNNING_SECONDS = 6
PAUSE_SECONDS = 4
FAIL_EVERY = 8


def get_active_vehicles():
    """Get existing active vehicles. Do not register new vehicles."""
    query = """
                    SELECT vehicle_id, vehicle_type
                    FROM fleet.vehicles
                    WHERE is_active = TRUE
                      AND vehicle_id NOT LIKE 'BENCH_%'
                    ORDER BY vehicle_id
                """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            vehicles = cursor.fetchall()

    return vehicles


def generate_events(vehicles):
    """Create new valid telemetry and a few intentionally invalid records."""
    events = []
    now = datetime.now(timezone.utc)

    for i in range(VALID_EVENTS_PER_RUN):
        vehicle_id, vehicle_type = vehicles[i % len(vehicles)]

        if vehicle_type == "TRUCK":
            speed = random.uniform(0, 105)
        else:
            speed = random.uniform(0, 125)

        # Simulated accelerated telemetry: multiple events per second.
        timestamp = now - timedelta(seconds=i % 30)
        timestamp = timestamp + timedelta(microseconds=i)

        event = {
            "vehicle_id": vehicle_id,
            "timestamp": timestamp,
            "latitude": round(random.uniform(49.5, 50.8), 6),
            "longitude": round(random.uniform(20.5, 23.1), 6),
            "speed_kmh": round(speed, 2),
            "fuel_level": round(random.uniform(15, 95), 2),
            "heading_degrees": round(random.uniform(0, 360), 2) % 360,
        }

        events.append(event)

    # Add invalid records so the quarantine table is updated in every run.
    for i in range(INVALID_EVENTS_PER_RUN):
        invalid = events[i].copy()

        if i == 0:
            invalid["speed_kmh"] = -15
        elif i == 1:
            invalid["latitude"] = 120
        elif i == 2:
            invalid["fuel_level"] = 140
        elif i == 3:
            invalid["heading_degrees"] = 360
        else:
            invalid["timestamp"] = None

        events.append(invalid)

    random.shuffle(events)
    return events


def validate_event(event):
    """Return a list of reasons why the GPS event is invalid."""
    errors = []

    if not isinstance(event.get("timestamp"), datetime):
        errors.append("Invalid timestamp")

    latitude = event.get("latitude")
    if latitude is None or not -90 <= latitude <= 90:
        errors.append("Latitude outside valid range")

    longitude = event.get("longitude")
    if longitude is None or not -180 <= longitude <= 180:
        errors.append("Longitude outside valid range")

    speed = event.get("speed_kmh")
    if speed is None or not 0 <= speed <= 180:
        errors.append("Speed outside valid range")

    fuel = event.get("fuel_level")
    if fuel is not None and not 0 <= fuel <= 100:
        errors.append("Fuel outside valid range")

    heading = event.get("heading_degrees")
    if heading is not None and not 0 <= heading < 360:
        errors.append("Heading outside valid range")

    return errors


def start_run(total_records):
    """Commit RUNNING immediately so Grafana can see the execution."""
    query = """
                    INSERT INTO fleet.etl_runs (status, total_records)
                    VALUES ('RUNNING', %s)
                    RETURNING run_id
                """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (total_records,))
            run_id = cursor.fetchone()[0]

    return run_id


def save_successful_run(run_id, events, fail_this_run):
    """Validate, load, and finish the ETL run within one transaction."""
    valid_events = []
    rejected_events = []
    seen = set()
    duplicate_count = 0

    for event in events:
        errors = validate_event(event)

        if errors:
            rejected_events.append((event, errors))
            continue

        key = (event["vehicle_id"], event["timestamp"])
        if key in seen:
            duplicate_count += 1
        else:
            seen.add(key)
            valid_events.append(event)

    insert_sql = """
                    INSERT INTO fleet.gps_events (
                        vehicle_id, run_id, timestamp, latitude, longitude,
                        speed_kmh, fuel_level, heading_degrees
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (vehicle_id, timestamp) DO NOTHING
                """

    rejected_sql = """
                    INSERT INTO fleet.rejected_events (
                        run_id, vehicle_id, raw_data, rejection_reasons
                    )
                    VALUES (%s, %s, %s::jsonb, %s::jsonb)
                """

    rows = []
    for event in valid_events:
        row = (
            event["vehicle_id"],
            run_id,
            event["timestamp"],
            event["latitude"],
            event["longitude"],
            event["speed_kmh"],
            event["fuel_level"],
            event["heading_degrees"],
        )
        rows.append(row)

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(insert_sql, rows)
            inserted_count = cursor.rowcount

            # Duplicates already present in the database are not inserted.
            duplicate_count += len(valid_events) - inserted_count

            for event, errors in rejected_events:
                cursor.execute(
                    rejected_sql,
                    (
                        run_id,
                        event.get("vehicle_id"),
                        json.dumps(event, default=str),
                        json.dumps(errors),
                    ),
                )

            # Demonstrate rollback and FAILED status every few runs.
            if fail_this_run:
                raise RuntimeError("Simulated database loading failure")

            cursor.execute(
                """
                UPDATE fleet.etl_runs
                SET status = 'SUCCESS',
                    finished_at = CURRENT_TIMESTAMP,
                    valid_records = %s,
                    rejected_records = %s,
                    duplicate_records = %s
                WHERE run_id = %s
                """,
                (
                    len(valid_events),
                    len(rejected_events),
                    duplicate_count,
                    run_id,
                ),
            )

    return inserted_count, len(rejected_events), duplicate_count


def mark_failed(run_id, message):
    """Keep the failed run in history after the data transaction rolls back."""
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE fleet.etl_runs
                SET status = 'FAILED',
                    finished_at = CURRENT_TIMESTAMP,
                    error_message = %s
                WHERE run_id = %s
                """,
                (message[:1000], run_id),
            )


def run_one_cycle(vehicles, cycle_number):
    events = generate_events(vehicles)
    run_id = start_run(len(events))
    print(f"Run {run_id}: RUNNING ({len(events)} records)", flush=True)

    try:
        # Keep RUNNING visible long enough for a 5-second Grafana refresh.
        time.sleep(RUNNING_SECONDS)

        fail_this_run = cycle_number % FAIL_EVERY == 0
        inserted, rejected, duplicates = save_successful_run(
            run_id,
            events,
            fail_this_run,
        )

        print(
            f"Run {run_id}: SUCCESS | inserted={inserted}, "
            f"rejected={rejected}, duplicates={duplicates}",
            flush=True,
        )

    except KeyboardInterrupt:
        mark_failed(run_id, "Simulation interrupted by user")
        raise

    except Exception as error:
        mark_failed(run_id, str(error))
        print(f"Run {run_id}: FAILED | {error}", flush=True)


def main():
    vehicles = get_active_vehicles()

    if not vehicles:
        raise ValueError("No active vehicles found in fleet.vehicles")

    print(f"Live simulator started. Active vehicles: {len(vehicles)}")
    print("Press Ctrl+C to stop. No existing GPS records are deleted.")

    cycle_number = 1

    try:
        while True:
            run_one_cycle(vehicles, cycle_number)
            cycle_number += 1
            time.sleep(PAUSE_SECONDS)
    except KeyboardInterrupt:
        print("\nLive simulator stopped.")


if __name__ == "__main__":
    main()
