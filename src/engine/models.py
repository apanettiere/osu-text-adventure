class Player:
    def __init__(self):
        self.inventory = {
            "wood": 0,
            "stone": 0,
            "food": 0
        }

    def show_inventory(self) -> None:
        print("\nInventory:")

        has_items = False

        for item, amount in self.inventory.items():
            if amount > 0:
                print(f"{item}: {amount}")
                has_items = True

        if not has_items:
            print("Empty")