import json
from pathlib import Path


def load_game_data() -> dict:
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "game.json"

    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_starting_room(game_data: dict) -> dict:
    starting_room_id = game_data.get("starting_room")
    rooms = game_data.get("rooms", [])

    for room in rooms:
        if room.get("id") == starting_room_id:
            return room

    # Fallback if JSON is missing something
    return {
        "id": "unknown",
        "name": "Unknown",
        "description": "The world data is missing a starting room."
    }


def main() -> None:
    game_data = load_game_data()
    room = get_starting_room(game_data)

    print(room.get("name", ""))
    print(room.get("description", ""))

    while True:
        user_input = input("\n> ").strip()

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye.")
            break

        print(f"You typed: {user_input}")


if __name__ == "__main__":
    main()