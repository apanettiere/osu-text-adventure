from engine.models import Player
from engine.loader import load_game_data, build_room_map
from engine.parser import parse_command


class GameState:
    def __init__(self):
        self.player = Player()

        self.game_data = load_game_data()
        self.rooms = build_room_map(self.game_data)

        self.current_room_id = self.game_data.get("starting_room")

    def print_room(self):
        room = self.rooms.get(self.current_room_id)

        print(f"\n{room.get('name', '')}")
        print(room.get("description", ""))

        exits = room.get("exits", {})
        if exits:
            directions = ", ".join(sorted(exits.keys()))
            print(f"Exits: {directions}")

    def run(self):
        print("The Dark Forest")
        print("Type: look, go <direction>, gather <resource>, inventory, quit")

        self.print_room()

        while True:
            user_input = input("\n> ")
            verb, target = parse_command(user_input)

            if verb in ("quit", "exit"):
                print("Goodbye.")
                break

            if verb == "":
                print("Please type a command.")
                continue

            if verb == "look":
                self.print_room()
                continue

            if verb == "inventory":
                self.player.show_inventory()
                continue

            if verb == "go":
                if not target:
                    print("Go where? Example: go north")
                    continue

                room = self.rooms.get(self.current_room_id)
                exits = room.get("exits", {})

                next_room_id = exits.get(target)

                if not next_room_id:
                    print("You cannot go that way.")
                    continue

                if next_room_id not in self.rooms:
                    print("Error: exit points to a missing room in game.json")
                    continue

                self.current_room_id = next_room_id
                self.print_room()
                continue
            
            if verb == "gather":
                if not target:
                    print("Gather what? Example: gather wood")
                    continue

                room = self.rooms.get(self.current_room_id)
                gather_data = room.get("gather", {})

                amount = gather_data.get(target, 0)

                if amount <= 0:
                    print("You cannot gather that here.")
                    continue

                if target not in self.player.inventory:
                    self.player.inventory[target] = 0

                self.player.inventory[target] += amount

                print("You gather wood." if target == "wood" else f"You gather {target}.")
                continue

            print("Unknown command.")