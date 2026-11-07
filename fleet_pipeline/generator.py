import random
import math
from datetime import datetime, timezone, timedelta


def generate_gps_event(vehicle_id: str) -> dict:

    timestamp = datetime.now(timezone.utc).isoformat()
    latitude = round(random.uniform(49.0, 54.0), 2)
    longitude = round(random.uniform(14.0, 24.0), 2)
    speed_kmh = round(random.uniform(0, 90.0), 2)
    fuel_level = round(random.uniform(10.0, 100.0), 2)

    return {
        "vehicle_id": vehicle_id,
        "timestamp": timestamp,
        "latitude": latitude,
        "longitude": longitude,
        "speed_kmh": speed_kmh,
        "fuel_level": fuel_level
    }


def generate_fleet_events(vehicle_ids: list[str]) -> list[dict]:

    vehicles = []

    for vehicle in vehicle_ids:
        event = generate_gps_event(vehicle)
        vehicles.append(event)

    return vehicles


def generate_timestamps(
    start_time: str,
    count: int,
    interval_seconds: int
) -> list[str]:

    if count <= 0:
        raise ValueError("Count must be positive")

    if interval_seconds <= 0:
        raise ValueError("Interval must be positive")

    start_datetime = datetime.fromisoformat(start_time)
    times = []

    for i in range(count):
        timestamp = start_datetime + timedelta(seconds=i * interval_seconds)
        times.append(timestamp.isoformat())

    return times


def generate_next_speed(
    current_speed: float,
    max_change: float = 5.0,
    max_speed: float = 120.0
) -> float:

    if current_speed < 0:
        raise ValueError("Speed cannot be negative")

    if max_change < 0:
        raise ValueError("Max change cannot be negative")

    if max_speed < 0:
        raise ValueError("Max speed cannot be negative")

    if current_speed > max_speed:
        raise ValueError("Current speed exceeds maximum")

    change = random.uniform(-max_change, max_change)
    new_speed = current_speed + change
    new_speed = max(0, min(max_speed, new_speed))

    return round(new_speed, 2)


def calculate_next_position(
    latitude: float,
    longitude: float,
    speed_kmh: float,
    heading_degrees: float,
    interval_seconds: int
) -> tuple[float, float]:

    if speed_kmh < 0:
        raise ValueError("Speed cannot be negative")

    if interval_seconds <= 0:
        raise ValueError("Interval must be positive")

    if latitude > 85 or latitude < -85:
        raise ValueError("Latitude out of range")

    if longitude > 180 or longitude < -180:
        raise ValueError("Longitude out of range")

    distance = speed_kmh * interval_seconds / 3600
    heading_radians = math.radians(heading_degrees)

    distance_north = distance * math.cos(heading_radians)
    distance_east = distance * math.sin(heading_radians)

    new_latitude = latitude + distance_north / 111.32
    new_longitude = longitude + distance_east / (111.32 * math.cos(math.radians(latitude)))

    if not -85 <= new_latitude <= 85:
        raise ValueError("New latitude out of range")

    if not -180 <= new_longitude <= 180:
        raise ValueError("New longitude out of range")

    return round(new_latitude, 6), round(new_longitude, 6)


def generate_next_heading(
    current_heading: float,
    max_turn: float = 10.0
) -> float:

    if current_heading < 0 or current_heading >= 360:
        raise ValueError("Heading out of range")

    if max_turn < 0:
        raise ValueError("Max turn cannot be negative")

    change = random.uniform(-max_turn, max_turn)
    new_heading = current_heading + change
    new_heading = new_heading % 360

    return round(new_heading, 2) % 360


def generate_vehicle_route(
    vehicle_id: str,
    start_latitude: float,
    start_longitude: float,
    start_speed: float,
    heading_degrees: float,
    start_time: str,
    count: int,
    interval_seconds: int
) -> list[dict]:

    timestamps = generate_timestamps(start_time, count, interval_seconds)

    current_latitude = start_latitude
    current_longitude = start_longitude
    current_speed = start_speed
    current_heading = heading_degrees

    current_fuel = 80.0
    consumption_per_100km = 28.0

    events = [{
        "vehicle_id": vehicle_id,
        "timestamp": timestamps[0],
        "latitude": current_latitude,
        "longitude": current_longitude,
        "speed_kmh": current_speed,
        "heading_degrees": current_heading,
        "fuel_level": round(current_fuel, 2)
    }]

    for i in range(1, count):

        distance_km = current_speed * interval_seconds / 3600
        consumed_fuel = distance_km * consumption_per_100km / 100

        current_fuel = current_fuel - consumed_fuel
        current_fuel = max(0, current_fuel)

        current_latitude, current_longitude = calculate_next_position(
            current_latitude,
            current_longitude,
            current_speed,
            current_heading,
            interval_seconds
        )

        current_speed = generate_next_speed(current_speed)
        current_heading = generate_next_heading(current_heading)

        event = {
            "vehicle_id": vehicle_id,
            "timestamp": timestamps[i],
            "latitude": current_latitude,
            "longitude": current_longitude,
            "speed_kmh": current_speed,
            "heading_degrees": current_heading,
            "fuel_level": round(current_fuel, 2)
        }

        events.append(event)

    return events


def generate_fleet_routes(
    vehicles: list[dict],
    start_time: str,
    count_per_vehicle: int,
    interval_seconds: int
) -> list[dict]:

    data = []

    if not vehicles:
        return []

    for vehicle in vehicles:
        vehicle_events = generate_vehicle_route(
            vehicle["vehicle_id"],
            vehicle["latitude"],
            vehicle["longitude"],
            vehicle["speed_kmh"],
            vehicle["heading_degrees"],
            start_time,
            count_per_vehicle,
            interval_seconds
        )
        data.extend(vehicle_events)

    return data


def inject_speed_anomaly(
    events: list[dict],
    index: int,
    new_speed: float
) -> list[dict]:

    if index < 0 or index >= len(events):
        raise IndexError("Invalid event index")

    if new_speed < 0:
        raise ValueError("Speed cannot be negative")

    new_data = []

    for event in events:
        new_data.append(event.copy())

    new_data[index]["speed_kmh"] = new_speed

    return new_data


def inject_vehicle_stop(
    events: list[dict],
    start_index: int,
    duration_events: int
) -> list[dict]:

    if start_index < 0 or start_index >= len(events):
        raise IndexError("Invalid event index")

    if duration_events <= 0:
        raise ValueError("Duration must be positive")

    if start_index + duration_events > len(events):
        raise IndexError("Stop goes beyond events")

    new_data = []

    for event in events:
        new_data.append(event.copy())

    for i in range(start_index, start_index + duration_events):
        new_data[i]["speed_kmh"] = 0.0

    return new_data
