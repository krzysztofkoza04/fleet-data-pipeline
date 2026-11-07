def deduplicate_events(events: list[dict]) -> list[dict]:
    data = []
    seen = set()

    for event in events:
        key = (event["vehicle_id"], event["timestamp"])

        if key not in seen:
            data.append(event)
            seen.add(key)

    return data


def count_duplicate_records(events: list[dict]) -> int:
    seen = set()
    duplicates = 0

    for event in events:
        key = (event["vehicle_id"], event["timestamp"])

        if key in seen:
            duplicates += 1
        else:
            seen.add(key)

    return duplicates
