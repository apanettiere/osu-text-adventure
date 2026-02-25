class Room:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.exits = data.get("exits", {})
        self.gather = data.get("gather", {})
        self.actions = data.get("actions", [])

        # Foundation fields for future features (not implemented yet)
        self.requires = data.get("requires", [])
        self.encounters = data.get("encounters", [])
        self.loot = data.get("loot", {})

    def gather_amount(self, resource: str) -> int:
        return int(self.gather.get(resource, 0) or 0)


class Player:
    def __init__(self):
        # Survival foundation (not used yet)
        self.max_hp = 30
        self.hp = 30

        # Map foundation (not used yet)
        self.discovered_rooms = set()

        # Inventory (used now)
        self.inventory = {
            "wood": 0,
            "stone": 0,
            "food": 0
        }

    def get_inventory_lines(self) -> list[str]:
        lines = []
        lines.append("\nInventory:")

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