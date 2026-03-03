from __future__ import annotations
from engine.models import Player
from engine.loader import load_game_data, build_room_map

DIRECTION_DELTAS: dict[str, tuple[int,int]] = {
    "north": (0, -1),
    "south": (0,  1),
    "east":  (1,  0),
    "west":  (-1, 0),
}

ENTRY_SPAWN: dict[str, object] = {
    "north": lambda w, h: (w // 2, h - 1),
    "south": lambda w, h: (w // 2, 0),
    "east":  lambda w, h: (0,      h // 2),
    "west":  lambda w, h: (w - 1,  h // 2),
}

# World-map top-left position (col, row) for each walkable room
# These are char coordinates on the unified map display
MAP_ROOM_POS: dict[str, tuple[int,int]] = {
    "shadow_trees":    (15, 0),
    "clearing":        (16, 10),
    "soggy_path":      (17, 22),
    "stone_foothills": (28, 11),
    "fallen_pines":    (4,  11),
}

REVEAL_RADIUS = 2  # tiles revealed around each visited position


class GameState:
    def __init__(self):
        self.player = Player()
        self.game_data = load_game_data()
        self.rooms = build_room_map(self.game_data)
        self.current_room_id: str = self.game_data.get("starting_room")
        self.is_running = True

        if self.current_room_id not in self.rooms:
            self.is_running = False
            return

        start = self.rooms[self.current_room_id]
        self.player.discovered_rooms.add(self.current_room_id)
        self.player.explored_rooms.add(self.current_room_id)
        self.player.room_positions[self.current_room_id] = (0, 0)
        self.player.current_pos = (0, 0)
        self.local_x = start.width  // 2
        self.local_y = start.height // 2
        self._mark_visited()

    def get_current_room(self):
        return self.rooms.get(self.current_room_id)

    def _world_pos(self) -> tuple[int,int] | None:
        base = MAP_ROOM_POS.get(self.current_room_id)
        if base is None:
            return None
        return (base[0] + self.local_x, base[1] + self.local_y)

    def _mark_visited(self):
        wp = self._world_pos()
        if wp is None:
            return
        wx, wy = wp
        r = REVEAL_RADIUS
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + 1:
                    self.player.visited_tiles.add((wx + dx, wy + dy))

    def _at_exit_edge(self, direction: str, room) -> bool:
        if direction == "north": return self.local_y == 0
        if direction == "south": return self.local_y == room.height - 1
        if direction == "east":  return self.local_x == room.width  - 1
        if direction == "west":  return self.local_x == 0
        return False

    def _step_local(self, direction: str, room) -> str | None:
        dx, dy = DIRECTION_DELTAS[direction]
        self.local_x = max(0, min(room.width  - 1, self.local_x + dx))
        self.local_y = max(0, min(room.height - 1, self.local_y + dy))
        self._mark_visited()
        for feat in getattr(room, "features", []):
            fx, fy = feat.get("pos", (-1, -1))
            if abs(fx - self.local_x) <= 1 and abs(fy - self.local_y) <= 1:
                return f"[nearby] {feat.get('desc', '')}"
        return None


    def describe_current_room(self) -> list[str]:
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        self.player.discovered_rooms.add(room.id)
        lines = [f"\n{room.name}", room.description]
        if room.exits:
            lines.append(f"Exits: {', '.join(sorted(room.exits.keys()))}")
        return lines


    def process_command(self, verb: str, target) -> list[str]:
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
        return ["Unknown command. Try: look, go <direction>, gather <resource>, inventory, quit"]


    def handle_go(self, target) -> list[str]:
        if not target:
            return ["Go where? Example: go north"]
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        if target not in DIRECTION_DELTAS:
            return ["Map supports only: north, south, east, west"]

        if room.is_walkable:
            at_edge = self._at_exit_edge(target, room)
            if not at_edge:
                flavour = self._step_local(target, room)
                lines = [f"You move {target}."]
                if flavour:
                    lines.append(flavour)
                return lines
            if target not in room.exits:
                return ["The trees press in close. You cannot go that way."]
        else:
            if target not in room.exits:
                return ["You cannot go that way."]

        next_room_id = room.exits[target]
        if next_room_id not in self.rooms:
            return ["Error: exit points to a missing room in game.json"]

        cur_x, cur_y = self.player.room_positions.get(self.current_room_id, (0, 0))
        dx, dy = DIRECTION_DELTAS[target]
        nx, ny = cur_x + dx, cur_y + dy
        if next_room_id not in self.player.room_positions:
            self.player.room_positions[next_room_id] = (nx, ny)

        dest_room = self.rooms.get(next_room_id)

        if dest_room and dest_room.requires:
            for req in dest_room.requires:
                if req.get("type") == "item":
                    item    = req.get("item")
                    amount  = int(req.get("amount", 1))
                    message = req.get("message", "You cannot go there yet.")
                    if int(self.player.inventory.get(item, 0)) < amount:
                        self.player.discovered_rooms.add(next_room_id)
                        return [message]

        self.player.current_pos = (nx, ny)
        self.player.discovered_rooms.add(next_room_id)
        self.player.explored_rooms.add(next_room_id)
        self.current_room_id = next_room_id

        dest = self.rooms[next_room_id]
        self.local_x, self.local_y = ENTRY_SPAWN[target](dest.width, dest.height)
        self._mark_visited()
        return self.describe_current_room()


    def handle_gather(self, target) -> list[str]:
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