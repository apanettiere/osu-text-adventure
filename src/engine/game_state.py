from engine.models import Player
from engine.loader import load_game_data, build_room_map


class GameState:
    def __init__(self):
        self.player = Player()

        self.game_data = load_game_data()
        self.rooms = build_room_map(self.game_data)

        self.current_room_id = self.game_data.get("starting_room")
        self.is_running = True

        if self.current_room_id not in self.rooms:
            self.is_running = False


    def get_current_room(self):
        return self.rooms.get(self.current_room_id)

    def describe_current_room(self) -> list[str]:
        room = self.get_current_room()

        if not room:
            return ["Error: current room not found."]

        self.player.discovered_rooms.add(room.id)

        lines = []
        lines.append(f"\n{room.name}")
        lines.append(room.description)

        if room.exits:
            directions = ", ".join(sorted(room.exits.keys()))
            lines.append(f"Exits: {directions}")

        return lines


    def process_command(self, verb: str, target: str | None) -> list[str]:
        if not self.is_running:
            return []

        if verb in ("quit", "exit"):
            self.is_running = False
            return ["Goodbye."]

        if verb == "":
            return ["Please type a command."]

        if verb == "look":
            return self.describe_current_room()

        if verb == "inventory":
            return self.player.get_inventory_lines()

        if verb == "go":
            return self.handle_go(target)

        if verb == "gather":
            return self.handle_gather(target)

        return [
            "Unknown command. Try: look, go <direction>, gather <resource>, inventory, quit"
        ]


    def handle_go(self, target: str | None) -> list[str]:
        if not target:
            return ["Go where? Example: go north"]

        room = self.get_current_room()

        if not room:
            return ["Error: current room not found."]

        if target not in room.exits:
            return ["You cannot go that way."]

        next_room_id = room.exits[target]

        if next_room_id not in self.rooms:
            return ["Error: exit points to a missing room in game.json"]

        self.current_room_id = next_room_id
        return self.describe_current_room()


    def handle_gather(self, target: str | None) -> list[str]:
        if not target:
            return ["Gather what? Example: gather wood"]

        room = self.get_current_room()

        if not room:
            return ["Error: current room not found."]

        amount = room.gather_amount(target)

        if amount <= 0:
            return ["You cannot gather that here."]

        if target not in self.player.inventory:
            self.player.inventory[target] = 0

        self.player.inventory[target] += amount

        return [f"You gather {target}."]