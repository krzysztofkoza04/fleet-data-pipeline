import pytest

from fleet_pipeline.validators import (
    validate_gps_event,
    validate_batch
)


@pytest.mark.parametrize(
    "event, expected",
    [
        ({
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-18T12:30:00+00:00",
            "latitude": 50.0413,
            "longitude": 21.9990,
            "speed_kmh": 65.5,
            "fuel_level": 73.2
        }, True),

        ({
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-18T12:30:00+00:00",
            "latitude": 120,
            "longitude": 21.9990,
            "speed_kmh": 65.5,
            "fuel_level": 73.2
        }, False),

        ({
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-18T12:30:00+00:00",
            "latitude": 50.0413,
            "longitude": 21.9990,
            "speed_kmh": -10,
            "fuel_level": 73.2
        }, False),

        ({
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-18T12:30:00+00:00",
            "latitude": 50.0413,
            "speed_kmh": 65.5,
            "fuel_level": 73.2
        }, False),

        ({
            "vehicle_id": "",
            "timestamp": "2026-10-18T12:30:00+00:00",
            "latitude": 50.0413,
            "longitude": 21.9990,
            "speed_kmh": 65.5,
            "fuel_level": 73.2
        }, False)
    ]
)
def test_validate_gps_event(event, expected):
    result = validate_gps_event(event)
    assert result == expected


def test_validate_batch_mixed():
    events = [
        {
            "vehicle_id": "TRUCK_001",
            "latitude": 50.04,
            "longitude": 21.99,
            "speed_kmh": 65,
            "fuel_level": 80
        },
        {
            "vehicle_id": "TRUCK_002",
            "latitude": 120,
            "longitude": 21.99,
            "speed_kmh": 70,
            "fuel_level": 50
        }
    ]

    result = validate_batch(events)

    assert result["valid_count"] == 1
    assert result["invalid_count"] == 1
    assert result["valid"] == [events[0]]
    assert result["invalid"] == [events[1]]


def test_validate_batch_empty():
    result = validate_batch([])

    assert result["valid"] == []
    assert result["invalid"] == []
    assert result["valid_count"] == 0
    assert result["invalid_count"] == 0
