from __future__ import annotations

import difflib

from engine.models import Player
from engine.loader import load_game_data, build_room_map
from engine.constants import (
    DIRECTION_DELTAS,
    ENTRY_SPAWN,
    MAP_ROOM_POS,
    REVEAL_RADIUS,
)
from engine.movement import MovementMixin
from engine.commands import CommandsMixin
from engine.save import SaveMixin


class GameState(CommandsMixin, MovementMixin, SaveMixin):
    def __init__(self):
        self.player    = Player()
        self.game_data = load_game_data()
        self.rooms     = build_room_map(self.game_data)

        self.item_registry: dict = self.game_data.get("items", {})
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
        self._ensure_progression_item("lantern", "cabin_interior")
        self._ensure_progression_item("raft", "cabin_interior")
        if ("riverbank" in self.player.discovered_rooms) and self.player.inventory.get("raft", 0) <= 0:
            riverbank = self.rooms.get("riverbank")
            if riverbank:
                riverbank.loot["raft"] = max(1, int(riverbank.loot.get("raft", 0)))
                riverbank.loot_hidden["raft"] = False
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

    def _add_to_inventory(self, item: str, count: int = 1):
        self.player.inventory[item] = self.player.inventory.get(item, 0) + count

    def get_intro_lines(self) -> list[str]:
        return list(self.game_data.get("intro_text", []))

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

    def process_command(self, verb: str, target) -> list[str]:
        if not self.is_running:
            return []
        if verb == "leave":
            return self.handle_leave()
        if verb == "exit":
            if self.current_room_id and self.current_room_id.endswith("_interior"):
                room = self.get_current_room()
                if room and room.exits:
                    return self.handle_leave()
            self.game_outcome = "quit"
            self.end_lines = ["Goodbye."]
            self.is_running = False
            return ["Goodbye."]
        if verb == "quit":
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
        if verb == "dig":
            return self.handle_use("shovel")
        if verb == "combine":
            return self.handle_combine(target)
        if verb == "eat":
            return self.handle_eat(target)
        if verb == "save":
            return self.handle_save()
        if verb == "status":
            return self.handle_status()
        known = [
            "look", "help", "hint", "go", "gather", "take", "craft",
            "examine", "enter", "drop", "read", "use", "combine", "inventory", "quit", "dig",
            "leave", "exit", "eat", "save", "status",
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
