import json
from pathlib import Path

from engine.models import Room


def load_game_data() -> dict:
    project_root = Path(__file__).resolve().parents[2]
    data_path = project_root / "data" / "game.json"

    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_room_map(game_data: dict) -> dict:
    room_map = {}

    for room_data in game_data.get("rooms", []):
        room_id = room_data.get("id")
        if not room_id:
            continue

        room_map[room_id] = Room(room_data)

    return room_map