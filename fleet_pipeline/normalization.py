
def normalize_gps_event(event: dict) -> dict:

    vehicle_id = event.get("vehicle_id")
    speed_kmh = event.get("speed_kmh")
    latitude = event.get("latitude")
    longitude = event.get("longitude")

    if vehicle_id is None:
        vehicle_id = event.get("truck_id")

    if speed_kmh is None:
        speed_kmh = event.get("speed")

    if latitude is None:
        latitude = event.get("lat")

    if longitude is None:
        longitude = event.get("lon")

    fuel_level = event.get("fuel_level")
    heading_degrees = event.get("heading_degrees")
    timestamp = event.get("timestamp")

    normalized_event = {
        "vehicle_id": vehicle_id,
        "timestamp": timestamp,
        "speed_kmh": speed_kmh,
        "latitude": latitude,
        "longitude": longitude,
        "fuel_level": fuel_level,
        "heading_degrees": heading_degrees
    }

    return normalized_event


def normalize_gps_batch(events: list[dict]) -> list[dict]:

    normalized_events = []

    for event in events:

        normalized_data = normalize_gps_event(event)

        normalized_events.append(normalized_data)

    return normalized_events
