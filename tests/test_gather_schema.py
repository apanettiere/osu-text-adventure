import json
from pathlib import Path


def test_at_least_one_room_has_gather_data():
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "game.json"

    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    rooms = data.get("rooms", [])

    for room in rooms:
        gather = room.get("gather")
        if isinstance(gather, dict) and "wood" in gather:
            return

    assert False, "No room contains gather data for wood"