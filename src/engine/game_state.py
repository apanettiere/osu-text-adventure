from __future__ import annotations
import difflib
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

MAP_ROOM_POS: dict[str, tuple[int,int]] = {
    "thick_forest":   (15, -1),
    "clearing":       (16, 13),
    "riverbank":      (17, 31),
    "cave_entrance":  (33, 16),
    "far_shore":      (21, 47),
    "mountain_pass":  ( 2, 16),
}

REVEAL_RADIUS = 2


def _encode_visited_tiles(tiles: set[tuple[int, int]]) -> list[list[object]]:
    if not tiles:
        return []
    rows: dict[int, list[int]] = {}
    for x, y in tiles:
        rows.setdefault(int(y), []).append(int(x))
    encoded: list[list[object]] = []
    for y in sorted(rows):
        xs = sorted(set(rows[y]))
        if not xs:
            continue
        runs: list[list[int]] = []
        start = xs[0]
        prev = xs[0]
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
                continue
            runs.append([start, prev])
            start = x
            prev = x
        runs.append([start, prev])
        encoded.append([y, runs])
    return encoded


def _decode_visited_tiles(encoded) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    if not isinstance(encoded, list):
        return out
    for row in encoded:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            continue
        y_raw, runs = row
        try:
            y = int(y_raw)
        except Exception:
            continue
        if not isinstance(runs, (list, tuple)):
            continue
        for run in runs:
            if not isinstance(run, (list, tuple)) or len(run) != 2:
                continue
            try:
                x0 = int(run[0])
                x1 = int(run[1])
            except Exception:
                continue
            if x1 < x0:
                x0, x1 = x1, x0
            for x in range(x0, x1 + 1):
                out.add((x, y))
    return out


class GameState:
    def __init__(self):
        self.player    = Player()
        self.game_data = load_game_data()
        self.rooms     = build_room_map(self.game_data)

        # Item registry: name -> {weight, type, desc}
        self.item_registry: dict = self.game_data.get("items", {})
        # Crafting recipes: name -> {requires: {item: count}, desc}
        self.recipes: dict = self.game_data.get("recipes", {})

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

    def snapshot(self) -> dict:
        room_state = {}
        for rid, room in self.rooms.items():
            room_state[rid] = {
                "loot": dict(room.loot),
                "loot_hidden": {k: bool(v) for k, v in room.loot_hidden.items()},
            }
        return {
            "current_room_id": self.current_room_id,
            "local_x": int(self.local_x),
            "local_y": int(self.local_y),
            "player": {
                "inventory": {k: int(v) for k, v in self.player.inventory.items() if int(v) > 0},
                "torch_uses": self.player.torch_uses,
                "discovered_rooms": sorted(self.player.discovered_rooms),
                "explored_rooms": sorted(self.player.explored_rooms),
                "room_positions": {
                    rid: [int(pos[0]), int(pos[1])]
                    for rid, pos in self.player.room_positions.items()
                },
                "current_pos": [int(self.player.current_pos[0]), int(self.player.current_pos[1])],
                "visited_runs": _encode_visited_tiles(self.player.visited_tiles),
            },
            "rooms": room_state,
        }

    def apply_snapshot(self, snap: dict) -> bool:
        try:
            rid = snap.get("current_room_id")
            if rid not in self.rooms:
                return False
            p = snap.get("player", {})
            self.player.inventory = {k: int(v) for k, v in p.get("inventory", {}).items() if int(v) >= 0}
            self.player.torch_uses = p.get("torch_uses")
            self.player.discovered_rooms = set(p.get("discovered_rooms", []))
            self.player.explored_rooms = set(p.get("explored_rooms", []))
            self.player.room_positions = {}
            for room_id, pos in p.get("room_positions", {}).items():
                if room_id in self.rooms and isinstance(pos, (list, tuple)) and len(pos) == 2:
                    self.player.room_positions[room_id] = (int(pos[0]), int(pos[1]))
            cur_pos = p.get("current_pos", [0, 0])
            if isinstance(cur_pos, (list, tuple)) and len(cur_pos) == 2:
                self.player.current_pos = (int(cur_pos[0]), int(cur_pos[1]))
            if "visited_runs" in p:
                self.player.visited_tiles = _decode_visited_tiles(p.get("visited_runs", []))
            else:
                self.player.visited_tiles = set()
                for tile in p.get("visited_tiles", []):
                    if isinstance(tile, (list, tuple)) and len(tile) == 2:
                        self.player.visited_tiles.add((int(tile[0]), int(tile[1])))

            room_snap = snap.get("rooms", {})
            for room_id, data in room_snap.items():
                room = self.rooms.get(room_id)
                if not room:
                    continue
                room.loot = {k: int(v) for k, v in data.get("loot", {}).items() if int(v) > 0}
                room.loot_hidden = {k: bool(v) for k, v in data.get("loot_hidden", {}).items()}

            self.current_room_id = rid
            room = self.rooms[rid]
            self.local_x = max(0, min(room.width - 1, int(snap.get("local_x", room.width // 2))))
            self.local_y = max(0, min(room.height - 1, int(snap.get("local_y", room.height // 2))))
            self.player.discovered_rooms.add(rid)
            self.player.explored_rooms.add(rid)
            self.is_running = True
            return True
        except Exception:
            return False

    def get_intro_lines(self) -> list[str]:
        return list(self.game_data.get("intro_text", []))

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
        nearby_lines: list[str] = []
        registry = getattr(self, "item_registry", {})

        for feat in getattr(room, "features", []):
            fx, fy = feat.get("pos", (-1, -1))
            if abs(fx - self.local_x) <= 1 and abs(fy - self.local_y) <= 1:
                nearby_lines.append(f"[nearby] {feat.get('desc', '')}")
                break

        for item, pos in self._item_positions(room).items():
            ix, iy = pos
            if abs(ix - self.local_x) <= 1 and abs(iy - self.local_y) <= 1:
                item_data = registry.get(item, {})
                desc = item_data.get("desc", "")
                name = item.replace("_", " ")
                item_line = f"[nearby item] {name}."
                if desc:
                    item_line += f" {desc}"
                nearby_lines.append(item_line)
                nearby_lines.append(f"Type take {item} or examine {item}.")
                break

        if nearby_lines:
            return "\n".join(nearby_lines)
        return None

    def _item_positions(self, room) -> dict[str, tuple[int, int]]:
        """Best-effort local item positions for nearby item hints."""
        visible_items = list(room.visible_loot().keys())
        if not visible_items:
            return {}

        positions: dict[str, tuple[int, int]] = {}
        feature_pos = {f.get("id"): f.get("pos", (-1, -1)) for f in getattr(room, "features", [])}
        used: set[tuple[int, int]] = set()

        # Prefer hint-linked feature positions when available.
        for item in visible_items:
            feat_id = room.loot_hint.get(item)
            if feat_id and feat_id in feature_pos:
                px, py = feature_pos[feat_id]
                px = max(0, min(room.width - 1, int(px)))
                py = max(0, min(room.height - 1, int(py)))
                positions[item] = (px, py)
                used.add((px, py))

        # Fallback cluster near the lower middle, similar to map item markers.
        unplaced = [item for item in visible_items if item not in positions]
        if not unplaced:
            return positions

        row = min(room.height - 1, max(0, room.height // 2 + 2))
        half = len(unplaced) // 2
        for idx, item in enumerate(unplaced):
            x = room.width // 2 + idx - half
            x = max(0, min(room.width - 1, x))
            pos = (x, row)
            if pos in used:
                found = None
                for dx in range(1, room.width):
                    for cand in ((x + dx, row), (x - dx, row)):
                        cx, cy = cand
                        if 0 <= cx < room.width and (cx, cy) not in used:
                            found = (cx, cy)
                            break
                    if found:
                        break
                if found:
                    pos = found
            positions[item] = pos
            used.add(pos)
        return positions

    def _add_to_inventory(self, item: str, count: int = 1):
        self.player.inventory[item] = self.player.inventory.get(item, 0) + count


    def describe_current_room(self) -> list[str]:
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        self.player.discovered_rooms.add(room.id)
        registry = getattr(self, "item_registry", {})
        desc  = room.get_description(self.player.inventory)
        lines = [f"\n{room.name}", desc]
        if room.exits:
            lines.append(f"Exits: {', '.join(sorted(room.exits.keys()))}")
        for item, count in room.visible_loot().items():
            item_data = registry.get(item, {})
            d = item_data.get("desc", "")
            lines.append(f"You see a {item.replace('_',' ')} here. {d}")
        carried = self.player.carried_weight(registry)
        limit   = self.player.carry_limit(registry)
        if carried >= limit > 0:
            lines.append("Your pack is full. You can barely move.")
        elif limit > 0 and carried >= limit * 0.85:
            lines.append("Your pack is heavy. Every step costs you.")
        hint = self._context_hint(room)
        if hint:
            lines.append(hint)
        return lines

    def _context_hint(self, room) -> str | None:
        inv = self.player.inventory
        if room.id == "clearing":
            if inv.get("machete", 0) <= 0:
                return "Hint: take the machete and note in this clearing, then go north."
            if inv.get("lantern", 0) <= 0 or inv.get("climbing_gear", 0) <= 0:
                return "Hint: go north and enter the cabin to gather a lantern and climbing gear."
            if inv.get("climbing_gear", 0) > 0:
                return "Hint: go west to climb the cliff and see the lighthouse."
        if room.id == "thick_forest":
            if room.loot_hidden.get("lantern", False) or room.loot_hidden.get("climbing_gear", False):
                return "Hint: try enter cabin or examine cabin to search inside."
        if room.id == "cave_entrance":
            return "Hint: examine the flat stone to read the cave painting clue."
        if room.id == "riverbank":
            if inv.get("raft", 0) <= 0:
                return "Hint: go north, enter the cabin, and take the raft. Then use raft here to cross south."
            return "Hint: use raft to cross south to the far shore."
        if room.id == "mountain_pass":
            return "Hint: examine the lighthouse and cliff edge to confirm the river meets the bay."
        return None

    def handle_help(self) -> list[str]:
        return [
            "Objective: reach the lighthouse.",
            "Movement: arrow keys or go north/south/east/west (n/s/e/w).",
            "Core commands: look, examine <thing>, enter <feature>, take <item>, use <item>, read <item>, inventory, hint.",
            "Crafting prep: gather <wood|stone|food>, and drop <item> when you need space.",
            "Map and menus: m opens map, i opens inventory, save or F5 saves now, esc returns to menu.",
            "When you move near an item, chat shows [nearby item] with what it is and how to interact.",
            "Natural input works too: pick up raft, look at rope post, move north, go to cave.",
        ]

    def handle_hint(self) -> list[str]:
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        hint = self._context_hint(room)
        if hint:
            return [hint]
        return ["Hint: examine nearby features and read any notes or maps you find."]

    def handle_enter(self, target) -> list[str]:
        if not target:
            return ["Enter what? Example: enter cabin"]
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        for feat in room.features:
            if feat["id"] == target or feat["label"].lower() == target:
                lines = [f"You step into the {feat['id'].replace('_',' ')}."]
                # Reuse examine so entering and searching share reveal behavior.
                extra = self.handle_examine(feat["id"])
                if extra and extra[0].startswith("You look closely"):
                    extra = extra[1:]
                return lines + extra
        return [f"You cannot enter the {target.replace('_',' ')} here."]


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
        if verb == "help":
            return self.handle_help()
        if verb == "hint":
            return self.handle_hint()
        if verb == "inventory":
            return self.player.get_inventory_lines(self.item_registry)
        if verb == "go":
            return self.handle_go(target)
        if verb == "gather":
            return self.handle_gather(target)
        if verb == "take":
            return self.handle_take(target)
        if verb == "craft":
            return self.handle_craft(target)
        if verb == "examine":
            return self.handle_examine(target)
        if verb == "enter":
            return self.handle_enter(target)
        if verb == "drop":
            return self.handle_drop(target)
        if verb == "read":
            return self.handle_read(target)
        if verb == "use":
            return self.handle_use(target)
        if verb == "combine":
            return self.handle_combine(target)
        known = [
            "look", "help", "hint", "go", "gather", "take", "craft",
            "examine", "enter", "drop", "read", "use", "combine", "inventory", "quit",
        ]
        guess = difflib.get_close_matches(verb, known, n=1, cutoff=0.60)
        if guess:
            return [
                f"Unknown command: {verb}. Did you mean {guess[0]}?",
                "Type help for controls and examples.",
            ]
        return [
            f"Unknown command: {verb}.",
            "Type help for controls and examples.",
        ]


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
                # Weight slowdown
                registry = getattr(self, "item_registry", {})
                carried = self.player.carried_weight(registry)
                limit   = self.player.carry_limit(registry)
                lines   = []
                if carried >= limit:
                    lines.append("You strain under the weight but drag yourself forward.")
                else:
                    lines.append(f"You move {target}.")
                if flavour:
                    lines.append(flavour)
                lines.extend(self._tick_torch())
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
        self._add_to_inventory(target, amount)
        return [f"You gather {target}."]


    def handle_take(self, target) -> list[str]:
        if not target:
            return ["Take what? Example: take machete"]
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        available = room.loot.get(target, 0)
        if available <= 0:
            # Check if it was already picked up
            if self.player.inventory.get(target, 0) > 0:
                return [f"You already have the {target.replace('_',' ')}."]
            return [f"There is no {target.replace('_',' ')} here."]
        # Hidden items can't be taken until revealed by examine
        if room.loot_hidden.get(target, False):
            return [f"You can't see anything like that. Try examining the area more carefully."]
        # Pick it up
        room.loot[target] -= 1
        if room.loot[target] <= 0:
            del room.loot[target]
        self._add_to_inventory(target, 1)
        item_data = self.item_registry.get(target, {})
        desc = item_data.get("desc", "")
        lines = [f"You pick up the {target.replace('_',' ')}."]
        if desc:
            lines.append(desc)
        if item_data.get("carry_bonus"):
            bonus = item_data["carry_bonus"]
            new_limit = self.player.carry_limit(getattr(self, "item_registry", {}))
            lines.append(f"Your carry limit increased to {int(new_limit)} kg.")
        if item_data.get("uses"):
            self.player.torch_uses = item_data["uses"]
        return lines


    def handle_examine(self, target) -> list[str]:
        if not target:
            return ["Examine what? Example: examine boulder"]
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]

        # Check features first
        for feat in room.features:
            if feat["id"] == target or feat["label"].lower() == target:
                lines = [f"You look closely at the {feat['id'].replace('_',' ')}."]
                lines.append(feat.get("desc", ""))
                # Examine clue: the extra detail reward
                clue = feat.get("examine_clue", "")
                if clue:
                    lines.append(clue)
                # Reveal any hidden loot tied to this feature
                revealed = room.reveal_loot_for_feature(feat["id"])
                for item in revealed:
                    item_data = self.item_registry.get(item, {})
                    desc = item_data.get("desc", "")
                    lines.append(f"You find a {item.replace('_',' ')} here. {desc}")
                    lines.append(f"Type  take {item.replace('_',' ')}  to pick it up.")
                return lines

        # Check inventory first: carried item takes priority over ground loot
        if self.player.inventory.get(target, 0) > 0:
            item_data = self.item_registry.get(target, {})
            w = item_data.get("weight", 0)
            return [f"You examine your {target.replace('_',' ')}.",
                    item_data.get("desc", "Nothing special."),
                    f"Weight: {w} kg"]

        # Check visible loot items
        if target in room.loot and room.loot[target] > 0:
            if not room.loot_hidden.get(target, False):
                item_data = self.item_registry.get(target, {})
                return [f"You look at the {target.replace('_',' ')}.",
                        item_data.get("desc", "No further detail."),
                        f"Type  take {target}  to pick it up."]

        return [f"You don't see any {target.replace('_',' ')} to examine."]


    def handle_drop(self, target) -> list[str]:
        if not target:
            return ["Drop what? Example: drop wood"]
        count = self.player.inventory.get(target, 0)
        if count <= 0:
            return [f"You are not carrying any {target.replace('_',' ')}."]
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        # Remove one from inventory, add to room loot
        self.player.inventory[target] -= 1
        room.loot[target] = room.loot.get(target, 0) + 1
        # Make it visible if it was hidden
        room.loot_hidden[target] = False
        return [f"You drop the {target.replace('_',' ')}.",
                "It lands on the ground. You can take it again if you change your mind."]


    def handle_craft(self, target) -> list[str]:
        if not target:
            return ["Craft what? Example: craft raft"]
        if target not in self.recipes:
            return [f"You don't know how to craft a {target}."]
        recipe = self.recipes[target]
        required = recipe.get("requires", {})
        # Check all ingredients first
        for ingredient, amount in required.items():
            have = self.player.inventory.get(ingredient, 0)
            if have < amount:
                return [f"You need {amount} {ingredient} to craft a {target}. You have {have}."]
        # Deduct ingredients
        for ingredient, amount in required.items():
            self.player.inventory[ingredient] -= amount
        # Add crafted item
        self._add_to_inventory(target, 1)
        item_data = self.item_registry.get(target, {})
        desc = item_data.get("desc", "")
        lines = [f"You craft a {target}."]
        if desc:
            lines.append(desc)
        return lines


    def handle_read(self, target) -> list[str]:
        if not target:
            for item, count in self.player.inventory.items():
                if count > 0 and self.item_registry.get(item, {}).get("readable"):
                    target = item
                    break
            if not target:
                return ["You are not carrying anything readable."]
        if self.player.inventory.get(target, 0) <= 0:
            room = self.get_current_room()
            if room and room.loot.get(target, 0) > 0 and not room.loot_hidden.get(target, False):
                pass
            else:
                return [f"You are not carrying a {target.replace('_', ' ')}."]
        item_data = self.item_registry.get(target, {})
        if not item_data.get("readable"):
            return [f"You cannot read the {target.replace('_', ' ')}."]
        text_key = f"{target}_text"
        text_lines = self.game_data.get(text_key, self.game_data.get("note_text", ["The page is blank."]))
        return [f"\n--- {target.replace('_', ' ').upper()} ---"] + text_lines + ["---"]


    def handle_use(self, target) -> list[str]:
        if not target:
            return ["Use what? Example: use raft"]
        if self.player.inventory.get(target, 0) <= 0:
            return [f"You are not carrying a {target.replace('_', ' ')}."]
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        _use_messages: dict[str, str] = {
            "raft":          "You drag the raft to the bank and push off into the current. The river fights you, but you make it across.",
            "machete":       "You raise the machete and hack through the tangled brambles. Thorns tear your sleeves but you force a path through.",
            "climbing_gear": "You snap the hooks into a crack in the rock, test your weight, and begin to climb. The cold face yields slowly.",
            "axe":           "You swing into the dense undergrowth, each stroke cutting a few feet more. The dark closes in but you keep chopping.",
        }
        for direction, next_id in room.exits.items():
            dest = self.rooms.get(next_id)
            if dest and dest.requires:
                for req in dest.requires:
                    if req.get("type") == "item" and req.get("item") == target:
                        msg = _use_messages.get(target, f"You use the {target.replace('_', ' ')}.")
                        lines = [msg]
                        lines.extend(self.handle_go(direction))
                        return lines
        item_data = self.item_registry.get(target, {})
        desc = item_data.get("desc", "")
        return [
            f"You hold the {target.replace('_', ' ')} in your hands.",
            desc if desc else "Nothing here needs it right now.",
        ]

    def handle_combine(self, target) -> list[str]:
        if not target:
            return ["Combine what? Example: combine rope hook"]
        parts = target.strip().split()
        if len(parts) < 2:
            return ["Combine needs two items. Example: combine rope hook"]
        a, b = parts[0], parts[1]
        key  = f"{a}+{b}"
        recipes = self.game_data.get("combine_recipes", {})
        if key not in recipes:
            return [f"You cannot combine {a} and {b}."]
        recipe = recipes[key]
        # Check both items in inventory
        for item in (a, b):
            if self.player.inventory.get(item, 0) <= 0:
                return [f"You are not carrying any {item.replace('_',' ')}."]
        # Consume one of each
        self.player.inventory[a] -= 1
        self.player.inventory[b] -= 1
        result = recipe["result"]
        self._add_to_inventory(result, 1)
        desc = recipe.get("desc", "")
        lines = [f"You combine the {a.replace('_',' ')} and {b.replace('_',' ')}."]
        if desc:
            lines.append(desc)
        lines.append(f"You now have: {result.replace('_',' ')}.")
        return lines


    def _tick_torch(self) -> list[str]:
        light_item = None
        if self.player.inventory.get("torch", 0) > 0:
            light_item = "torch"
        elif self.player.inventory.get("lantern", 0) > 0:
            light_item = "lantern"
        if light_item is None:
            return []
        if self.player.torch_uses is None:
            max_uses = self.item_registry.get(light_item, {}).get("uses", 15)
            self.player.torch_uses = max_uses
        self.player.torch_uses -= 1
        if self.player.torch_uses <= 0:
            self.player.inventory[light_item] -= 1
            self.player.torch_uses = None
            return [f"Your {light_item} gutters and dies. You are in darkness."]
        if self.player.torch_uses == 3:
            return [f"Your {light_item} is almost out."]
        if self.player.torch_uses == 7:
            return [f"Your {light_item} is burning low."]
        return []
