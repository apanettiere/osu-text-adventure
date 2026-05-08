from __future__ import annotations

from engine.constants import encode_visited_tiles, decode_visited_tiles


class SaveMixin:

    def snapshot(self) -> dict:
        room_state = {}
        for rid, room in self.rooms.items():
            room_state[rid] = {
                "loot": dict(room.loot),
                "loot_hidden": {k: bool(v) for k, v in room.loot_hidden.items()},
            }
        return {
            "difficulty": getattr(self, "difficulty", "normal"),
            "current_room_id": self.current_room_id,
            "local_x": int(self.local_x),
            "local_y": int(self.local_y),
            "player": {
                "hp": int(self.player.hp),
                "max_hp": int(self.player.max_hp),
                "inventory": {k: int(v) for k, v in self.player.inventory.items() if int(v) > 0},
                "torch_uses": self.player.torch_uses,
                "discovered_rooms": sorted(self.player.discovered_rooms),
                "explored_rooms": sorted(self.player.explored_rooms),
                "room_positions": {
                    rid: [int(pos[0]), int(pos[1])]
                    for rid, pos in self.player.room_positions.items()
                },
                "current_pos": [int(self.player.current_pos[0]), int(self.player.current_pos[1])],
                "visited_runs": encode_visited_tiles(self.player.visited_tiles),
                "defeated_enemies": sorted(self.player.defeated_enemies),
            },
            "rooms": room_state,
        }

    def apply_snapshot(self, snap: dict) -> bool:
        try:
            rid = snap.get("current_room_id")
            if rid not in self.rooms:
                return False
            from engine.constants import DIFFICULTY_PRESETS, DEFAULT_DIFFICULTY
            diff = snap.get("difficulty", DEFAULT_DIFFICULTY)
            if diff not in DIFFICULTY_PRESETS:
                diff = DEFAULT_DIFFICULTY
            preset = DIFFICULTY_PRESETS[diff]
            self.difficulty = diff
            self.enemy_damage_mult = float(preset["enemy_damage_mult"])
            self.gather_mult = int(preset["gather_mult"])
            p = snap.get("player", {})
            self.player.hp = int(p.get("hp", self.player.max_hp))
            self.player.max_hp = int(p.get("max_hp", self.player.max_hp))
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
                self.player.visited_tiles = decode_visited_tiles(p.get("visited_runs", []))
            else:
                self.player.visited_tiles = set()
                for tile in p.get("visited_tiles", []):
                    if isinstance(tile, (list, tuple)) and len(tile) == 2:
                        self.player.visited_tiles.add((int(tile[0]), int(tile[1])))
            self.player.defeated_enemies = set(p.get("defeated_enemies", []))

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
