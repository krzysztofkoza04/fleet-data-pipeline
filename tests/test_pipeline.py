import json

from fleet_pipeline.validators import validate_batch
from fleet_pipeline.deduplication import deduplicate_events
from fleet_pipeline.storage import append_events_to_jsonl

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
        "latitude": 120,
        "longitude": 22.01,
        "speed_kmh": 70,
        "fuel_level": 55
    },
    {
        "vehicle_id": "TRUCK_003",
        "timestamp": "2026-10-18T10:02:00Z",
        "latitude": 50.05,
        "longitude": 22.02,
        "speed_kmh": 60,
        "fuel_level": 75
    }
]

def test_full_pipeline(tmp_path):

    filepath = tmp_path / "processed_events.jsonl"

    info = validate_batch(events)
    assert info["valid_count"] ==3
    assert info["invalid_count"] == 1

    data =deduplicate_events(info["valid"])
    assert len(data) == 2

    append_events_to_jsonl(data,filepath)
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    event_1 = json.loads(lines[0])
    event_2 = json.loads(lines[1])

    assert len(lines) == 2
    assert event_1 == data[0]
    assert event_2 == data[1]
