
import psycopg


def bulk_upsert_gps_events(
    connection: psycopg.Connection,
    events: list[dict],
    batch_size: int = 1000
) -> int:

    if batch_size <= 0:
        raise ValueError("Batch size must be greater than 0")

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

    affected_events = 0

    for start in range(0, len(events), batch_size):

        # Get one batch of GPS events
        batch = events[start:start + batch_size]

        values = []

        for event in batch:

            row = (
                event["vehicle_id"],
                event["timestamp"],
                event["latitude"],
                event["longitude"],
                event["speed_kmh"],
                event.get("fuel_level"),
                event.get("heading_degrees")
            )

            values.append(row)

        # Save the batch to PostgreSQL
        with connection.cursor() as cursor:

            cursor.executemany(query, values)

            affected_events += cursor.rowcount

    return affected_events
