import pandas as pd
import pytest

from fleet_pipeline.pandas_analytics import (
    prepare_fleet_timestamps,
    sort_vehicle_events,
    calculate_time_differences,
    calculate_speed_changes,
    detect_telemetry_gaps
)


def create_test_dataframe():

    data = [
        {
            "vehicle_id": "TRUCK_002",
            "timestamp": "2026-10-28T10:01:00Z",
            "speed_kmh": 70.0
        },
        {
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-28T10:05:00Z",
            "speed_kmh": 80.0
        },
        {
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-28T10:00:00Z",
            "speed_kmh": 50.0
        },
        {
            "vehicle_id": "TRUCK_002",
            "timestamp": "2026-10-28T10:00:00Z",
            "speed_kmh": 60.0
        },
        {
            "vehicle_id": "TRUCK_001",
            "timestamp": "2026-10-28T10:00:30Z",
            "speed_kmh": 65.0
        }
    ]

    return pd.DataFrame(data)


# TEST 1 - Konwersja timestampów
def test_prepare_fleet_timestamps():

    df = create_test_dataframe()

    result = prepare_fleet_timestamps(df)

    assert isinstance(result["timestamp"].dtype, pd.DatetimeTZDtype)
    assert str(result["timestamp"].dt.tz) == "UTC"


# TEST 2 - Nieprawidłowy timestamp
def test_prepare_invalid_timestamp():

    df = create_test_dataframe()

    df.loc[0, "timestamp"] = "invalid_date"

    result = prepare_fleet_timestamps(df)

    assert pd.isna(result.loc[0, "timestamp"])


# TEST 3 - Brak modyfikacji oryginału
def test_prepare_timestamps_no_mutation():

    df = create_test_dataframe()

    original = df.copy(deep=True)

    prepare_fleet_timestamps(df)

    pd.testing.assert_frame_equal(df, original)


# TEST 4 - Sortowanie rekordów
def test_sort_vehicle_events():

    df = prepare_fleet_timestamps(
        create_test_dataframe()
    )

    result = sort_vehicle_events(df)

    assert result.iloc[0]["vehicle_id"] == "TRUCK_001"
    assert result.iloc[0]["speed_kmh"] == 50.0

    assert result.iloc[1]["speed_kmh"] == 65.0
    assert result.iloc[2]["speed_kmh"] == 80.0

    assert result.iloc[3]["vehicle_id"] == "TRUCK_002"


# TEST 5 - Resetowanie indeksu
def test_sort_vehicle_events_index():

    df = create_test_dataframe()

    result = sort_vehicle_events(df)

    assert result.index.tolist() == [0, 1, 2, 3, 4]


# TEST 6 - Obliczanie różnic czasu
def test_calculate_time_differences():

    df = create_test_dataframe()

    result = calculate_time_differences(df)

    truck_1 = result[
        result["vehicle_id"] == "TRUCK_001"
    ].reset_index(drop=True)

    assert pd.isna(
        truck_1.loc[0, "time_difference_seconds"]
    )

    assert truck_1.loc[1, "time_difference_seconds"] == 30.0
    assert truck_1.loc[2, "time_difference_seconds"] == 270.0


# TEST 7 - Niezależność pojazdów
def test_time_differences_per_vehicle():

    df = create_test_dataframe()

    result = calculate_time_differences(df)

    truck_2 = result[
        result["vehicle_id"] == "TRUCK_002"
    ].reset_index(drop=True)

    assert pd.isna(
        truck_2.loc[0, "time_difference_seconds"]
    )

    assert truck_2.loc[1, "time_difference_seconds"] == 60.0


# TEST 8 - Zmiany prędkości
def test_calculate_speed_changes():

    df = create_test_dataframe()

    result = calculate_speed_changes(df)

    truck_1 = result[
        result["vehicle_id"] == "TRUCK_001"
    ].reset_index(drop=True)

    assert pd.isna(truck_1.loc[0, "previous_speed"])

    assert truck_1.loc[1, "previous_speed"] == 50.0
    assert truck_1.loc[1, "speed_change_kmh"] == 15.0
    assert truck_1.loc[2, "speed_change_kmh"] == 15.0


# TEST 9 - Bezwzględna zmiana prędkości
def test_absolute_speed_change():

    df = create_test_dataframe()

    result = calculate_speed_changes(df)

    assert "absolute_speed_change" in result.columns

    speeds = result["absolute_speed_change"].dropna()

    assert (speeds >= 0).all()


# TEST 10 - Wykrywanie przerw
def test_detect_telemetry_gaps():

    df = create_test_dataframe()

    gaps = detect_telemetry_gaps(
        df,
        max_gap_seconds=60
    )

    assert len(gaps) == 1
    assert gaps.iloc[0]["vehicle_id"] == "TRUCK_001"
    assert gaps.iloc[0]["time_difference_seconds"] == 270.0


# TEST 11 - Nieprawidłowy próg
def test_detect_telemetry_gaps_invalid_threshold():

    df = create_test_dataframe()

    with pytest.raises(ValueError):
        detect_telemetry_gaps(
            df,
            max_gap_seconds=0
        )


# TEST 12 - Puste dane
def test_empty_dataframes():

    df = pd.DataFrame()

    assert prepare_fleet_timestamps(df).empty
    assert sort_vehicle_events(df).empty
    assert calculate_time_differences(df).empty
    assert calculate_speed_changes(df).empty
    assert detect_telemetry_gaps(df).empty
