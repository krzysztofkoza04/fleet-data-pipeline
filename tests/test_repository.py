
from fleet_pipeline.database import get_database_connection
from fleet_pipeline.repository import (
    upsert_vehicle,
    get_vehicle_by_id,
    upsert_gps_event,
    upsert_gps_batch
)


def create_test_vehicle():

    vehicle = {
        "vehicle_id": "TRUCK_TEST_001",
        "registration_number": "TEST001",
        "vehicle_type": "Test Truck",
        "fuel_capacity_liters": 500,
        "is_active": True
    }

    return vehicle


def create_test_event():

    event = {
        "vehicle_id": "TRUCK_TEST_001",
        "timestamp": "2026-11-07T10:00:00+00:00",
        "latitude": 50.05,
        "longitude": 22.01,
        "speed_kmh": 50,
        "fuel_level": 80,
        "heading_degrees": 90
    }

    return event


# Test 1 - Insert or update a vehicle
def test_upsert_vehicle():

    vehicle = create_test_vehicle()

    with get_database_connection() as connection:

        upsert_vehicle(connection, vehicle)

        result = get_vehicle_by_id(
            connection,
            "TRUCK_TEST_001"
        )

        assert result is not None
        assert result["vehicle_id"] == "TRUCK_TEST_001"


# Test 2 - Read vehicle data
def test_get_vehicle_by_id():

    with get_database_connection() as connection:

        result = get_vehicle_by_id(
            connection,
            "TRUCK_TEST_001"
        )

        assert result["vehicle_type"] == "Test Truck"


# Test 3 - Save GPS event
def test_upsert_gps_event():

    event = create_test_event()

    with get_database_connection() as connection:

        upsert_gps_event(connection, event)

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM fleet.gps_events
                WHERE vehicle_id = %s
                """,
                ("TRUCK_TEST_001",)
            )

            count = cursor.fetchone()[0]

        assert count >= 1


# Test 4 - Idempotent GPS batch
def test_upsert_gps_batch():

    event = create_test_event()

    with get_database_connection() as connection:

        result = upsert_gps_batch(
            connection,
            [event]
        )

        assert result["total_events"] == 1
        assert result["unchanged_events"] == 1
