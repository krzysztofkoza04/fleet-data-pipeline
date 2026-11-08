
import psycopg


# =====================================================
# 1. UPSERT VEHICLE
# =====================================================

def upsert_vehicle(
    connection: psycopg.Connection,
    vehicle: dict
) -> int:

    query = """
        INSERT INTO fleet.vehicles (
            vehicle_id,
            registration_number,
            vehicle_type,
            fuel_capacity_liters,
            is_active
        )
        VALUES (%s, %s, %s, %s, %s)

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
        )
    """

    values = (
        vehicle["vehicle_id"],
        vehicle["registration_number"],
        vehicle["vehicle_type"],
        vehicle["fuel_capacity_liters"],
        vehicle["is_active"]
    )

    with connection.cursor() as cursor:
        cursor.execute(query, values)
        affected_rows = cursor.rowcount

    return affected_rows


# =====================================================
# 2. GET VEHICLE BY ID
# =====================================================

def get_vehicle_by_id(
    connection: psycopg.Connection,
    vehicle_id: str
) -> dict | None:

    query = """
        SELECT
            vehicle_id,
            registration_number,
            vehicle_type,
            fuel_capacity_liters,
            is_active
        FROM fleet.vehicles
        WHERE vehicle_id = %s
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (vehicle_id,))
        result = cursor.fetchone()

    if result is None:
        return None

    vehicle = {
        "vehicle_id": result[0],
        "registration_number": result[1],
        "vehicle_type": result[2],
        "fuel_capacity_liters": result[3],
        "is_active": result[4]
    }

    return vehicle


# =====================================================
# 3. UPSERT GPS EVENT
# =====================================================

def upsert_gps_event(
    connection: psycopg.Connection,
    event: dict
) -> int:

    query = """
        INSERT INTO fleet.gps_events (
            vehicle_id,
            timestamp,
            latitude,
            longitude,
            speed_kmh,
            fuel_level,
            heading_degrees
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)

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
        )
    """

    values = (
        event["vehicle_id"],
        event["timestamp"],
        event["latitude"],
        event["longitude"],
        event["speed_kmh"],
        event.get("fuel_level"),
        event.get("heading_degrees")
    )

    with connection.cursor() as cursor:
        cursor.execute(query, values)
        affected_rows = cursor.rowcount

    return affected_rows


# =====================================================
# 4. UPSERT GPS BATCH
# =====================================================

def upsert_gps_batch(
    connection: psycopg.Connection,
    events: list[dict]
) -> dict:

    total_events = len(events)
    affected_events = 0

    for event in events:

        affected_rows = upsert_gps_event(
            connection,
            event
        )

        affected_events += affected_rows

    unchanged_events = total_events - affected_events

    result = {
        "total_events": total_events,
        "affected_events": affected_events,
        "unchanged_events": unchanged_events
    }

    return result
