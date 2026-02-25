class Player:
    def __init__(self):
        self.inventory = {
            "wood": 0,
            "stone": 0,
            "food": 0
        }

    def show_inventory(self) -> None:
        print("\nInventory:")
        for item, amount in self.inventory.items():
            print(f"{item}: {amount}")