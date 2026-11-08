
import json

from .database import get_database_connection
from .normalization import normalize_gps_batch
from .validators import validate_gps_records
from .repository import upsert_gps_batch


def run_db_pipeline(events: list[dict]) -> dict:

    # Step 1: Normalize GPS records
    normalized_events = normalize_gps_batch(events)

    # Step 2: Validate GPS records
    validation = validate_gps_records(normalized_events)

    valid_events = validation["valid"]
    rejected_events = validation["rejected"]

    # Step 3: Remove duplicate records
    seen = set()
    unique_events = []
    duplicate_count = 0

    for event in valid_events:

        key = (
            event["vehicle_id"],
            event["timestamp"]
        )

        if key in seen:
            duplicate_count += 1
        else:
            seen.add(key)
            unique_events.append(event)

    # Step 4: Save data in one transaction
    with get_database_connection() as connection:

        with connection.cursor() as cursor:

            # Create an ETL execution record
            cursor.execute(
                """
                INSERT INTO fleet.etl_runs (
                    status,
                    total_records
                )
                VALUES ('RUNNING', %s)
                RETURNING run_id
                """,
                (len(events),)
            )

            run_id = cursor.fetchone()[0]

            # Save rejected records
            for rejected in rejected_events:

                raw_data = rejected["record"]
                reasons = rejected["errors"]

                vehicle_id = raw_data.get("vehicle_id")

                cursor.execute(
                    """
                    INSERT INTO fleet.rejected_events (
                        run_id,
                        vehicle_id,
                        raw_data,
                        rejection_reasons
                    )
                    VALUES (
                        %s,
                        %s,
                        %s::jsonb,
                        %s::jsonb
                    )
                    """,
                    (
                        run_id,
                        vehicle_id,
                        json.dumps(raw_data, default=str),
                        json.dumps(reasons, default=str)
                    )
                )

        # Save valid GPS events
        batch_result = upsert_gps_batch(
            connection,
            unique_events
        )

        # Update ETL execution status
        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE fleet.etl_runs
                SET
                    finished_at = CURRENT_TIMESTAMP,
                    status = 'SUCCESS',
                    valid_records = %s,
                    rejected_records = %s,
                    duplicate_records = %s
                WHERE run_id = %s
                """,
                (
                    len(unique_events),
                    len(rejected_events),
                    duplicate_count,
                    run_id
                )
            )

    # Step 5: Return processing summary
    result = {
        "run_id": run_id,
        "status": "SUCCESS",
        "total_records": len(events),
        "valid_records": len(unique_events),
        "rejected_records": len(rejected_events),
        "duplicate_records": duplicate_count,
        "affected_events": batch_result["affected_events"],
        "unchanged_events": batch_result["unchanged_events"]
    }

    return result
