
from fleet_pipeline.db_pipeline import run_db_pipeline


def test_db_pipeline():

    events = [
        {
            "vehicle_id": "TRUCK_TEST_001",
            "timestamp": "2026-11-07T12:00:00+00:00",
            "latitude": 50.05,
            "longitude": 22.01,
            "speed_kmh": 50,
            "fuel_level": 80,
            "heading_degrees": 90
        },
        {
            "vehicle_id": "TRUCK_TEST_001",
            "timestamp": "2026-11-07T12:01:00+00:00",
            "latitude": 50.06,
            "longitude": 22.02,
            "speed_kmh": 60,
            "fuel_level": 79,
            "heading_degrees": 95
        }
    ]

    result = run_db_pipeline(events)

    assert result["status"] == "SUCCESS"
    assert result["total_records"] == 2
    assert result["valid_records"] == 2
    assert result["rejected_records"] == 0
    assert result["duplicate_records"] == 0
    assert result["affected_events"] + result["unchanged_events"] == 2
