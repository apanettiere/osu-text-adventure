from __future__ import annotations

from engine.constants import (
    DIRECTION_DELTAS,
    ENTRY_SPAWN,
    MAP_ROOM_POS,
    REVEAL_RADIUS,
    LIGHT_SOURCES,
)


class MovementMixin:

    def _world_pos(self) -> tuple[int, int] | None:
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
        visible_items = list(room.visible_loot().keys())
        if not visible_items:
            return {}

        positions: dict[str, tuple[int, int]] = {}
        feature_pos = {f.get("id"): f.get("pos", (-1, -1)) for f in getattr(room, "features", [])}
        used: set[tuple[int, int]] = set()

        for item in visible_items:
            feat_id = room.loot_hint.get(item)
            if feat_id and feat_id in feature_pos:
                px, py = feature_pos[feat_id]
                px = max(0, min(room.width - 1, int(px)))
                py = max(0, min(room.height - 1, int(py)))
                positions[item] = (px, py)
                used.add((px, py))

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
                for ddx in range(1, room.width):
                    for cand in ((x + ddx, row), (x - ddx, row)):
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

    def _blocked_edge_message(self, room) -> str:
        if not room:
            return "You cannot go that way."
        if room.id in {"cave_entrance", "cave_chamber"}:
            return "Stone walls close in. You cannot go that way."
        if room.id in {"riverbank", "river_run", "river_lake", "far_shore", "open_waters"}:
            return "Water blocks that route. You cannot go that way."
        return "The trees press in close. You cannot go that way."

    def _requirement_block_message(self, room) -> str | None:
        if not room or not room.requires:
            return None
        for req in room.requires:
            if req.get("type") != "item":
                continue
            item = req.get("item")
            amount = int(req.get("amount", 1))
            if int(self.player.inventory.get(item, 0)) >= amount:
                continue
            if item in LIGHT_SOURCES:
                if any(int(self.player.inventory.get(alt, 0)) >= amount for alt in LIGHT_SOURCES):
                    continue
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

    def handle_leave(self) -> list[str]:
        room = self.get_current_room()
        if not room:
            return ["Error: current room not found."]
        if not room.exits:
            return ["There is no obvious way out from here."]
        exits = list(room.exits.items())
        if len(exits) == 1:
            direction, _ = exits[0]
            if room.is_walkable and direction in ENTRY_SPAWN:
                lx, ly = ENTRY_SPAWN[direction](room.width, room.height)
                if   direction == "north": self.local_y = 0
                elif direction == "south": self.local_y = room.height - 1
                elif direction == "east":  self.local_x = room.width - 1
                elif direction == "west":  self.local_x = 0
                self._mark_visited()
            return self.handle_go(direction)
        dirs = ", ".join(sorted(room.exits.keys()))
        return [f"Leave which way? Available exits: {dirs}."]

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

        WATER_ROOMS = {"river_run", "river_lake", "far_shore", "open_waters"}

        water_to_pass = (
            next_room_id == "mountain_pass"
            and self.current_room_id in WATER_ROOMS
        )
        if water_to_pass:
            has_raft = self.player.inventory.get("raft", 0) > 0
            has_gear = self.player.inventory.get("climbing_gear", 0) > 0
            if not has_raft and not has_gear:
                self.player.discovered_rooms.add(next_room_id)
                return ["The bay current is too deep and rough here. You need the raft to head west."]

        entering_water_from_land = (
            next_room_id in WATER_ROOMS
            and self.current_room_id not in WATER_ROOMS
        )
        if entering_water_from_land:
            has_raft = self.player.inventory.get("raft", 0) > 0
            if not has_raft:
                self.player.discovered_rooms.add(next_room_id)
                return ["The water runs fast and deep. You need the raft to cross."]

        blocked = None if water_to_pass else self._requirement_block_message(dest_room)
        if blocked:
            self.player.discovered_rooms.add(next_room_id)
            return [blocked]

        self.player.current_pos = (nx, ny)
        self.player.discovered_rooms.add(next_room_id)
        self.player.explored_rooms.add(next_room_id)
        source_room_id = self.current_room_id
        self.current_room_id = next_room_id

        dest = self.rooms[next_room_id]
        spawn_override = None
        for feat in getattr(dest, "features", []):
            if feat.get("enter_to") == source_room_id:
                fx, fy = feat.get("pos", (0, 0))
                sy = min(int(fy) + 1, dest.height - 1)
                sx = max(0, min(int(fx), dest.width - 1))
                spawn_override = (sx, sy)
                break
        if spawn_override is not None:
            self.local_x, self.local_y = spawn_override
        else:
            self.local_x, self.local_y = ENTRY_SPAWN[target](dest.width, dest.height)
        self._mark_visited()
        return self.describe_current_room()
