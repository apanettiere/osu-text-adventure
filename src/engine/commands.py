from __future__ import annotations

import difflib

from engine.constants import ENTER_TARGET_ALIASES


class CommandsMixin:

    def _resolve_enter_target(self, target: str) -> str:
        return ENTER_TARGET_ALIASES.get(target, target)

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
        if room.id == "far_shore":
            return "Hint: this muddy shore is a dead end. Head back west to the open waters to explore the islands."
        if room.id == "open_waters":
            if inv.get("shovel", 0) > 0:
                return "Hint: find the X marks the spot on the southern island and dig."
            return "Hint: explore the islands. The X marks buried treasure. You need a shovel from the tool shed at the riverbank."
        if room.id == "shed_interior":
            return "Hint: take the shovel here, then raft west through the river to the open waters and dig at the X on the southern island."
        if room.id == "mountain_pass":
            return "Hint: enter lighthouse, then climb to the top and light the signal."
        if room.id == "lighthouse_interior":
            return "Hint: enter spiral stairs to reach the lantern room at the top."
        if room.id == "lighthouse_top":
            return "Hint: use lantern or light lighthouse light to send SOS."
        return None

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

    def handle_help(self) -> list[str]:
        return [
            "Objective: reach the lighthouse top and signal SOS.",
            "Movement: arrow keys or go north/south/east/west (n/s/e/w).",
            "Core commands: look, examine <thing>, enter <feature>, take <item>, use <item>, read <item>, inventory, hint.",
            "Survival: eat (consume food to heal), status (check HP and weight).",
            "Crafting prep: gather <wood|stone|food>, craft or craft list, drop <item> when you need space, and dig when you have a shovel.",
            "Map and menus: m opens map, i opens inventory, save or F5 saves now, esc returns to menu.",
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
        raw_target = str(target).strip().lower().replace(" ", "_")
        if room.id == "clearing" and raw_target in {"cave", "cave_entrance", "cave_tunnel", "tunnel", "chamber"}:
            return self._move_to_room_from_feature("cave_entrance")
        target = self._resolve_enter_target(target)
        if room.id in {"riverbank", "river_lake", "far_shore", "mountain_pass", "open_waters"} and target in {"river", "water", "lake", "channel", "bay", "sea", "ocean"}:
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
                extra = self.handle_examine(feat["id"])
                if extra and extra[0].startswith("You look closely"):
                    extra = extra[1:]
                return lines + extra
        return [f"You cannot enter the {target.replace('_',' ')} here."]

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
            if self.player.inventory.get(target, 0) > 0:
                return [f"You already have the {target.replace('_',' ')}."]
            return [f"There is no {target.replace('_',' ')} here."]
        if room.loot_hidden.get(target, False):
            return [f"You can't see anything like that. Try examining the area more carefully."]
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

        for feat in room.features:
            if feat["id"] == target or feat["label"].lower() == target:
                lines = [f"You look closely at the {feat['id'].replace('_',' ')}."]
                lines.append(feat.get("desc", ""))
                clue = feat.get("examine_clue", "")
                if clue:
                    lines.append(clue)
                revealed = room.reveal_loot_for_feature(feat["id"])
                for item in revealed:
                    item_data = self.item_registry.get(item, {})
                    desc = item_data.get("desc", "")
                    lines.append(f"You find a {item.replace('_',' ')} here. {desc}")
                    lines.append(f"Type  take {item.replace('_',' ')}  to pick it up.")
                return lines

        if self.player.inventory.get(target, 0) > 0:
            item_data = self.item_registry.get(target, {})
            w = item_data.get("weight", 0)
            return [f"You examine your {target.replace('_',' ')}.",
                    item_data.get("desc", "Nothing special."),
                    f"Weight: {w} kg"]

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
        self.player.inventory[target] -= 1
        room.loot[target] = room.loot.get(target, 0) + 1
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
        missing: list[str] = []
        for ingredient, amount in required.items():
            have = self.player.inventory.get(ingredient, 0)
            need = int(amount)
            if have < need:
                missing.append(f"{need} {ingredient.replace('_', ' ')} (have {have})")
        if missing:
            return [f"Cannot craft {target.replace('_', ' ')}. You need: {', '.join(missing)}."]
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

        if target == "shovel" and self.player.inventory.get("shovel", 0) <= 0:
            return ["You don't have a shovel. There might be one in the tool shed by the riverbank."]
        if self.player.inventory.get(target, 0) <= 0:
            return [f"You are not carrying a {target.replace('_', ' ')}."]

        if target == "shovel" and room.id == "open_waters":
            revealed = room.reveal_loot_for_feature("x_marks_spot")
            if revealed:
                lines = [
                    "You drive the shovel into the loose earth beside the marked stone.",
                    "After a few minutes of digging, the blade hits something solid.",
                    "You pull a waterproof case from the mud and crack it open.",
                ]
                for item in revealed:
                    item_data = self.item_registry.get(item, {})
                    desc = item_data.get("desc", "")
                    lines.append(f"Inside: a {item.replace('_', ' ')}. {desc}")
                    lines.append(f"Type  take {item.replace('_', ' ')}  to pick it up.")
                return lines
            if room.loot.get("signal_flare", 0) <= 0 and self.player.inventory.get("signal_flare", 0) > 0:
                return ["You already dug up what was buried here."]
            return ["You dig around the marked spot but find nothing else."]

        _use_messages: dict[str, str] = {
            "raft":          "You pull the raft into position and steady it for deeper crossings.",
            "machete":       "You raise the machete and hack through the tangled brambles. Thorns tear your sleeves but you force a path through.",
            "climbing_gear": "You snap the hooks into a crack in the rock, test your weight, and begin to climb. The cold face yields slowly.",
            "axe":           "You swing into the dense undergrowth, each stroke cutting a few feet more. The dark closes in but you keep chopping.",
        }

        raft_nav_rooms = {"riverbank", "river_lake", "far_shore", "mountain_pass", "open_waters"}

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
        for item in (a, b):
            if self.player.inventory.get(item, 0) <= 0:
                return [f"You are not carrying any {item.replace('_',' ')}."]
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

    def handle_eat(self, target) -> list[str]:
        if not target:
            target = "food"
        if target != "food":
            return [f"You cannot eat the {target.replace('_', ' ')}."]
        count = self.player.inventory.get("food", 0)
        if count <= 0:
            return ["You have no food. Gather some first."]
        self.player.inventory["food"] -= 1
        healed = min(5, self.player.max_hp - self.player.hp)
        self.player.hp = min(self.player.max_hp, self.player.hp + 5)
        lines = ["You eat some foraged food."]
        if healed > 0:
            lines.append(f"You recover {healed} HP. ({self.player.hp}/{self.player.max_hp})")
        else:
            lines.append(f"You feel satisfied. ({self.player.hp}/{self.player.max_hp})")
        return lines

    def handle_save(self) -> list[str]:
        return ["Game saved."]

    def handle_status(self) -> list[str]:
        room = self.get_current_room()
        room_name = room.name if room else "Unknown"
        registry = getattr(self, "item_registry", {})
        carried = self.player.carried_weight(registry)
        limit = self.player.carry_limit(registry)
        return [
            f"\nStatus:",
            f"  Location: {room_name}",
            f"  HP: {self.player.hp}/{self.player.max_hp}",
            f"  Carry weight: {carried:g}/{int(limit)} kg",
            f"  Rooms explored: {len(self.player.explored_rooms)}",
        ]

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
