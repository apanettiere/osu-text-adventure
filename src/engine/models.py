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

        # Walkable room fields
        self.width       = int(data.get("width",  1))
        self.height      = int(data.get("height", 1))
        self.is_walkable = self.width > 1 or self.height > 1

        # Features: list of {id, label, desc, pos: [x, y]}
        raw_features = data.get("features", [])
        self.features = []
        for f in raw_features:
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

        self.discovered_rooms = set()
        self.room_positions   = {}       # room_id -> (world_x, world_y)
        self.current_pos      = (0, 0)

        self.inventory = {"wood": 0, "stone": 0, "food": 0}

    def set_room_position(self, room_id: str, x: int, y: int) -> None:
        self.room_positions[room_id] = (x, y)

    def get_room_position(self, room_id: str) -> tuple[int, int] | None:
        return self.room_positions.get(room_id)

    def get_inventory_lines(self) -> list[str]:
        lines = ["\nInventory:"]
        has_items = False
        for item, amount in self.inventory.items():
            if amount > 0:
                lines.append(f"{item}: {amount}")
                has_items = True
        if not has_items:
            lines.append("Empty")
        return lines

    def show_inventory(self) -> None:
        for line in self.get_inventory_lines():
            print(line)