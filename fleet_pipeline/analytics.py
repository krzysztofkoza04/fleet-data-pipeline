import math
from datetime import datetime


# 1. Group GPS events by vehicle
def group_events_by_vehicle(events: list[dict]) -> dict:
    data = {}

    for event in events:
        vehicle_id = event["vehicle_id"]

        if vehicle_id not in data:
            data[vehicle_id] = []

        data[vehicle_id].append(event)

    return data


# 2. Calculate KPIs for a single vehicle
def calculate_vehicle_stats(events: list[dict]) -> dict:
    if not events:
        return {}

    events_count = len(events)
    max_speed = 0
    sum_of_speed = 0

    for event in events:
        speed = event["speed_kmh"]
        sum_of_speed += speed

        if speed > max_speed:
            max_speed = speed

    latest_event = max(events, key=lambda event: event["timestamp"])
    last_fuel_level = latest_event.get("fuel_level")
    avg_speed = round(sum_of_speed / events_count, 2)

    return {
        "vehicle_id": events[0]["vehicle_id"],
        "event_count": events_count,
        "avg_speed_kmh": avg_speed,
        "max_speed_kmh": max_speed,
        "last_fuel_level": last_fuel_level
    }


# 3. Calculate distance between two GPS coordinates
def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    lat_diff = lat2 - lat1
    lon_diff = lon2 - lon1
    radius = 6371

    a = (
        math.sin(lat_diff / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(lon_diff / 2) ** 2
    )

    a = max(0.0, min(1.0, a))
    distance = 2 * radius * math.asin(math.sqrt(a))

    return round(distance, 2)


# 4. Calculate total GPS distance
def calculate_total_distance(events: list[dict]) -> float:
    if len(events) < 2:
        return 0.0

    sorted_events = sorted(events, key=lambda event: event["timestamp"])
    sum_of_distance = 0.0

    for i in range(len(sorted_events) - 1):
        first = sorted_events[i]
        second = sorted_events[i + 1]

        distance = haversine_distance(
            first["latitude"],
            first["longitude"],
            second["latitude"],
            second["longitude"]
        )
        sum_of_distance += distance

    return round(sum_of_distance, 2)


# 5. Detect large speed changes
def detect_speed_anomalies(
    events: list[dict],
    threshold: float = 50.0
) -> list[dict]:
    anomalies = []

    if len(events) < 2:
        return anomalies

    sorted_events = sorted(events, key=lambda event: event["timestamp"])

    for i in range(len(sorted_events) - 1):
        first = sorted_events[i]
        second = sorted_events[i + 1]
        speed_diff = abs(first["speed_kmh"] - second["speed_kmh"])

        if speed_diff > threshold:
            anomalies.append(second)

    return anomalies


# 6. Calculate acceleration between two events
def calculate_acceleration(event_1: dict, event_2: dict) -> float:
    time_1 = datetime.fromisoformat(event_1["timestamp"])
    time_2 = datetime.fromisoformat(event_2["timestamp"])
    seconds = (time_2 - time_1).total_seconds()

    if seconds <= 0:
        raise ValueError("Time difference must be positive")

    speed_1_ms = event_1["speed_kmh"] / 3.6
    speed_2_ms = event_2["speed_kmh"] / 3.6
    acceleration = (speed_2_ms - speed_1_ms) / seconds

    return round(acceleration, 2)


# 7. Remove duplicate timestamps (for a single vehicle)
def remove_duplicate_timestamps(events: list[dict]) -> list[dict]:
    seen = set()
    data = []

    for event in events:
        timestamp = event["timestamp"]

        if timestamp not in seen:
            data.append(event)
            seen.add(timestamp)

    return data


# 8. Detect unusual acceleration or braking
def detect_acceleration_anomalies(
    events: list[dict],
    threshold: float = 3.0
) -> list[dict]:
    anomalies = []

    if len(events) < 2:
        return anomalies

    deduplicated_events = remove_duplicate_timestamps(events)

    if len(deduplicated_events) < 2:
        return anomalies

    sorted_events = sorted(deduplicated_events, key=lambda event: event["timestamp"])

    for i in range(len(sorted_events) - 1):
        first = sorted_events[i]
        second = sorted_events[i + 1]
        acceleration = calculate_acceleration(first, second)

        if abs(acceleration) > threshold:
            anomalies.append(second)

    return anomalies


# 9. Generate reports for all vehicles
def generate_fleet_report(events: list[dict]) -> list[dict]:
    grouped_events = group_events_by_vehicle(events)
    data = []

    for vehicle_id, vehicle_events in grouped_events.items():
        vehicle_stats = calculate_vehicle_stats(vehicle_events)
        vehicle_distance = calculate_total_distance(vehicle_events)
        anomalies = detect_acceleration_anomalies(vehicle_events)
        stop_seconds = calculate_vehicle_stops(vehicle_events)

        vehicle_stats["total_distance_km"] = vehicle_distance
        vehicle_stats["acceleration_anomalies_count"] = len(anomalies)
        vehicle_stats["total_stop_seconds"] = stop_seconds
        data.append(vehicle_stats)

    return data


# 10. Calculate total stopped time for one vehicle
def calculate_vehicle_stops(events: list[dict]) -> float:
    if len(events) < 2:
        return 0.0

    sorted_events = sorted(events, key=lambda event: event["timestamp"])
    time_of_stoppage = 0.0

    for i in range(len(sorted_events) - 1):
        first = sorted_events[i]
        second = sorted_events[i + 1]

        if first["speed_kmh"] == 0 and second["speed_kmh"] == 0:
            time_1 = datetime.fromisoformat(first["timestamp"])
            time_2 = datetime.fromisoformat(second["timestamp"])
            difference = (time_2 - time_1).total_seconds()

            if difference > 0:
                time_of_stoppage += difference

    return time_of_stoppage


# 11. Calculate summary KPIs for the fleet
def calculate_fleet_summary(reports: list[dict]) -> dict:
    if not reports:
        return {}

    total_vehicles = len(reports)
    total_events = 0
    total_distance_km = 0.0
    total_anomalies = 0
    total_stop_seconds = 0.0
    max_speed_kmh = 0.0
    sum_weighted_speed = 0.0

    for report in reports:
        event_count = report["event_count"]
        total_events += event_count
        total_distance_km += report["total_distance_km"]
        total_anomalies += report["acceleration_anomalies_count"]
        total_stop_seconds += report["total_stop_seconds"]
        sum_weighted_speed += report["avg_speed_kmh"] * event_count

        if report["max_speed_kmh"] > max_speed_kmh:
            max_speed_kmh = report["max_speed_kmh"]

    if total_events > 0:
        avg_speed_kmh = round(sum_weighted_speed / total_events, 2)
    else:
        avg_speed_kmh = 0.0

    return {
        "total_vehicles": total_vehicles,
        "total_events": total_events,
        "total_distance_km": round(total_distance_km, 2),
        "avg_speed_kmh": avg_speed_kmh,
        "max_speed_kmh": max_speed_kmh,
        "total_anomalies": total_anomalies,
        "total_stop_seconds": total_stop_seconds
    }


# 12. Calculate fuel used for a distance
def calculate_fuel_consumption(
    distance_km: float,
    consumption_per_100km: float
) -> float:
    if distance_km < 0:
        raise ValueError("Distance cannot be negative")

    if consumption_per_100km < 0:
        raise ValueError("Consumption cannot be negative")

    fuel_consumption = distance_km * consumption_per_100km / 100
    return round(fuel_consumption, 2)


# 13. Update fuel level after travelling
def update_fuel_level(
    current_fuel: float,
    distance_km: float,
    consumption_per_100km: float
) -> float:
    if current_fuel < 0:
        raise ValueError("Fuel cannot be negative")

    consumed_fuel = calculate_fuel_consumption(distance_km, consumption_per_100km)
    remaining_fuel = current_fuel - consumed_fuel
    remaining_fuel = max(0.0, remaining_fuel)

    return round(remaining_fuel, 2)


# 14. Detect sudden drops in fuel level (single vehicle)
def detect_fuel_anomalies(
    events: list[dict],
    threshold: float = 10.0
) -> list[dict]:
    if threshold < 0:
        raise ValueError("Threshold cannot be negative")

    anomalies = []

    if len(events) < 2:
        return anomalies

    sorted_events = sorted(events, key=lambda event: event["timestamp"])

    for i in range(len(sorted_events) - 1):
        first = sorted_events[i]
        second = sorted_events[i + 1]
        first_fuel = first.get("fuel_level")
        second_fuel = second.get("fuel_level")

        if first_fuel is None or second_fuel is None:
            continue

        fuel_drop = first_fuel - second_fuel

        if fuel_drop > threshold:
            anomalies.append(second)

    return anomalies


# 15. Detect impossible GPS movements (single vehicle)
def detect_gps_jumps(
    events: list[dict],
    max_speed_kmh: float = 150.0
) -> list[dict]:
    if max_speed_kmh <= 0:
        raise ValueError("Max speed must be positive")

    anomalies = []

    if len(events) < 2:
        return anomalies

    sorted_events = sorted(events, key=lambda event: event["timestamp"])

    for i in range(len(sorted_events) - 1):
        first = sorted_events[i]
        second = sorted_events[i + 1]

        distance = haversine_distance(
            first["latitude"],
            first["longitude"],
            second["latitude"],
            second["longitude"]
        )

        time_1 = datetime.fromisoformat(first["timestamp"])
        time_2 = datetime.fromisoformat(second["timestamp"])
        seconds = (time_2 - time_1).total_seconds()

        if seconds <= 0:
            continue

        speed = distance / seconds * 3600

        if speed > max_speed_kmh:
            anomalies.append(second)

    return anomalies


# 16. Detect events with low fuel
def detect_low_fuel(
    events: list[dict],
    threshold: float = 30.0
) -> list[dict]:
    if threshold < 0:
        raise ValueError("Threshold cannot be negative")

    low_fuel_records = []

    for event in events:
        fuel_level = event.get("fuel_level")

        if fuel_level is None:
            continue

        if fuel_level < threshold:
            low_fuel_records.append(event)

    return low_fuel_records


# 17. Calculate consumption in litres per 100 km
def calculate_fuel_efficiency(distance_km: float, fuel_used: float) -> float:
    if distance_km < 0:
        raise ValueError("Distance cannot be negative")

    if fuel_used < 0:
        raise ValueError("Fuel used cannot be negative")

    if distance_km == 0:
        return 0.0

    fuel_consumption = fuel_used / distance_km * 100
    return round(fuel_consumption, 2)


# 18. Find individual long stops for one vehicle
def detect_long_stops(
    events: list[dict],
    threshold_seconds: float = 60.0
) -> list[dict]:
    if threshold_seconds <= 0:
        raise ValueError("Threshold must be greater than zero")

    if len(events) < 2:
        return []

    sorted_events = sorted(events, key=lambda event: event["timestamp"])
    data = []
    stop_start = None
    last_zero_event = None

    for event in sorted_events:
        if event["speed_kmh"] == 0:
            if stop_start is None:
                stop_start = event["timestamp"]

            last_zero_event = event
        else:
            if stop_start is not None:
                start = datetime.fromisoformat(stop_start)
                end = datetime.fromisoformat(last_zero_event["timestamp"])
                duration_seconds = (end - start).total_seconds()

                if duration_seconds > threshold_seconds:
                    data.append({
                        "vehicle_id": last_zero_event["vehicle_id"],
                        "start_time": stop_start,
                        "end_time": last_zero_event["timestamp"],
                        "duration_seconds": duration_seconds
                    })

                stop_start = None
                last_zero_event = None

    if stop_start is not None:
        start = datetime.fromisoformat(stop_start)
        end = datetime.fromisoformat(last_zero_event["timestamp"])
        duration_seconds = (end - start).total_seconds()

        if duration_seconds > threshold_seconds:
            data.append({
                "vehicle_id": last_zero_event["vehicle_id"],
                "start_time": stop_start,
                "end_time": last_zero_event["timestamp"],
                "duration_seconds": duration_seconds
            })

    return data


# 19. Find the fastest vehicle in fleet reports
def get_fastest_vehicle(reports: list[dict]) -> dict:
    if not reports:
        return {}

    fastest_vehicle = reports[0]
    max_speed_kmh = fastest_vehicle["max_speed_kmh"]

    for report in reports:
        speed = report["max_speed_kmh"]

        if speed > max_speed_kmh:
            max_speed_kmh = speed
            fastest_vehicle = report

    return fastest_vehicle


# 20. Calculate percentage of moving vehicles
def calculate_fleet_utilization(vehicles: list[dict]) -> float:
    if not vehicles:
        return 0.0

    total_vehicles = len(vehicles)
    moving_vehicles = 0

    for vehicle in vehicles:
        if vehicle["speed_kmh"] > 0:
            moving_vehicles += 1

    percent = moving_vehicles / total_vehicles * 100
    return round(percent, 2)
