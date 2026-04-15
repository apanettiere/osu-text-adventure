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
    "river_run":      (8, 25),
    "river_lake":     (52, 30),
    "cave_entrance":  (33, 16),
    "cabin_interior": (38, -2),
    "cave_chamber":   (37, 7),
    "far_shore":      (21, 47),
    "mountain_pass":  (-2, 16),
    "lighthouse_interior": (-1, 5),
    "lighthouse_top":      (-2, -6),
}

REVEAL_RADIUS = 2

ENTER_TARGET_ALIASES: dict[str, str] = {
    "tower": "lighthouse",
    "stairs": "spiral_stairs",
    "staircase": "spiral_stairs",
    "top": "spiral_stairs",
    "upstairs": "spiral_stairs",
    "cave": "cave_tunnel",
    "tunnel": "cave_tunnel",
    "chamber": "cave_tunnel",
}


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
        self.game_outcome: str | None = None
        self.end_lines: list[str] = []

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
        self._repair_progression_items()


    def get_current_room(self):
        return self.rooms.get(self.current_room_id)

    def _item_exists_anywhere(self, item: str) -> bool:
        if self.player.inventory.get(item, 0) > 0:
            return True
        for room in self.rooms.values():
            if room.loot.get(item, 0) > 0:
                return True
        return False

    def _ensure_progression_item(self, item: str, room_id: str):
        if self._item_exists_anywhere(item):
            return
        room = self.rooms.get(room_id)
        if not room:
            return
        room.loot[item] = max(1, int(room.loot.get(item, 0)))
        room.loot_hidden[item] = False

    def _repair_progression_items(self):
        # Save migration safety: keep critical progression items available.
        self._ensure_progression_item("lantern", "cabin_interior")
        self._ensure_progression_item("raft", "cabin_interior")
        # Keep an extra visible raft near the river once players discover that zone.
        if ("riverbank" in self.player.discovered_rooms) and self.player.inventory.get("raft", 0) <= 0:
            riverbank = self.rooms.get("riverbank")
            if riverbank:
                riverbank.loot["raft"] = max(1, int(riverbank.loot.get("raft", 0)))
                riverbank.loot_hidden["raft"] = False
        # Keep climbing gear in the cabin with other core tools.
        cabin = self.rooms.get("cabin_interior")
        misplaced = 0
        for rid in ("cave_entrance", "cave_chamber"):
            room = self.rooms.get(rid)
            if not room:
                continue
            misplaced += int(room.loot.pop("climbing_gear", 0))
            room.loot_hidden.pop("climbing_gear", None)
        if self.player.inventory.get("climbing_gear", 0) <= 0:
            if cabin:
                cabin.loot["climbing_gear"] = max(1, int(cabin.loot.get("climbing_gear", 0)), misplaced)
                cabin.loot_hidden["climbing_gear"] = False
            else:
                self._ensure_progression_item("climbing_gear", "cabin_interior")

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
            self.game_outcome = None
            self.end_lines = []
            self._repair_progression_items()
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
            if inv.get("lantern", 0) <= 0:
                return "Hint: go north and enter the cabin to grab the lantern."
            if inv.get("climbing_gear", 0) <= 0:
                return "Hint: go north and enter the cabin to pick up climbing gear with the raft."
            return "Hint: go west to reach the cliff shelf and the lighthouse approach."
        if room.id == "thick_forest":
            return "Hint: enter cabin to search inside for supplies."
        if room.id == "cabin_interior":
            return "Hint: take the lantern, raft, and climbing gear here, then go south to return outside."
        if room.id == "cave_entrance":
            return "Hint: examine the flat stone for the map clue and enter cave tunnel to explore deeper."
        if room.id == "cave_chamber":
            return "Hint: explore the chamber features, then go west to return to the cave entrance."
        if room.id == "riverbank":
            if inv.get("raft", 0) <= 0:
                return "Hint: south leads to the lake edge. To follow the river west toward sea spray, take the raft first."
            return "Hint: with the raft, go west to ride the river run toward the sea cliffs."
        if room.id == "river_run":
            return "Hint: this is the main river current. East returns to the riverbank launch, west heads toward the bay mouth."
        if room.id == "river_lake":
            if inv.get("raft", 0) <= 0:
                return "Hint: move north back to riverbank. South opens into deeper water and needs the raft."
            return "Hint: move north to riverbank or south across deep water to the far shore."
        if room.id == "mountain_pass":
            return "Hint: enter lighthouse, then climb to the top and light the signal."
        if room.id == "lighthouse_interior":
            return "Hint: enter spiral stairs to reach the lantern room at the top."
        if room.id == "lighthouse_top":
            return "Hint: use lantern or light lighthouse light to send SOS."
        return None

    def _blocked_edge_message(self, room) -> str:
        if not room:
            return "You cannot go that way."
        if room.id in {"cave_entrance", "cave_chamber"}:
            return "Stone walls close in. You cannot go that way."
        if room.id in {"riverbank", "river_run", "river_lake", "far_shore"}:
            return "Water blocks that route. You cannot go that way."
        return "The trees press in close. You cannot go that way."

    def handle_help(self) -> list[str]:
        return [
            "Objective: reach the lighthouse top and signal SOS.",
            "Movement: arrow keys or go north/south/east/west (n/s/e/w).",
            "Core commands: look, examine <thing>, enter <feature>, take <item>, use <item>, read <item>, inventory, hint.",
            "Crafting prep: gather <wood|stone|food>, craft or craft list, and drop <item> when you need space.",
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

    def _resolve_enter_target(self, target: str) -> str:
        return ENTER_TARGET_ALIASES.get(target, target)

    def _requirement_block_message(self, room) -> str | None:
        if not room or not room.requires:
            return None
        for req in room.requires:
            if req.get("type") != "item":
                continue
            item = req.get("item")
            amount = int(req.get("amount", 1))
            if int(self.player.inventory.get(item, 0)) < amount:
                return req.get("message", "You cannot go there yet.")
        return None

    def _move_to_room_from_feature(self, next_room_id: str) -> list[str]:
        dest = self.rooms.get(next_room_id)
        if not dest:
            return ["Error: feature points to a missing room in game.json"]

        blocked = self._requirement_block_message(dest)
        if blocked:
            self.player.discovered_rooms.add(next_room_id)
            return [blocked]

        if next_room_id not in self.player.room_positions:
            self.player.room_positions[next_room_id] = self.player.room_positions.get(self.current_room_id, (0, 0))

        self.player.current_pos = self.player.room_positions.get(next_room_id, (0, 0))
        self.player.discovered_rooms.add(next_room_id)
        self.player.explored_rooms.add(next_room_id)
        self.current_room_id = next_room_id

        if dest.is_walkable:
            self.local_x = dest.width // 2
            self.local_y = dest.height // 2
        else:
            self.local_x = 0
            self.local_y = 0
        self._mark_visited()
        return self.describe_current_room()

    def _handle_lighthouse_victory(self, target: str) -> list[str] | None:
        if self.current_room_id != "lighthouse_top":
            return None
        valid_targets = {
            "lantern",
            "torch",
            "signal_brazier",
            "signal_lens",
            "lighthouse_light",
            "light",
            "sos",
            "fire",
            "beacon",
        }
        if target not in valid_targets:
            return None

        lines = [
            "You strike the dry fuel in the lantern room and the fire catches.",
            "The lighthouse lens turns and a white beam punches through the dark sky.",
            "You signal three long, three short, three long flashes: SOS.",
            "A small seaplane roars in low, skims the bay, and lands on the dark water below.",
            "As dawn breaks, the clouds open and the whole sky lights up above the lighthouse.",
            "You made it. Rescue has arrived.",
        ]
        self.game_outcome = "won"
        self.end_lines = list(lines)
        self.is_running = False
        return lines

    def handle_enter(self, target) -> list[str]:
        if not target:
            return ["Enter what? Example: enter cabin"]
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        raw_target = str(target).strip().lower().replace(" ", "_")
        if room.id == "clearing" and raw_target in {"cave", "cave_entrance", "cave_tunnel", "tunnel", "chamber"}:
            return self._move_to_room_from_feature("cave_entrance")
        target = self._resolve_enter_target(target)
        if room.id in {"riverbank", "river_lake", "far_shore", "mountain_pass"} and target in {"river", "water", "lake", "channel", "bay", "sea", "ocean"}:
            if target in {"bay", "sea", "ocean"} and self.player.inventory.get("raft", 0) <= 0:
                return ["That water is deep. You need the raft for open water crossings."]
            if self.player.inventory.get("raft", 0) > 0:
                return self.handle_use("raft")
            return ["You step into the shallows. Move with go north, south, east, or west."]
        for feat in room.features:
            if feat["id"] == target or feat["label"].lower() == target:
                revealed = room.reveal_loot_for_feature(feat["id"])
                destination = feat.get("enter_to")
                if destination:
                    lines = [f"You step into the {feat['id'].replace('_',' ')}."]
                    for item in revealed:
                        item_data = self.item_registry.get(item, {})
                        desc = item_data.get("desc", "")
                        lines.append(f"You find a {item.replace('_',' ')} here. {desc}")
                        lines.append(f"Type  take {item.replace('_',' ')}  to pick it up.")
                    lines.extend(self._move_to_room_from_feature(destination))
                    return lines
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
            self.game_outcome = "quit"
            self.end_lines = ["Goodbye."]
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
            enter_target = self._resolve_enter_target(target)
            if any(feat["id"] == enter_target or feat["label"].lower() == enter_target for feat in room.features):
                return self.handle_enter(enter_target)
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
                return [self._blocked_edge_message(room)]
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

        # Water approach to mountain pass is a separate route from the cliff climb.
        # Keep climbing gear required from the forest side, but require raft from lake side.
        water_to_pass = (
            next_room_id == "mountain_pass"
            and self.current_room_id in {"river_lake", "far_shore", "river_run"}
        )
        if water_to_pass and self.player.inventory.get("raft", 0) <= 0:
            self.player.discovered_rooms.add(next_room_id)
            return ["The bay current is too deep and rough here. You need the raft to head west."]

        blocked = None if water_to_pass else self._requirement_block_message(dest_room)
        if blocked:
            self.player.discovered_rooms.add(next_room_id)
            return [blocked]

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


    def _format_recipe_requires(self, required: dict) -> str:
        parts: list[str] = []
        for ingredient, amount in required.items():
            parts.append(f"{int(amount)} {ingredient.replace('_', ' ')}")
        return ", ".join(parts) if parts else "nothing"

    def _crafting_recipe_lines(self) -> list[str]:
        if not self.recipes:
            return ["You do not know any recipes yet."]
        lines = ["Crafting recipes:"]
        for recipe_name in sorted(self.recipes.keys()):
            recipe = self.recipes.get(recipe_name, {})
            requires = recipe.get("requires", {})
            needs = self._format_recipe_requires(requires)
            weight = self.item_registry.get(recipe_name, {}).get("weight")
            weight_suffix = f" | {weight:g} kg" if weight is not None else ""
            lines.append(f"  {recipe_name.replace('_', ' ')}: {needs}{weight_suffix}")
        lines.append("Type craft <item>. Example: craft spear")
        return lines

    def handle_craft(self, target) -> list[str]:
        if not self.recipes:
            return ["You do not know any recipes yet."]
        if not target or target in {"list", "recipes", "all", "?"}:
            return self._crafting_recipe_lines()
        target = str(target).strip().lower().replace(" ", "_")
        if target not in self.recipes:
            known = sorted(self.recipes.keys())
            guess = difflib.get_close_matches(target, known, n=1, cutoff=0.60)
            if guess:
                return [f"You don't know how to craft {target.replace('_', ' ')}. Try: craft {guess[0].replace('_', ' ')}."]
            return [f"You don't know how to craft {target.replace('_', ' ')}.", "Type craft to list recipes."]
        recipe = self.recipes[target]
        required = recipe.get("requires", {})
        if not required:
            return [f"The {target.replace('_', ' ')} recipe is missing ingredients data."]
        for ingredient, amount in required.items():
            have = self.player.inventory.get(ingredient, 0)
            need = int(amount)
            if have < need:
                return [f"You need {need} {ingredient.replace('_', ' ')} to craft {target.replace('_', ' ')}. You have {have}."]
        for ingredient, amount in required.items():
            self.player.inventory[ingredient] -= int(amount)
        self._add_to_inventory(target, 1)
        item_data = self.item_registry.get(target, {})
        desc = item_data.get("desc", "")
        lines = [f"You craft {target.replace('_', ' ')}."]
        if desc:
            lines.append(desc)
        carried = self.player.carried_weight(self.item_registry)
        limit = self.player.carry_limit(self.item_registry)
        lines.append(f"Carry weight: {carried:g} / {int(limit)} kg.")
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
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]

        win_lines = self._handle_lighthouse_victory(target)
        if win_lines is not None:
            return win_lines

        if self.player.inventory.get(target, 0) <= 0:
            return [f"You are not carrying a {target.replace('_', ' ')}."]
        _use_messages: dict[str, str] = {
            "raft":          "You pull the raft into position and steady it for deeper crossings.",
            "machete":       "You raise the machete and hack through the tangled brambles. Thorns tear your sleeves but you force a path through.",
            "climbing_gear": "You snap the hooks into a crack in the rock, test your weight, and begin to climb. The cold face yields slowly.",
            "axe":           "You swing into the dense undergrowth, each stroke cutting a few feet more. The dark closes in but you keep chopping.",
        }

        raft_nav_rooms = {"riverbank", "river_lake", "far_shore", "mountain_pass"}

        if target == "raft" and room.id in raft_nav_rooms:
            return [
                "You brace your feet and climb onto the raft.",
                "Use go north, go south, go east, or go west to steer.",
            ]

        eligible: list[tuple[str, str]] = []
        for direction, next_id in room.exits.items():
            dest = self.rooms.get(next_id)
            if dest and dest.requires:
                for req in dest.requires:
                    if req.get("type") == "item" and req.get("item") == target:
                        eligible.append((direction, next_id))
                        break

        if eligible:
            # Prefer river navigation route when using raft at riverbank.
            chosen_dir = eligible[0][0]
            if target == "raft":
                preferred = ["east", "south", "west", "north"]
                if room.id == "riverbank":
                    dirs = [d for d, _ in eligible]
                    if self._at_exit_edge("south", room) and "south" in dirs:
                        chosen_dir = "south"
                    elif self._at_exit_edge("east", room) and "east" in dirs:
                        chosen_dir = "east"
                    else:
                        for pd in preferred:
                            if pd in dirs:
                                chosen_dir = pd
                                break
                else:
                    dirs = [d for d, _ in eligible]
                    for pd in preferred:
                        if pd in dirs:
                            chosen_dir = pd
                            break

            # Force edge alignment so "use raft" or "use climbing_gear" triggers traversal immediately.
            if room.is_walkable:
                if chosen_dir == "north":
                    self.local_y = 0
                elif chosen_dir == "south":
                    self.local_y = room.height - 1
                elif chosen_dir == "east":
                    self.local_x = room.width - 1
                elif chosen_dir == "west":
                    self.local_x = 0

            msg = _use_messages.get(target, f"You use the {target.replace('_', ' ')}.")
            lines = [msg]
            lines.extend(self.handle_go(chosen_dir))
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
            if light_item == "lantern":
                # Keep the lantern as a persistent tool; it can be re-lit with reserve oil.
                max_uses = int(self.item_registry.get("lantern", {}).get("uses", 30))
                self.player.torch_uses = max_uses
                return ["Your lantern sputters out, then you trim the wick and relight it from reserve oil."]
            self.player.inventory[light_item] -= 1
            self.player.torch_uses = None
            return [f"Your {light_item} gutters and dies. You are in darkness."]
        if self.player.torch_uses == 3:
            return [f"Your {light_item} is almost out."]
        if self.player.torch_uses == 7:
            return [f"Your {light_item} is burning low."]
        return []
