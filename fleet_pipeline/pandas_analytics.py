import pandas as pd
from pandas.conftest import ascending


def load_fleet_dataframe(filepath : str) -> pd.DataFrame:

    df = pd.read_json(filepath)

    if df.empty:
        return pd.DataFrame()

    return df

def inspect_fleet_data(df : pd.DataFrame) -> dict:

    total_rows = df.shape[0]
    total_columns = df.shape[1]
    columns_names = df.columns.tolist()
    missing  = df.isna().sum()
    missing_dict = missing.to_dict()

    dict = {
        "total_rows" : total_rows,
        "total_columns" : total_columns,
        "column_names" : columns_names,
        "missing_values": missing_dict
    }

    return dict

def filter_vehicle_events(
    df: pd.DataFrame,
    vehicle_id: str,
    min_speed: float = 0.0
) -> pd.DataFrame:

    if min_speed < 0:
        raise ValueError

    condition_1 = df["vehicle_id"] == vehicle_id
    filtered_df_1 = df[condition_1]

    condition_2 =filtered_df_1["speed_kmh"] > min_speed
    filtered_df_2 = filtered_df_1[condition_2]

    return filtered_df_2

def calculate_speed_statistics(
    df: pd.DataFrame
) -> dict:

    dictionary = {}

    if df.empty:
        return dictionary

    total_events = len(df)

    speeds = df["speed_kmh"]

    condition_1 = df["speed_kmh"] == 0
    filtered_events_1 = df[condition_1]
    stopped_events = len(filtered_events_1)

    condition_2 = df["speed_kmh"] > 0
    filtered_events_2 = df[condition_2]
    moving_events = len(filtered_events_2)

    average_speed = round(speeds.mean(), 2)
    maximum_speed = round(speeds.max(), 2)
    minimum_speed = round(speeds.min(), 2)

    dictionary = {
    "total_events": total_events,
    "avg_speed_kmh": average_speed,
    "max_speed_kmh": maximum_speed,
    "min_speed_kmh": minimum_speed,
    "moving_events": moving_events,
    "stopped_events": stopped_events
    }

    return dictionary

def calculate_pandas_fleet_report(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby("vehicle_id")

    report = grouped["speed_kmh"].agg(
        ["mean", "max", "min", "count"]
    )

    report["mean"] = round(report["mean"],2)
    report["max"] = round(report["max"], 2)
    report["min"] = round(report["min"], 2)

    report = report.rename(
        columns = {
            "mean": "avg_speed_kmh",
            "max": "max_speed_kmh",
            "min": "min_speed_kmh",
            "count": "event_count"
        }
    )

    report = report.reset_index()

    return report


def prepare_fleet_timestamps(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()

    new_df = df.copy()

    new_df["timestamp"] = pd.to_datetime(
        new_df["timestamp"],
        utc= True,
        errors =  "coerce"
    )

    return new_df

def sort_vehicle_events(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()

    sorted_df = df.copy()

    sorted_df = sorted_df.sort_values(
        by = ["vehicle_id", "timestamp"],
        ascending = [True, True]
    )

    sorted_df = sorted_df.reset_index(drop = True)

    return sorted_df

def calculate_time_differences(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()

    df_copy = df.copy()

    data_1 = prepare_fleet_timestamps(df_copy)

    data_2 = sort_vehicle_events(data_1)

    grouped = data_2.groupby("vehicle_id")

    previous_timestamp = grouped["timestamp"].shift(1)

    data_2["previous_timestamp"] = previous_timestamp

    data_2["time_difference"] = (
            data_2["timestamp"] - data_2["previous_timestamp"]
    )

    data_2["time_difference_seconds"] = (
        data_2["time_difference"].dt.total_seconds()
    )

    return data_2


def calculate_speed_changes(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()



    data_1 = prepare_fleet_timestamps(df)

    data_2 = sort_vehicle_events(data_1)

    grouped = data_2.groupby("vehicle_id")

    previous_speed = grouped["speed_kmh"].shift(1)

    data_2["previous_speed"] = previous_speed

    data_2["speed_change_kmh"] = (
            data_2["speed_kmh"] - data_2["previous_speed"]
    )

    data_2["absolute_speed_change"] = (
        data_2["speed_change_kmh"].abs()
    )

    return data_2

def detect_telemetry_gaps(
    df: pd.DataFrame,
    max_gap_seconds: float = 60.0
) -> pd.DataFrame:

    if max_gap_seconds<= 0:
        raise  ValueError

    if df.empty:
        return df.copy()

    data = calculate_time_differences(df)

    data["is_gap"] = (
        data["time_difference_seconds"] > max_gap_seconds
    )

    condition = data["is_gap"] == True

    gaps = data[condition]

    gaps = gaps.reset_index(drop = True)

    return gaps



def calculate_vehicle_telemetry_summary(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()

    grouped = df.groupby("vehicle_id")

    report = grouped.agg(
        avg_speed_kmh=("speed_kmh", "mean"),
        max_speed_kmh=("speed_kmh", "max"),
        min_fuel_level=("fuel_level", "min"),
        avg_fuel_level=("fuel_level", "mean"),
        event_count=("speed_kmh", "size")
    )

    report = report.round(2)
    report = report.reset_index()

    return report



def calculate_speed_deviation(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()

    data = df.copy()

    grouped = data.groupby("vehicle_id")

    data["vehicle_avg_speed"] = (
        grouped["speed_kmh"].transform("mean")
    )

    data["speed_deviation"] = (
        data["speed_kmh"] - data["vehicle_avg_speed"]
    )

    data["vehicle_avg_speed"] = (
        data["vehicle_avg_speed"].round(2)
    )

    data["speed_deviation"] = (
        data["speed_deviation"].round(2)
    )

    return data



def calculate_fuel_changes(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()

    data = prepare_fleet_timestamps(df)
    data = sort_vehicle_events(data)

    grouped = data.groupby("vehicle_id")

    data["fuel_change"] = grouped["fuel_level"].diff()

    data["fuel_consumed"] = (
        (-data["fuel_change"]).clip(lower=0)
    )

    data["fuel_change"] = data["fuel_change"].round(2)
    data["fuel_consumed"] = data["fuel_consumed"].round(2)

    return data



def detect_refueling_events(
    df: pd.DataFrame,
    min_fuel_increase: float = 10.0
) -> pd.DataFrame:

    if min_fuel_increase <= 0:
        raise ValueError

    if df.empty:
        return df.copy()

    data = calculate_fuel_changes(df)

    condition = data["fuel_change"] > min_fuel_increase

    refueling_events = data[condition].copy()

    refueling_events = refueling_events.reset_index(drop=True)

    return refueling_events



def calculate_fuel_summary(
    df: pd.DataFrame,
    min_fuel_increase: float = 10.0
) -> pd.DataFrame:

    if min_fuel_increase <= 0:
        raise ValueError

    if df.empty:
        return df.copy()

    data = calculate_fuel_changes(df)

    data["is_refueling"] = (
        data["fuel_change"] > min_fuel_increase
    )

    grouped = data.groupby("vehicle_id")

    report = grouped.agg(
        total_fuel_consumed=("fuel_consumed", "sum"),
        refueling_count=("is_refueling", "sum"),
        avg_fuel_level=("fuel_level", "mean"),
        event_count=("fuel_consumed", "size")
    )

    report = report.round(2)
    report = report.reset_index()

    return report


def enrich_gps_with_vehicle_info(
    gps_df: pd.DataFrame,
    vehicles_df: pd.DataFrame
) -> pd.DataFrame:

    if gps_df.empty:
        return gps_df.copy()

    gps = gps_df.copy()
    vehicles = vehicles_df.copy()

    result = pd.merge(
        gps,
        vehicles,
        on="vehicle_id",
        how="left",
        validate="many_to_one"
    )

    return result


def calculate_rolling_avg_speed(
    df: pd.DataFrame,
    window: int = 3
) -> pd.DataFrame:

    if window < 1:
        raise ValueError

    if df.empty:
        return df.copy()

    data = prepare_fleet_timestamps(df)
    data = sort_vehicle_events(data)

    grouped = data.groupby("vehicle_id")

    data["rolling_avg_speed"] = (
        grouped["speed_kmh"].transform(
            lambda speeds: speeds.rolling(
                window=window
            ).mean()
        )
    )

    data["rolling_avg_speed"] = (
        data["rolling_avg_speed"].round(2)
    )

    return data



def detect_sudden_speed_changes(
    df: pd.DataFrame,
    threshold: float = 30.0
) -> pd.DataFrame:

    if threshold <= 0:
        raise ValueError

    if df.empty:
        return df.copy()

    data = calculate_speed_changes(df)

    condition = data["absolute_speed_change"] > threshold

    result = data[condition].copy()

    result["change_type"] = "acceleration"

    condition2 = result["speed_change_kmh"] < 0

    result.loc[condition2, "change_type"] = "deceleration"

    result = result.reset_index(drop=True)

    return result



def calculate_vehicle_stop_time(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
        return df.copy()

    data = calculate_time_differences(df)

    grouped = data.groupby("vehicle_id")

    data["previous_speed"] = grouped["speed_kmh"].shift(1)

    data["stop_seconds"] = 0.0

    condition = (
        (data["speed_kmh"] == 0) &
        (data["previous_speed"] == 0) &
        (data["time_difference_seconds"] > 0)
    )

    data.loc[condition, "stop_seconds"] = (
        data.loc[condition, "time_difference_seconds"]
    )

    return data

def calculate_daily_fleet_report(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:
      return df.copy()

    data = prepare_fleet_timestamps(df)

    data["date"] = data["timestamp"].dt.date

    data=data.dropna(subset = ["date"])

    grouped = data.groupby(["vehicle_id","date"])

    report  = grouped.agg(
        avg_speed_kmh=("speed_kmh","mean"),
        max_speed_kmh=("speed_kmh", "max"),
        event_count=("speed_kmh", "size")
    )

    report = report.round(2)

    report = report.reset_index()

    return report
