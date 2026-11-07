def validate_gps_event(event: dict) -> bool:

    try:

        vehicle_id = event["vehicle_id"]
        latitude = event["latitude"]
        longitude = event["longitude"]
        speed_kmh = event["speed_kmh"]
        fuel_level = event["fuel_level"]
    except KeyError:
        return False


    if not isinstance(vehicle_id, str) or vehicle_id.strip() == "" :
        return False

    if not isinstance(latitude, (int, float)):
        return False
    if latitude < -90 or latitude > 90:
        return False

    if not isinstance(longitude, (int, float)):
        return False
    if longitude  < -180 or longitude > 180:
        return False

    if not isinstance(speed_kmh, (int, float)):
        return False
    if speed_kmh < 0 or speed_kmh > 180:
        return False

    if not isinstance(fuel_level, (int, float)):
        return False
    if fuel_level < 0 or fuel_level > 100:
        return False

    return True

def validate_batch(events : list[dict]) ->  dict:
    valid =[]
    invalid =[]
    for event in events:

        if validate_gps_event(event):
            valid.append(event)
        else:
            invalid.append(event)
    return {
        "valid" : valid,
        "invalid" : invalid,
        "valid_count" : len(valid),
        "invalid_count": len(invalid)
    }


def has_missing_fields(
    event: dict,
    required_fields: list[str]
) -> bool:
    for field in required_fields:
        if field not in event or event[field] is None:
            return True
    return False


def count_incomplete_records(
    events: list[dict],
    required_fields: list[str]
) -> int:
    incomplete_records = 0

    for event in events:
        if has_missing_fields(event, required_fields):
            incomplete_records += 1

    return incomplete_records


def get_missing_fields(
    event: dict,
    required_fields: list[str]
) -> list[str]:
    missing = []

    for field in required_fields:
        if field not in event or event[field] is None:
            missing.append(field)

    return missing


def separate_valid_records(
    events: list[dict],
    required_fields: list[str]
) -> dict:
    valid = []
    rejected = []

    for event in events:
        if has_missing_fields(event, required_fields):
            rejected.append(event)
        else:
            valid.append(event)

    return {
        "valid": valid,
        "rejected": rejected
    }


def build_rejection_report(
    events: list[dict],
    required_fields: list[str]
) -> list[dict]:
    rejected = []

    for event in events:
        missing = get_missing_fields(event, required_fields)

        if missing:
            rejected.append({
                "record": event,
                "missing_fields": missing
            })

    return rejected


def validate_gps_records(
    events: list[dict],
    max_speed_kmh: float = 150.0
) -> dict:

    if max_speed_kmh <= 0:
        raise ValueError("max_speed_kmh must be positive")

    valid = []
    rejected = []

    for event in events:
        errors = []

        vehicle_id = event.get("vehicle_id")
        timestamp = event.get("timestamp")
        latitude = event.get("latitude")
        longitude = event.get("longitude")
        speed_kmh = event.get("speed_kmh")

        if not isinstance(vehicle_id, str) or not vehicle_id.strip():
            errors.append("missing_vehicle_id")

        if not isinstance(timestamp, str) or not timestamp.strip():
            errors.append("missing_timestamp")

        if latitude is None:
            errors.append("missing_latitude")
        elif (
            not isinstance(latitude, (int, float))
            or isinstance(latitude, bool)
            or not -90 <= latitude <= 90
        ):
            errors.append("invalid_latitude")

        if longitude is None:
            errors.append("missing_longitude")
        elif (
            not isinstance(longitude, (int, float))
            or isinstance(longitude, bool)
            or not -180 <= longitude <= 180
        ):
            errors.append("invalid_longitude")

        if speed_kmh is None:
            errors.append("missing_speed")
        elif (
            not isinstance(speed_kmh, (int, float))
            or isinstance(speed_kmh, bool)
            or not 0 <= speed_kmh <= max_speed_kmh
        ):
            errors.append("invalid_speed")

        if errors:
            rejected.append({
                "record": event,
                "errors": errors
            })
        else:
            valid.append(event)

    total_records = len(events)
    valid_records = len(valid)
    rejected_records = len(rejected)

    valid_percent = (
        round(valid_records / total_records * 100, 2)
        if total_records > 0
        else 0.0
    )

    return {
        "valid": valid,
        "rejected": rejected,
        "summary": {
            "total_records": total_records,
            "valid_records": valid_records,
            "rejected_records": rejected_records,
            "valid_percent": valid_percent
        }
    }
