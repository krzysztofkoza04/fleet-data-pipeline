from .generator import generate_fleet_events
from .storage import save_events_to_json, load_events_from_json
from .validators import validate_batch, validate_gps_records, get_missing_fields
from .normalization import normalize_gps_batch


def run_pipeline(vehicle_ids: list[str], filepath: str) -> list[dict]:
    events = generate_fleet_events(vehicle_ids)
    save_events_to_json(events, filepath)
    data = load_events_from_json(filepath)
    return data


def process_and_save_batch(
    events: list[dict],
    valid_path: str,
    invalid_path: str
) -> dict:
    data = validate_batch(events)
    save_events_to_json(data["valid"], valid_path)
    save_events_to_json(data["invalid"], invalid_path)

    return {
        "valid_count": data["valid_count"],
        "invalid_count": data["invalid_count"]
    }


def split_into_batches(
    events: list[dict],
    batch_size: int
) -> list[list[dict]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    batches = []

    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        batches.append(batch)

    return batches


def process_gps_batches(
    events: list[dict],
    batch_size: int
) -> list[dict]:
    batches = split_into_batches(events, batch_size)
    results = []

    for batch in batches:
        normalized = normalize_gps_batch(batch)
        results.extend(normalized)

    return results


def process_gps_quarantine(
    events: list[dict],
    required_fields: list[str]
) -> dict:
    normalized = normalize_gps_batch(events)
    valid = []
    rejected = []

    for event in normalized:
        missing = get_missing_fields(event, required_fields)

        if missing:
            rejected.append({
                "record": event,
                "missing_fields": missing
            })
        else:
            valid.append(event)

    total_records = len(events)
    valid_records = len(valid)
    rejected_records = len(rejected)

    if total_records == 0:
        valid_percent = 0.0
    else:
        valid_percent = round(valid_records / total_records * 100, 2)

    summary = {
        "total_records": total_records,
        "valid_records": valid_records,
        "rejected_records": rejected_records,
        "valid_percent": valid_percent
    }

    return {
        "valid": valid,
        "rejected": rejected,
        "summary": summary
    }


def process_telemetry_pipeline(
    events: list[dict],
    batch_size: int = 100
) -> dict:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    clean_events = []
    rejected_events = []
    seen = set()

    duplicate_records = 0
    validation_errors = 0

    batches = split_into_batches(events, batch_size)

    for batch in batches:
        normalized = normalize_gps_batch(batch)
        validation_result = validate_gps_records(normalized)

        rejected_batch = validation_result["rejected"]
        rejected_events.extend(rejected_batch)
        validation_errors += len(rejected_batch)

        valid_batch = validation_result["valid"]

        for event in valid_batch:
            key = (event["vehicle_id"], event["timestamp"])

            if key in seen:
                duplicate_records += 1
                rejected_events.append({
                    "record": event,
                    "errors": ["duplicate_record"]
                })
            else:
                seen.add(key)
                clean_events.append(event)

    total_records = len(events)
    valid_records = len(clean_events)
    rejected_records = len(rejected_events)

    if total_records == 0:
        valid_percent = 0.0
    else:
        valid_percent = round(valid_records / total_records * 100, 2)

    summary = {
        "total_records": total_records,
        "valid_records": valid_records,
        "rejected_records": rejected_records,
        "duplicate_records": duplicate_records,
        "validation_errors": validation_errors,
        "valid_percent": valid_percent
    }

    return {
        "clean_events": clean_events,
        "rejected_events": rejected_events,
        "summary": summary
    }


def process_batches_safely(batches: list[list[dict]]) -> dict:
    processed = []
    failed_batches = []

    for batch_number, batch in enumerate(batches, start=1):
        try:
            normalized = normalize_gps_batch(batch)
            processed.extend(normalized)
        except (TypeError, KeyError, ValueError) as error:
            failed_batches.append({
                "batch_number": batch_number,
                "error": str(error)
            })

    total_batches = len(batches)
    failed_count = len(failed_batches)
    successful_batches = total_batches - failed_count

    summary = {
        "total_batches": total_batches,
        "successful_batches": successful_batches,
        "failed_batches": failed_count
    }

    return {
        "processed": processed,
        "failed_batches": failed_batches,
        "summary": summary
    }
