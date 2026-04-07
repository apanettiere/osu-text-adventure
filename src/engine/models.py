from __future__ import annotations


class Room:
    def __init__(self, data: dict):
        self.id          = data.get("id")
        self.name        = data.get("name", "")
        self.description = data.get("description", "")
        self.exits       = data.get("exits", {})
        self.gather      = data.get("gather", {})
        self.actions     = data.get("actions", [])
        self.requires    = data.get("requires", [])
        self.encounters  = data.get("encounters", [])
        self.loot: dict[str, int]  = dict(data.get("loot", {}))
        self.loot_hidden: dict[str, bool] = dict(data.get("loot_hidden", {}))
        self.loot_hint:   dict[str, str]  = dict(data.get("loot_hint", {}))

        # Conditional descriptions keyed by "description_with_<item>"
        self._conditional_descs: dict[str, str] = {
            k[len("description_with_"):]: v
            for k, v in data.items()
            if k.startswith("description_with_")
        }

        self.width       = int(data.get("width",  1))
        self.height      = int(data.get("height", 1))
        self.is_walkable = self.width > 1 or self.height > 1

        self.features: list[dict] = []
        for f in data.get("features", []):
            pos = f.get("pos", [-1, -1])
            self.features.append({
                "id":           f.get("id", ""),
                "label":        f.get("label", "?"),
                "desc":         f.get("desc", ""),
                "examine_clue": f.get("examine_clue", ""),
                "enter_to":     f.get("enter_to"),
                "pos":          (int(pos[0]), int(pos[1])),
            })

    def gather_amount(self, resource: str) -> int:
        return int(self.gather.get(resource, 0) or 0)

    def visible_loot(self) -> dict[str, int]:
        return {k: v for k, v in self.loot.items()
                if v > 0 and not self.loot_hidden.get(k, False)}

    def reveal_loot_for_feature(self, feature_id: str) -> list[str]:
        revealed = []
        for item, hint_feat in self.loot_hint.items():
            if hint_feat == feature_id and self.loot_hidden.get(item):
                self.loot_hidden[item] = False
                if self.loot.get(item, 0) > 0:
                    revealed.append(item)
        return revealed

    def get_description(self, inventory: dict) -> str:
        """Return base description plus any conditional line matching carried items."""
        lines = [self.description]
        for item_key, extra in self._conditional_descs.items():
            if inventory.get(item_key, 0) > 0:
                lines.append(extra)
                break  # one conditional at a time
        return "\n".join(lines)


class Player:
    def __init__(self):
        self.max_hp = 30
        self.hp     = 30
        self.discovered_rooms: set[str]                  = set()
        self.explored_rooms:   set[str]                  = set()
        self.room_positions:   dict[str, tuple[int,int]] = {}
        self.current_pos:      tuple[int,int]            = (0, 0)
        self.visited_tiles:    set[tuple[int,int]]       = set()

        self.inventory: dict[str, int] = {
            "wood": 0, "stone": 0, "food": 0
        }

        # Torch uses remaining (None if not carrying one)
        self.torch_uses: int | None = None

        # Movement penalty when overweight
        self.overweight: bool = False

    def carry_limit(self, item_registry: dict) -> float:
        base  = 20.0
        bonus = item_registry.get("backpack", {}).get("carry_bonus", 0)                 if self.inventory.get("backpack", 0) > 0 else 0
        return base + bonus

    def carried_weight(self, item_registry: dict) -> float:
        total = 0.0
        for item, count in self.inventory.items():
            if count > 0 and item in item_registry:
                total += item_registry[item].get("weight", 0) * count
        return total

    def get_inventory_lines(self, item_registry: dict | None = None) -> list[str]:
        lines = ["\nInventory:"]
        total_weight = 0
        has_items = False
        for item, count in self.inventory.items():
            if count <= 0:
                continue
            has_items = True
            weight_str = ""
            if item_registry and item in item_registry:
                w = item_registry[item].get("weight", 0)
                item_weight = w * count
                total_weight += item_weight
                weight_str = f"  ({item_weight} kg)"
            lines.append(f"  {item}: {count}{weight_str}")
        if not has_items:
            lines.append("  Empty")
        elif item_registry:
            limit = self.carry_limit(item_registry)
            lines.append(f"  --- carried: {total_weight} / {int(limit)} kg ---")
        return lines

    def inventory_items(self) -> list[tuple[str, int]]:
        return [(k, v) for k, v in self.inventory.items() if v > 0]
