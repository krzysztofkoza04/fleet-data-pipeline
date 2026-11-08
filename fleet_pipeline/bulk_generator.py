
from datetime import datetime, timedelta, timezone


def generate_bulk_gps_events(
    vehicle_ids: list[str],
    events_per_vehicle: int
) -> list[dict]:

    if events_per_vehicle <= 0:
        raise ValueError("Events per vehicle must be greater than 0")

    events = []

    start_time = datetime(
        2026, 11, 7, 8, 0, 0,
        tzinfo=timezone.utc
    )

    for vehicle_id in vehicle_ids:

        for i in range(events_per_vehicle):

            # Generate timestamp
            timestamp = start_time + timedelta(minutes=i)

            # Generate synthetic telemetry values
            speed_kmh = 40 + (i % 40)

            latitude = 50.0 + (i % 10000) * 0.00001
            longitude = 22.0 + (i % 10000) * 0.00001

            fuel_level = 90 - (i % 1000) * 0.005

            heading_degrees = 90.0

            # Create GPS event
            event = {
                "vehicle_id": vehicle_id,
                "timestamp": timestamp.isoformat(),
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "speed_kmh": round(speed_kmh, 2),
                "fuel_level": round(fuel_level, 2),
                "heading_degrees": heading_degrees
            }

            events.append(event)

    return events
