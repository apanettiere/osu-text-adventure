def parse_command(text: str) -> tuple[str, str | None]:
    raw = text.strip().lower()

    if not raw:
        return "", None

    parts = raw.split()

    # Single-word shortcuts / aliases
    aliases = {
        "n": ("go", "north"),
        "north": ("go", "north"),
        "s": ("go", "south"),
        "south": ("go", "south"),
        "e": ("go", "east"),
        "east": ("go", "east"),
        "w": ("go", "west"),
        "west": ("go", "west"),

        "l": ("look", None),
        "look": ("look", None),

        "i": ("inventory", None),
        "inv": ("inventory", None),
        "inventory": ("inventory", None),

        "q": ("quit", None),
        "quit": ("quit", None),
        "exit": ("quit", None),
    }

    if len(parts) == 1 and parts[0] in aliases:
        return aliases[parts[0]]

    # Allow "go n" etc.
    verb = parts[0]
    target = parts[1] if len(parts) > 1 else None

    if verb == "go" and target:
        dir_alias = {
            "n": "north",
            "s": "south",
            "e": "east",
            "w": "west",
        }
        if target in dir_alias:
            target = dir_alias[target]

    return verb, target