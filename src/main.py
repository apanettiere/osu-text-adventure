import json
from pathlib import Path
from engine.models import Player


def load_game_data() -> dict:
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "game.json"

    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_room_map(game_data: dict) -> dict:
    rooms = game_data.get("rooms", [])
    return {room.get("id"): room for room in rooms if room.get("id")}


def print_room(room: dict) -> None:
    print(f"\n{room.get('name', '')}")
    print(room.get("description", ""))

    exits = room.get("exits", {})
    if exits:
        directions = ", ".join(sorted(exits.keys()))
        print(f"Exits: {directions}")


def parse_command(text: str) -> tuple[str, str | None]:
    parts = text.strip().lower().split()

    if not parts:
        return "", None

    verb = parts[0]
    target = parts[1] if len(parts) > 1 else None

    return verb, target


def main() -> None:
    player = Player()

    game_data = load_game_data()
    rooms = build_room_map(game_data)

    current_room_id = game_data.get("starting_room")

    if current_room_id not in rooms:
        print("Error: starting_room is missing or invalid in game.json")
        return

    print("The Dark Forest")
    print("Type: look, go <direction>, inventory, quit")

    print_room(rooms[current_room_id])

    while True:
        user_input = input("\n> ")
        verb, target = parse_command(user_input)

        if verb in ("quit", "exit"):
            print("Goodbye.")
            break

        if verb == "":
            print("Please type a command.")
            continue

        if verb == "look":
            print_room(rooms[current_room_id])
            continue

        if verb == "go":
            if not target:
                print("Go where? Example: go north")
                continue

            exits = rooms[current_room_id].get("exits", {})
            next_room_id = exits.get(target)

            if not next_room_id:
                print("You cannot go that way.")
                continue

            if next_room_id not in rooms:
                print("Error: exit points to a missing room in game.json")
                continue

            current_room_id = next_room_id
            print_room(rooms[current_room_id])
            continue

        if verb == "inventory":
            player.show_inventory()
            continue

        print("Unknown command. Try: look, go <direction>, inventory, quit")


if __name__ == "__main__":
    main()