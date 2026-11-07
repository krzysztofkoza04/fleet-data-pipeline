
import pytest

from fleet_pipeline.analytics import (
    group_events_by_vehicle,
    calculate_vehicle_stats,
    haversine_distance,
    calculate_total_distance,
    detect_speed_anomalies,
    calculate_acceleration,
    remove_duplicate_timestamps,
    detect_acceleration_anomalies,
)


# Shared test data for acceleration calculations
acceleration_events = [
    {
        "vehicle_id": "TRUCK_001",
        "timestamp": "2026-10-19T10:00:00+00:00",
        "speed_kmh": 72
    },
    {
        "vehicle_id": "TRUCK_001",
        "timestamp": "2026-10-19T10:00:05+00:00",
        "speed_kmh": 36
    },
    {
        "vehicle_id": "TRUCK_001",
        "timestamp": "2026-10-19T10:00:00+00:00",
        "speed_kmh": 90
    }
]


def test_negative_acceleration():
    result = calculate_acceleration(
        acceleration_events[0],
        acceleration_events[1]
    )
    assert result == -2.0


def test_same_timestamp_raises_error():
    with pytest.raises(
        ValueError,
        match="Time difference must be positive"
    ):
        calculate_acceleration(
            acceleration_events[0],
            acceleration_events[2]
        )


def test_negative_time_raises_error():
    with pytest.raises(ValueError):
        calculate_acceleration(
            acceleration_events[1],
            acceleration_events[0]
        )


def test_detect_acceleration_anomalies():
    events = [
        {
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-19T10:00:00+00:00",
            "speed_kmh": 50
        },
        {
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-19T10:00:05+00:00",
            "speed_kmh": 55
        },
        {
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-19T10:00:07+00:00",
            "speed_kmh": 100
        }
    ]

    result = detect_acceleration_anomalies(events, 3.0)

    assert result == [events[2]]


def test_no_acceleration_anomalies():
    events = [
        {
            "timestamp": "2026-10-19T10:00:00+00:00",
            "speed_kmh": 50
        },
        {
            "timestamp": "2026-10-19T10:00:10+00:00",
            "speed_kmh": 55
        }
    ]

    result = detect_acceleration_anomalies(events, 3.0)

    assert result == []


def test_acceleration_anomalies_with_duplicates():
    events = [
        {
            "timestamp": "2026-10-19T10:00:00+00:00",
            "speed_kmh": 50
        },
        {
            "timestamp": "2026-10-19T10:00:00+00:00",
            "speed_kmh": 70
        },
        {
            "timestamp": "2026-10-19T10:00:02+00:00",
            "speed_kmh": 100
        },
        {
            "timestamp": "2026-10-19T10:00:12+00:00",
            "speed_kmh": 95
        }
    ]

    result = detect_acceleration_anomalies(events)

    assert result == [events[2]]


def test_acceleration_anomalies_only_duplicates():
    events = [
        {"timestamp": "2026-10-19T10:00:00+00:00", "speed_kmh": 50},
        {"timestamp": "2026-10-19T10:00:00+00:00", "speed_kmh": 70}
    ]

    result = detect_acceleration_anomalies(events)

    assert result == []


# Additional tests for other analytics functions

def test_group_events_by_vehicle():
    events = [
        {"vehicle_id": "A", "speed_kmh": 50},
        {"vehicle_id": "B", "speed_kmh": 60},
        {"vehicle_id": "A", "speed_kmh": 70}
    ]

    result = group_events_by_vehicle(events)

    assert result == {
        "A": [events[0], events[2]],
        "B": [events[1]]
    }


def test_calculate_vehicle_stats():
    events = [
        {
            "vehicle_id": "A",
            "timestamp": "2026-10-19T10:10:00+00:00",
            "speed_kmh": 80,
            "fuel_level": 70
        },
        {
            "vehicle_id": "A",
            "timestamp": "2026-10-19T10:00:00+00:00",
            "speed_kmh": 40,
            "fuel_level": 90
        }
    ]

    result = calculate_vehicle_stats(events)

    assert result == {
        "vehicle_id": "A",
        "event_count": 2,
        "avg_speed_kmh": 60.0,
        "max_speed_kmh": 80,
        "last_fuel_level": 70
    }


def test_haversine_distance():
    assert haversine_distance(0, 0, 0, 0) == 0.0
    assert haversine_distance(0, 0, 0, 1) == 111.19


def test_calculate_total_distance():
    events = [
        {
            "timestamp": "2026-10-19T10:20:00+00:00",
            "latitude": 0.0,
            "longitude": 2.0
        },
        {
            "timestamp": "2026-10-19T10:00:00+00:00",
            "latitude": 0.0,
            "longitude": 0.0
        },
        {
            "timestamp": "2026-10-19T10:10:00+00:00",
            "latitude": 0.0,
            "longitude": 1.0
        }
    ]

    result = calculate_total_distance(events)

    assert result == 222.38


def test_detect_speed_anomalies():
    events = [
        {"timestamp": "10:00", "speed_kmh": 50},
        {"timestamp": "10:01", "speed_kmh": 55},
        {"timestamp": "10:02", "speed_kmh": 140},
        {"timestamp": "10:03", "speed_kmh": 60}
    ]

    result = detect_speed_anomalies(events, 50)

    assert result == [events[2], events[3]]


def test_remove_duplicate_timestamps():
    events = [
        {"timestamp": "10:00", "speed_kmh": 50},
        {"timestamp": "10:05", "speed_kmh": 60},
        {"timestamp": "10:00", "speed_kmh": 80}
    ]

    result = remove_duplicate_timestamps(events)

    assert result == [events[0], events[1]]
