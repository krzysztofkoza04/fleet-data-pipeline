
import pandas as pd
import pytest

from fleet_pipeline.pandas_analytics import (
    enrich_gps_with_vehicle_info,
    calculate_rolling_avg_speed,
    detect_sudden_speed_changes,
    calculate_vehicle_stop_time,
    calculate_daily_fleet_report
)


def create_gps_dataframe():

    data = [
        {"vehicle_id": "TRUCK_001", "timestamp": "2026-10-28T10:00:00Z", "speed_kmh": 40.0},
        {"vehicle_id": "TRUCK_001", "timestamp": "2026-10-28T10:00:30Z", "speed_kmh": 50.0},
        {"vehicle_id": "TRUCK_001", "timestamp": "2026-10-28T10:01:00Z", "speed_kmh": 90.0},
        {"vehicle_id": "TRUCK_001", "timestamp": "2026-10-28T10:01:30Z", "speed_kmh": 0.0},
        {"vehicle_id": "TRUCK_001", "timestamp": "2026-10-28T10:02:00Z", "speed_kmh": 0.0},
        {"vehicle_id": "TRUCK_002", "timestamp": "2026-10-28T10:00:00Z", "speed_kmh": 60.0},
        {"vehicle_id": "TRUCK_002", "timestamp": "2026-10-28T10:01:00Z", "speed_kmh": 80.0}
    ]

    return pd.DataFrame(data)


def test_merge_left_join():

    gps = create_gps_dataframe()

    vehicles = pd.DataFrame([
        {"vehicle_id": "TRUCK_001", "driver_name": "Adam"}
    ])

    result = enrich_gps_with_vehicle_info(gps, vehicles)

    assert len(result) == len(gps)

    truck_2 = result[result["vehicle_id"] == "TRUCK_002"]

    assert truck_2["driver_name"].isna().all()


def test_merge_driver_name():

    gps = create_gps_dataframe()

    vehicles = pd.DataFrame([
        {"vehicle_id": "TRUCK_001", "driver_name": "Adam"}
    ])

    result = enrich_gps_with_vehicle_info(gps, vehicles)

    truck_1 = result[result["vehicle_id"] == "TRUCK_001"]

    assert (truck_1["driver_name"] == "Adam").all()


def test_merge_duplicate_vehicle():

    gps = create_gps_dataframe()

    vehicles = pd.DataFrame([
        {"vehicle_id": "TRUCK_001"},
        {"vehicle_id": "TRUCK_001"}
    ])

    with pytest.raises(pd.errors.MergeError):
        enrich_gps_with_vehicle_info(gps, vehicles)


def test_rolling_average():

    df = create_gps_dataframe()

    result = calculate_rolling_avg_speed(df, window=3)

    truck_1 = result[
        result["vehicle_id"] == "TRUCK_001"
    ].reset_index(drop=True)

    assert pd.isna(truck_1.loc[0, "rolling_avg_speed"])
    assert pd.isna(truck_1.loc[1, "rolling_avg_speed"])
    assert truck_1.loc[2, "rolling_avg_speed"] == 60.0


def test_rolling_separate_vehicles():

    df = create_gps_dataframe()

    result = calculate_rolling_avg_speed(df, window=2)

    truck_2 = result[
        result["vehicle_id"] == "TRUCK_002"
    ].reset_index(drop=True)

    assert pd.isna(truck_2.loc[0, "rolling_avg_speed"])
    assert truck_2.loc[1, "rolling_avg_speed"] == 70.0


def test_invalid_rolling_window():

    df = create_gps_dataframe()

    with pytest.raises(ValueError):
        calculate_rolling_avg_speed(df, window=0)


def test_sudden_speed_changes():

    df = create_gps_dataframe()

    result = detect_sudden_speed_changes(df, threshold=30)

    truck_1 = result[result["vehicle_id"] == "TRUCK_001"]

    assert len(truck_1) == 2

    assert set(truck_1["change_type"]) == {
        "acceleration",
        "deceleration"
    }


def test_invalid_speed_threshold():

    df = create_gps_dataframe()

    with pytest.raises(ValueError):
        detect_sudden_speed_changes(df, threshold=0)


def test_vehicle_stop_time():

    df = create_gps_dataframe()

    result = calculate_vehicle_stop_time(df)

    truck_1 = result[result["vehicle_id"] == "TRUCK_001"]

    assert truck_1["stop_seconds"].sum() == 30.0


def test_stop_time_per_vehicle():

    df = create_gps_dataframe()

    result = calculate_vehicle_stop_time(df)

    truck_2 = result[result["vehicle_id"] == "TRUCK_002"]

    assert truck_2["stop_seconds"].sum() == 0.0


def test_daily_fleet_report():

    df = create_gps_dataframe()

    result = calculate_daily_fleet_report(df)

    assert len(result) == 2

    truck_1 = result[
        result["vehicle_id"] == "TRUCK_001"
    ].iloc[0]

    assert truck_1["event_count"] == 5
    assert truck_1["avg_speed_kmh"] == 36.0
    assert truck_1["max_speed_kmh"] == 90.0


def test_daily_report_invalid_date():

    df = create_gps_dataframe()

    df.loc[0, "timestamp"] = "invalid"

    result = calculate_daily_fleet_report(df)

    truck_1 = result[
        result["vehicle_id"] == "TRUCK_001"
    ].iloc[0]

    assert truck_1["event_count"] == 4
