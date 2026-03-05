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

    verb   = parts[0]
    target = parts[1] if len(parts) > 1 else None

    # "g wood"    → gather wood
    if verb == "g" and target:
        return "gather", target

    # "t machete" → take machete
    if verb == "t" and target:
        return "take", target

    # "c raft"    → craft raft
    if verb == "c" and target:
        return "craft", target

    # "x boulder" → examine boulder
    if verb == "x" and target:
        return "examine", target

    # "d wood" → drop wood
    if verb == "d" and target:
        return "drop", target
    # "r note" → read note,  bare "r" or "read" → read note
    if verb == "r":
        return "read", target or "note"
    if verb == "read" and not target:
        return "read", "note"

    # "cb rope hook" → combine rope hook
    if verb == "cb" and target:
        rest = " ".join(parts[1:])
        return "combine", rest

    if verb == "go" and target:
        dir_alias = {"n": "north", "s": "south", "e": "east", "w": "west"}
        if target in dir_alias:
            target = dir_alias[target]

    return verb, target