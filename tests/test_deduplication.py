from fleet_pipeline.deduplication import deduplicate_events
import pytest

test_data =[
    {
        "vehicle_id": "TRUCK_001",
        "timestamp": "2026-10-18T10:00:00Z"
    },

    {
        "vehicle_id": "TRUCK_001",
        "timestamp": "2026-10-18T10:01:00Z"
    }
]

duplicate_data =[
    {
        "vehicle_id": "TRUCK_001",
        "timestamp": "2026-10-18T10:00:00Z"
    },

    {
        "vehicle_id": "TRUCK_001",
        "timestamp": "2026-10-18T10:00:00Z"
    }
]

def test_empty_list():
    result = deduplicate_events([])

    assert result == []

def test_duplicate_events():
    result = deduplicate_events(duplicate_data)

    assert result == [duplicate_data[0]]



def test_same_vehicle_different_timestamps():
    result = deduplicate_events(test_data)

    assert result == test_data
