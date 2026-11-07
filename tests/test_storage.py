
import json

from fleet_pipeline.storage import (
    save_events_to_json,
    load_events_from_json,
    append_events_to_jsonl
)


def test_save_load_events(tmp_path):
    events = [
        {
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-18T10:00:00Z",
            "latitude": 50.04,
            "longitude": 21.99,
            "speed_kmh": 65,
            "fuel_level": 80
        },
        {
            "vehicle_id": "TRUCK_002",
            "timestamp": "2026-10-18T10:01:00Z",
            "latitude": 50.05,
            "longitude": 22.01,
            "speed_kmh": 70,
            "fuel_level": 55
        }
    ]

    filepath = tmp_path / "gps_events.json"

    save_events_to_json(events, filepath)
    data = load_events_from_json(filepath)

    assert filepath.exists()
    assert data == events


def test_append_events_to_jsonl(tmp_path):
    batch_1 = [
        {"vehicle_id": "TRUCK_001", "timestamp": "10:00"},
        {"vehicle_id": "TRUCK_002", "timestamp": "10:00"}
    ]

    batch_2 = [
        {"vehicle_id": "TRUCK_003", "timestamp": "10:01"}
    ]

    filepath = tmp_path / "events.jsonl"

    append_events_to_jsonl(batch_1, filepath)
    append_events_to_jsonl(batch_2, filepath)

    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    event_1 = json.loads(lines[0])
    event_2 = json.loads(lines[2])

    assert len(lines) == 3
    assert event_1 == batch_1[0]
    assert event_2 == batch_2[0]
