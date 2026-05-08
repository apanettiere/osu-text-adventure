from __future__ import annotations

DIRECTION_DELTAS: dict[str, tuple[int, int]] = {
    "north": (0, -1),
    "south": (0,  1),
    "east":  (1,  0),
    "west":  (-1, 0),
}

ENTRY_SPAWN: dict[str, object] = {
    "north": lambda w, h: (w // 2, h - 1),
    "south": lambda w, h: (w // 2, 0),
    "east":  lambda w, h: (0,      h // 2),
    "west":  lambda w, h: (w - 1,  h // 2),
}

MAP_ROOM_POS: dict[str, tuple[int, int]] = {
    "thick_forest":   (15, -1),
    "clearing":       (16, 13),
    "riverbank":      (17, 31),
    "river_run":      (8, 25),
    "river_lake":     (52, 30),
    "cave_entrance":  (33, 16),
    "cabin_interior": (16, -2),
    "cave_chamber":   (37, 7),
    "far_shore":      (21, 47),
    "shed_interior":  (14, 34),
    "open_waters":    (-35, 2),
    "mountain_pass":  (-2, 16),
    "lighthouse_interior": (-1, 5),
    "lighthouse_top":      (-2, -6),
}

REVEAL_RADIUS = 2

ENTER_TARGET_ALIASES: dict[str, str] = {
    "tower": "lighthouse",
    "stairs": "spiral_stairs",
    "staircase": "spiral_stairs",
    "top": "spiral_stairs",
    "upstairs": "spiral_stairs",
    "cave": "cave_tunnel",
    "tunnel": "cave_tunnel",
    "chamber": "cave_tunnel",
    "shed": "tool_shed",
    "tool_shed": "tool_shed",
}

LIGHT_SOURCES = {"lantern", "torch"}

DIFFICULTY_PRESETS = {
    "easy": {
        "label": "Easy",
        "player_hp": 40,
        "enemy_damage_mult": 0.75,
        "gather_mult": 2,
    },
    "normal": {
        "label": "Normal",
        "player_hp": 30,
        "enemy_damage_mult": 1.0,
        "gather_mult": 1,
    },
    "hard": {
        "label": "Hard",
        "player_hp": 20,
        "enemy_damage_mult": 1.5,
        "gather_mult": 1,
    },
}

DEFAULT_DIFFICULTY = "normal"


def encode_visited_tiles(tiles: set[tuple[int, int]]) -> list[list[object]]:
    if not tiles:
        return []
    rows: dict[int, list[int]] = {}
    for x, y in tiles:
        rows.setdefault(int(y), []).append(int(x))
    encoded: list[list[object]] = []
    for y in sorted(rows):
        xs = sorted(set(rows[y]))
        if not xs:
            continue
        runs: list[list[int]] = []
        start = xs[0]
        prev = xs[0]
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
                continue
            runs.append([start, prev])
            start = x
            prev = x
        runs.append([start, prev])
        encoded.append([y, runs])
    return encoded


def decode_visited_tiles(encoded) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    if not isinstance(encoded, list):
        return out
    for row in encoded:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            continue
        y_raw, runs = row
        try:
            y = int(y_raw)
        except Exception:
            continue
        if not isinstance(runs, (list, tuple)):
            continue
        for run in runs:
            if not isinstance(run, (list, tuple)) or len(run) != 2:
                continue
            try:
                x0 = int(run[0])
                x1 = int(run[1])
            except Exception:
                continue
            if x1 < x0:
                x0, x1 = x1, x0
            for x in range(x0, x1 + 1):
                out.add((x, y))
    return out
