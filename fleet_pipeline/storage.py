import json

def save_events_to_json(events : list[dict], filepath : str) -> None:

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(events, file,indent=4)

def load_events_from_json(filepath: str) -> list[dict]:

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            lista = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    return lista

def append_events_to_jsonl(
    events: list[dict],
    filepath: str
) -> None:

    with open(filepath, "a", encoding="utf-8") as file:

        for event in events:

            file.write(json.dumps(event) + "\n")

def load_events_from_jsonl(filepath : str) -> list[dict]:

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            events = []
            for event in file:
                event=event.strip()

                if not event:
                    continue

                event = json.loads(event)
                events.append(event)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    return events


