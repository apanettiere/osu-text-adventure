from engine.game_state import GameState
from engine.parser import parse_command


def select_difficulty() -> str:
    print("\nSelect difficulty:")
    print("  1) Easy   - More HP, less enemy damage, double gather yields")
    print("  2) Normal - Balanced combat and resources")
    print("  3) Hard   - Less HP, harder hits")
    while True:
        choice = input("Choose (1/2/3): ").strip()
        if choice in ("1", "easy"):
            return "easy"
        if choice in ("2", "normal", ""):
            return "normal"
        if choice in ("3", "hard"):
            return "hard"
        print("Please enter 1, 2, or 3.")


def main() -> None:
    difficulty = select_difficulty()
    state = GameState(difficulty=difficulty)

    print("\nThe Dark Forest")
    print("Type: help for commands. Core: look, go <direction>, gather, craft, take, examine, enter, read, use, hint, inventory, quit")

    for line in state.get_intro_lines():
        print(line)

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
