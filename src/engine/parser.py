import re


DIRECTION_ALIASES = {
    "n": "north",
    "north": "north",
    "up": "north",
    "s": "south",
    "south": "south",
    "down": "south",
    "e": "east",
    "east": "east",
    "right": "east",
    "w": "west",
    "west": "west",
    "left": "west",
}

SINGLE_ALIASES = {
    "l": ("look", None),
    "look": ("look", None),
    "i": ("inventory", None),
    "inv": ("inventory", None),
    "inventory": ("inventory", None),
    "bag": ("inventory", None),
    "items": ("inventory", None),
    "q": ("quit", None),
    "quit": ("quit", None),
    "exit": ("quit", None),
    "help": ("help", None),
    "commands": ("help", None),
    "controls": ("help", None),
    "?": ("help", None),
    "hint": ("hint", None),
    "h": ("hint", None),
    "recipe": ("craft", "list"),
    "recipes": ("craft", "list"),
    "crafting": ("craft", "list"),
}

VERB_ALIASES = {
    "g": "gather",
    "t": "take",
    "c": "craft",
    "x": "examine",
    "d": "drop",
    "r": "read",
    "cb": "combine",
    "walk": "go",
    "move": "go",
    "travel": "go",
    "head": "go",
    "run": "go",
    "inspect": "examine",
    "check": "examine",
    "search": "examine",
    "grab": "take",
    "collect": "take",
    "get": "take",
    "make": "craft",
    "build": "craft",
    "climb": "enter",
    "light": "use",
    "ignite": "use",
    "signal": "use",
    "point": "use",
}

TARGET_FILLERS = {
    "the", "a", "an", "to", "toward", "towards", "at", "on", "into",
    "in", "inside", "around", "from", "with", "up", "for", "my",
}

TWO_WORD_TARGETS = {
    ("climbing", "gear"): "climbing_gear",
    ("old", "map"): "old_map",
    ("river", "lake"): "river_lake",
    ("river", "run"): "river_run",
    ("flat", "stone"): "flat_stone",
    ("cave", "tunnel"): "cave_tunnel",
    ("cave", "chamber"): "cave_chamber",
    ("cabin", "interior"): "cabin_interior",
    ("loft", "ladder"): "loft_ladder",
    ("cabin", "bunk"): "cabin_bunk",
    ("work", "table"): "worktable",
    ("stone", "column"): "stone_column",
    ("echo", "pool"): "echo_pool",
    ("chamber", "ledge"): "chamber_ledge",
    ("flat", "rock"): "flat_rock",
    ("rope", "post"): "rope_post",
    ("fallen", "tree"): "fallen_tree",
    ("trail", "marker"): "trail_marker",
    ("cliff", "edge"): "cliff_edge",
    ("tide", "pool"): "tide_pool",
    ("signal", "brazier"): "signal_brazier",
    ("signal", "lens"): "signal_lens",
    ("signal", "lever"): "signal_lever",
    ("spiral", "stairs"): "spiral_stairs",
    ("fogged", "window"): "fogged_window",
    ("maintenance", "locker"): "maintenance_locker",
    ("winch", "console"): "winch_console",
    ("shutter", "crank"): "shutter_crank",
    ("catwalk", "hatch"): "catwalk_hatch",
    ("lighthouse", "light"): "lighthouse_light",
    ("fire", "pit"): "firepit",
    ("far", "shore"): "far_shore",
}


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()
    return [t for t in cleaned.split() if t]


def _trim_fillers(tokens: list[str]) -> list[str]:
    idx = 0
    while idx < len(tokens) and tokens[idx] in TARGET_FILLERS:
        idx += 1
    return tokens[idx:]


def _map_target(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    if len(tokens) >= 2:
        mapped = TWO_WORD_TARGETS.get((tokens[0], tokens[1]))
        if mapped:
            return mapped
    if tokens[0] == "rafter":
        return "raft"
    return tokens[0]


def parse_command(text: str) -> tuple[str, str | None]:
    raw = text.strip().lower()
    if raw == "?":
        return "help", None

    parts = _tokenize(text)
    if not parts:
        return "", None

    if len(parts) == 1:
        d = DIRECTION_ALIASES.get(parts[0])
        if d:
            return "go", d
        alias = SINGLE_ALIASES.get(parts[0])
        if alias:
            return alias

    # Common natural-language intents for first-time players.
    if parts[:2] == ["look", "around"]:
        return "look", None
    if parts[:2] == ["look", "at"]:
        target = _map_target(_trim_fillers(parts[2:]))
        return "examine", target
    if parts[:3] == ["where", "am", "i"]:
        return "look", None
    if parts[:3] == ["how", "to", "play"]:
        return "help", None
    if parts[:4] == ["what", "do", "i", "do"] or parts[:2] == ["what", "now"]:
        return "hint", None
    if parts[:2] == ["pick", "up"]:
        target = _map_target(_trim_fillers(parts[2:]))
        return "take", target

    verb = VERB_ALIASES.get(parts[0], parts[0])
    rest = parts[1:]

    # "go to the north", "walk west", "move right"
    if verb == "go":
        dest_tokens = _trim_fillers(rest)
        if dest_tokens and dest_tokens[0] in DIRECTION_ALIASES:
            return "go", DIRECTION_ALIASES[dest_tokens[0]]
        return "go", _map_target(dest_tokens)

    if verb in ("combine",):
        combo_parts = [t for t in rest if t not in {"the", "a", "an", "with", "and"}]
        if not combo_parts:
            return "combine", None
        return "combine", " ".join(combo_parts)

    target_tokens = _trim_fillers(rest)
    target = _map_target(target_tokens)

    # Bare read should try first readable item in inventory.
    if verb == "read" and not target:
        return "read", None

    return verb, target
