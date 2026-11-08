
import time
import uuid

from fleet_pipeline.database import get_database_connection
from fleet_pipeline.repository import (
    upsert_vehicle,
    upsert_gps_batch
)
from fleet_pipeline.bulk_generator import generate_bulk_gps_events
from fleet_pipeline.bulk_loader import bulk_upsert_gps_events


def create_benchmark_vehicles(connection):

    # Create a unique ID for this benchmark
    test_id = uuid.uuid4().hex[:8]

    vehicle_ids = []

    for i in range(1, 11):

        vehicle_id = f"BENCH_{test_id}_{i:02d}"

        vehicle = {
            "vehicle_id": vehicle_id,
            "registration_number": f"B-{test_id}-{i:02d}",
            "vehicle_type": "TRUCK",
            "fuel_capacity_liters": 500,
            "is_active": True
        }

        upsert_vehicle(connection, vehicle)

        vehicle_ids.append(vehicle_id)

    return vehicle_ids


def count_benchmark_events(connection, vehicle_ids):

    query = """
        SELECT COUNT(*)
        FROM fleet.gps_events
        WHERE vehicle_id = ANY(%s)
    """

    with connection.cursor() as cursor:

        cursor.execute(query, (vehicle_ids,))

        result = cursor.fetchone()

    return result[0]


def run_benchmark(total_records, method):

    print()
    print("=" * 45)
    print("Records:", total_records)
    print("Method:", method)

    with get_database_connection() as connection:

        # Create vehicles before inserting GPS data
        vehicle_ids = create_benchmark_vehicles(connection)

        events_per_vehicle = total_records // len(vehicle_ids)

        # Generate synthetic GPS data
        events = generate_bulk_gps_events(
            vehicle_ids,
            events_per_vehicle
        )

        # Measure database loading time
        start_time = time.perf_counter()

        if method == "single":

            affected_events = upsert_gps_batch(
                connection,
                events
            )["affected_events"]

        elif method == "batch":

            affected_events = bulk_upsert_gps_events(
                connection,
                events,
                batch_size=1000
            )

        else:
            raise ValueError("Unknown loading method")

        # Measure the INSERT/UPSERT execution
        end_time = time.perf_counter()

        loading_time = end_time - start_time

        # Check the records in the same transaction
        database_count = count_benchmark_events(
            connection,
            vehicle_ids
        )

        if database_count != len(events):
            raise ValueError("Incorrect number of saved events")

        if affected_events != len(events):
            raise ValueError("Not all generated events were inserted")

    # Calculate performance
    records_per_second = len(events) / loading_time

    print("Generated:", len(events))
    print("Affected rows:", affected_events)
    print("Saved in DB:", database_count)
    print("Loading time:", round(loading_time, 3), "s")
    print("Speed:", round(records_per_second), "records/s")

    result = {
        "records": len(events),
        "method": method,
        "seconds": loading_time,
        "records_per_second": records_per_second
    }

    return result


def main():

    results = []

    # Compare both methods on smaller datasets
    results.append(run_benchmark(1000, "single"))
    results.append(run_benchmark(1000, "batch"))

    results.append(run_benchmark(10000, "single"))
    results.append(run_benchmark(10000, "batch"))

    # Test the larger dataset using batch loading
    results.append(run_benchmark(50000, "batch"))

    print()
    print("=" * 55)
    print("FINAL BENCHMARK RESULTS")
    print("=" * 55)

    for result in results:

        print(
            result["records"],
            "records |",
            result["method"],
            "|",
            round(result["seconds"], 3),
            "s |",
            round(result["records_per_second"]),
            "records/s"
        )


if __name__ == "__main__":
    main()
