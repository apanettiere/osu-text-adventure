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
            return

        self.player.discovered_rooms.add(self.current_room_id)
        self.player.room_positions[self.current_room_id] = (0, 0)
        self.player.current_pos = (0, 0)


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

        direction_deltas = {
            "north": (0, -1),
            "south": (0, 1),
            "east": (1, 0),
            "west": (-1, 0),
        }

        if target not in direction_deltas:
            return ["Map supports only: north, south, east, west"]

        next_room_id = room.exits[target]

        if next_room_id not in self.rooms:
            return ["Error: exit points to a missing room in game.json"]

        # --- Compute map coordinates ---
        current_pos = self.player.room_positions.get(self.current_room_id, (0, 0))
        x, y = current_pos
        dx, dy = direction_deltas[target]
        nx, ny = (x + dx, y + dy)

        # Always assign coordinate so it appears on map
        if next_room_id not in self.player.room_positions:
            self.player.room_positions[next_room_id] = (nx, ny)

        dest_room = self.rooms.get(next_room_id)

        # --- Check if blocked ---
        if dest_room and dest_room.requires:
            for req in dest_room.requires:
                if req.get("type") == "item":
                    item = req.get("item")
                    amount = int(req.get("amount", 1))
                    message = req.get("message", "You cannot go there yet.")

                    have = int(self.player.inventory.get(item, 0))

                    if have < amount:
                        # Reveal but DO NOT move
                        self.player.discovered_rooms.add(next_room_id)
                        return [message]

        self.player.current_pos = (nx, ny)
        self.player.discovered_rooms.add(next_room_id)
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