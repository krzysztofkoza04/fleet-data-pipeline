from pathlib import Path

from fleet_pipeline.generator import generate_fleet_routes
from fleet_pipeline.pipeline import process_telemetry_pipeline
from fleet_pipeline.analytics import generate_fleet_report
from fleet_pipeline.analytics import calculate_fleet_summary
from fleet_pipeline.analytics import group_events_by_vehicle
from fleet_pipeline.analytics import detect_gps_jumps
from fleet_pipeline.analytics import detect_fuel_anomalies
from fleet_pipeline.analytics import detect_low_fuel
from fleet_pipeline.analytics import detect_long_stops
from fleet_pipeline.analytics import detect_acceleration_anomalies
from fleet_pipeline.storage import save_events_to_json


def create_demo_events() -> list[dict]:
    vehicles = [
        {
            "vehicle_id": "TRUCK_001",
            "latitude": 50.04,
            "longitude": 22.00,
            "speed_kmh": 65.0,
            "heading_degrees": 90.0
        },
        {
            "vehicle_id": "TRUCK_002",
            "latitude": 50.10,
            "longitude": 21.90,
            "speed_kmh": 50.0,
            "heading_degrees": 180.0
        },
        {
            "vehicle_id": "TRUCK_003",
            "latitude": 49.95,
            "longitude": 22.10,
            "speed_kmh": 75.0,
            "heading_degrees": 270.0
        }
    ]

    events = generate_fleet_routes(
        vehicles=vehicles,
        start_time="2026-10-28T10:00:00+00:00",
        count_per_vehicle=12,
        interval_seconds=30
    )

    # Dodajemy duplikat, aby sprawdzic deduplikacje.
    duplicate = events[0].copy()
    events.append(duplicate)

    # Dodajemy bledna predkosc, aby sprawdzic kwarantanne.
    invalid_speed = events[1].copy()
    invalid_speed["speed_kmh"] = -10.0
    invalid_speed["timestamp"] = "2026-10-28T11:00:00+00:00"
    events.append(invalid_speed)

    # Dodajemy rekord bez szerokosci geograficznej.
    missing_latitude = events[2].copy()
    missing_latitude.pop("latitude")
    missing_latitude["timestamp"] = "2026-10-28T11:01:00+00:00"
    events.append(missing_latitude)

    return events


def print_fleet_reports(events: list[dict]) -> None:
    reports = generate_fleet_report(events)
    summary = calculate_fleet_summary(reports)

    print("\n=== FLEET REPORTS ===")

    for report in reports:
        print("Vehicle:", report["vehicle_id"])
        print("Events:", report["event_count"])
        print("Average speed:", report["avg_speed_kmh"])
        print("Maximum speed:", report["max_speed_kmh"])
        print("Total distance:", report["total_distance_km"])
        print("Acceleration anomalies:", report["acceleration_anomalies_count"])
        print("Stop seconds:", report["total_stop_seconds"])
        print("Last fuel level:", report["last_fuel_level"])
        print()

    print("=== FLEET SUMMARY ===")
    print(summary)


def print_anomaly_reports(events: list[dict]) -> None:
    grouped = group_events_by_vehicle(events)

    print("\n=== ANOMALY REPORTS ===")

    for vehicle_id, vehicle_events in grouped.items():
        gps_jumps = detect_gps_jumps(vehicle_events)
        fuel_anomalies = detect_fuel_anomalies(vehicle_events)
        low_fuel = detect_low_fuel(vehicle_events)
        long_stops = detect_long_stops(vehicle_events)
        acceleration = detect_acceleration_anomalies(vehicle_events)

        print("Vehicle:", vehicle_id)
        print("GPS jumps:", len(gps_jumps))
        print("Fuel anomalies:", len(fuel_anomalies))
        print("Low fuel measurements:", len(low_fuel))
        print("Long stops:", len(long_stops))
        print("Acceleration anomalies:", len(acceleration))
        print()


def main() -> None:
    Path("data").mkdir(exist_ok=True)

    raw_events = create_demo_events()

    # Zapis do zwyklego JSON nadpisuje poprzedni plik.
    # Nie powielamy danych przy kolejnym uruchomieniu.
    save_events_to_json(raw_events, "data/demo_raw_events.json")

    result = process_telemetry_pipeline(raw_events, batch_size=10)

    clean_events = result["clean_events"]
    rejected_events = result["rejected_events"]
    summary = result["summary"]

    save_events_to_json(clean_events, "data/demo_clean_events.json")
    save_events_to_json(rejected_events, "data/demo_rejected_events.json")

    print("=== ETL SUMMARY ===")
    print("Total records:", summary["total_records"])
    print("Valid records:", summary["valid_records"])
    print("Rejected records:", summary["rejected_records"])
    print("Duplicates:", summary["duplicate_records"])
    print("Validation errors:", summary["validation_errors"])
    print("Valid percent:", summary["valid_percent"])

    print("\n=== REJECTED RECORDS ===")
    for rejected in rejected_events:
        print(rejected["errors"], rejected["record"].get("vehicle_id"))

    print_fleet_reports(clean_events)
    print_anomaly_reports(clean_events)

    print("=== OUTPUT FILES ===")
    print("data/demo_raw_events.json")
    print("data/demo_clean_events.json")
    print("data/demo_rejected_events.json")


if __name__ == "__main__":
    main()
