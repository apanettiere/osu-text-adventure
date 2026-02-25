from engine.game_state import GameState
from engine.parser import parse_command


def main() -> None:
    state = GameState()

    print("The Dark Forest")
    print("Type: look, go <direction>, gather <resource>, inventory, quit")

    for line in state.describe_current_room():
        print(line)

    while state.is_running:
        user_input = input("\n> ")
        verb, target = parse_command(user_input)

        lines = state.process_command(verb, target)

        for line in lines:
            print(line)


if __name__ == "__main__":
    main()