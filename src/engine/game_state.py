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

MAP_ROOM_POS: dict[str, tuple[int,int]] = {
    "shadow_trees":    (13, 0),
    "clearing":        (14, 12),
    "soggy_path":      (17, 28),
    "stone_foothills": (30, 14),
    "fallen_pines":    (0,  14),
}

REVEAL_RADIUS = 2


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
        if verb == "drop":
            return self.handle_drop(target)
        if verb == "read":
            return self.handle_read(target)
        if verb == "combine":
            return self.handle_combine(target)
        return ["Unknown command. Try: look, go, gather, take, examine, drop, craft, read, combine, inventory"]


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
                # Examine clue — the extra detail reward
                clue = feat.get("examine_clue", "")
                if clue:
                    lines.append(clue)
                # Reveal any hidden loot tied to this feature
                revealed = room.reveal_loot_for_feature(feat["id"])
                for item in revealed:
                    item_data = self.item_registry.get(item, {})
                    desc = item_data.get("desc", "")
                    lines.append(f"You find a {item.replace('_',' ')} here. {desc}")
                    lines.append(f"Type  take {item}  to pick it up.")
                return lines

        # Check visible loot items
        if target in room.loot and room.loot[target] > 0:
            if not room.loot_hidden.get(target, False):
                item_data = self.item_registry.get(target, {})
                return [f"You look at the {target.replace('_',' ')}.",
                        item_data.get("desc", "No further detail."),
                        f"Type  take {target}  to pick it up."]

        # Check inventory items
        if self.player.inventory.get(target, 0) > 0:
            item_data = self.item_registry.get(target, {})
            w = item_data.get("weight", 0)
            return [f"You examine your {target.replace('_',' ')}.",
                    item_data.get("desc", "Nothing special."),
                    f"Weight: {w} kg"]

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
            target = "note"  # default: read note
        # Check inventory
        if self.player.inventory.get(target, 0) <= 0:
            # Check ground
            room = self.get_current_room()
            if room and room.loot.get(target, 0) > 0 and not room.loot_hidden.get(target, False):
                pass  # can read from ground without picking up
            else:
                return [f"You are not carrying a {target.replace('_',' ')}."]
        item_data = self.item_registry.get(target, {})
        if not item_data.get("readable"):
            return [f"You cannot read the {target.replace('_',' ')}."]
        note_lines = self.game_data.get("note_text", ["The page is blank."])
        return [f"\n--- {target.replace('_',' ').upper()} ---"] + note_lines + ["---"]


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

    # ── torch use tracking ────────────────────────────────────────────────────

    def _tick_torch(self) -> list[str]:
        """Call each move when player has a torch. Returns warning lines if burning low."""
        if self.player.inventory.get("torch", 0) <= 0:
            return []
        if self.player.torch_uses is None:
            max_uses = self.item_registry.get("torch", {}).get("uses", 15)
            self.player.torch_uses = max_uses
        self.player.torch_uses -= 1
        if self.player.torch_uses <= 0:
            self.player.inventory["torch"] -= 1
            self.player.torch_uses = None
            return ["Your torch gutters and dies. You are in darkness."]
        if self.player.torch_uses == 3:
            return ["Your torch is almost out."]
        if self.player.torch_uses == 7:
            return ["Your torch is burning low."]
        return []