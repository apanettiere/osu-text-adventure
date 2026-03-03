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
        self.loot        = data.get("loot", {})

        self.width       = int(data.get("width",  1))
        self.height      = int(data.get("height", 1))
        self.is_walkable = self.width > 1 or self.height > 1

        self.features: list[dict] = []
        for f in data.get("features", []):
            pos = f.get("pos", [-1, -1])
            self.features.append({
                "id":    f.get("id", ""),
                "label": f.get("label", "?"),
                "desc":  f.get("desc", ""),
                "pos":   (int(pos[0]), int(pos[1])),
            })

    def gather_amount(self, resource: str) -> int:
        return int(self.gather.get(resource, 0) or 0)


class Player:
    def __init__(self):
        self.max_hp = 30
        self.hp     = 30

        self.discovered_rooms: set[str]              = set()
        self.explored_rooms:   set[str]              = set()
        self.room_positions:   dict[str, tuple[int,int]] = {}
        self.current_pos:      tuple[int,int]        = (0, 0)

        # World-map tiles revealed by walking (set of (world_col, world_row))
        self.visited_tiles: set[tuple[int,int]] = set()

        self.inventory: dict[str, int] = {"wood": 0, "stone": 0, "food": 0}

    def get_inventory_lines(self) -> list[str]:
        lines = ["\nInventory:"]
        any_items = False
        for item, amount in self.inventory.items():
            if amount > 0:
                lines.append(f"  {item}: {amount}")
                any_items = True
        if not any_items:
            lines.append("  Empty")
        return lines