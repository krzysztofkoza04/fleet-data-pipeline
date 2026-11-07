
import pandas as pd
import pytest

from fleet_pipeline.pandas_analytics import (
    load_fleet_dataframe,
    inspect_fleet_data,
    filter_vehicle_events,
    calculate_speed_statistics,
    calculate_pandas_fleet_report
)


# Przykładowe dane do testów
def create_test_dataframe():

    data = [
        {"vehicle_id": "TRUCK_001", "speed_kmh": 60.0},
        {"vehicle_id": "TRUCK_001", "speed_kmh": 80.0},
        {"vehicle_id": "TRUCK_002", "speed_kmh": 40.0},
        {"vehicle_id": "TRUCK_002", "speed_kmh": 0.0},
        {"vehicle_id": "TRUCK_003", "speed_kmh": 100.0}
    ]

    df = pd.DataFrame(data)

    return df


# TEST 1 - Wczytywanie pliku JSON
def test_load_fleet_dataframe(tmp_path):

    filepath = tmp_path / "events.json"

    df = create_test_dataframe()

    df.to_json(filepath, orient="records")

    loaded = load_fleet_dataframe(str(filepath))

    assert isinstance(loaded, pd.DataFrame)
    assert len(loaded) == 5
    assert "vehicle_id" in loaded.columns


# TEST 2 - Pusty plik JSON zawierający []
def test_load_empty_dataframe(tmp_path):

    filepath = tmp_path / "empty.json"

    filepath.write_text("[]", encoding="utf-8")

    df = load_fleet_dataframe(str(filepath))

    assert df.empty


# TEST 3 - Informacje o DataFrame
def test_inspect_fleet_data():

    df = create_test_dataframe()

    result = inspect_fleet_data(df)

    assert result["total_rows"] == 5
    assert result["total_columns"] == 2

    assert "vehicle_id" in result["column_names"]
    assert "speed_kmh" in result["column_names"]

    assert result["missing_values"]["speed_kmh"] == 0


# TEST 4 - Wykrywanie brakujących wartości
def test_inspect_missing_values():

    df = create_test_dataframe()

    df.loc[0, "speed_kmh"] = None

    result = inspect_fleet_data(df)

    assert result["missing_values"]["speed_kmh"] == 1


# TEST 5 - Filtrowanie pojazdów
def test_filter_vehicle_events():

    df = create_test_dataframe()

    result = filter_vehicle_events(
        df,
        vehicle_id="TRUCK_001",
        min_speed=65.0
    )

    assert len(result) == 1
    assert result.iloc[0]["speed_kmh"] == 80.0


# TEST 6 - Filtrowanie bez wyników
def test_filter_vehicle_events_empty():

    df = create_test_dataframe()

    result = filter_vehicle_events(
        df,
        vehicle_id="TRUCK_999"
    )

    assert result.empty
    assert "speed_kmh" in result.columns


# TEST 7 - Nieprawidłowy próg prędkości
def test_filter_vehicle_events_invalid_speed():

    df = create_test_dataframe()

    with pytest.raises(ValueError):

        filter_vehicle_events(
            df,
            vehicle_id="TRUCK_001",
            min_speed=-10.0
        )


# TEST 8 - Statystyki prędkości
def test_calculate_speed_statistics():

    df = create_test_dataframe()

    result = calculate_speed_statistics(df)

    assert result["total_events"] == 5
    assert result["avg_speed_kmh"] == 56.0
    assert result["max_speed_kmh"] == 100.0
    assert result["min_speed_kmh"] == 0.0

    assert result["moving_events"] == 4
    assert result["stopped_events"] == 1


# TEST 9 - Pusty DataFrame
def test_calculate_speed_statistics_empty():

    df = pd.DataFrame()

    result = calculate_speed_statistics(df)

    assert result == {}


# TEST 10 - Raport grupowy floty
def test_calculate_pandas_fleet_report():

    df = create_test_dataframe()

    report = calculate_pandas_fleet_report(df)

    assert len(report) == 3

    truck_1 = report[
        report["vehicle_id"] == "TRUCK_001"
    ].iloc[0]

    truck_2 = report[
        report["vehicle_id"] == "TRUCK_002"
    ].iloc[0]

    assert truck_1["avg_speed_kmh"] == 70.0
    assert truck_1["max_speed_kmh"] == 80.0
    assert truck_1["event_count"] == 2

    assert truck_2["avg_speed_kmh"] == 20.0
    assert truck_2["min_speed_kmh"] == 0.0
    assert truck_2["event_count"] == 2
