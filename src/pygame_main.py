import json
from pathlib import Path
import pygame
from engine.game_state import GameState, MAP_ROOM_POS
from engine.parser import parse_command

WIDTH  = 960
HEIGHT = 640
FPS    = 60
PADDING     = 16
LINE_HEIGHT = 26
GAME_INPUT_HEIGHT = 56
MAP_INPUT_HEIGHT = 86
MAX_LOG_LINES = 300
SAVE_FILE = Path(__file__).resolve().parents[1] / "data" / "savegame.json"


def clamp_log(lines):
    return lines[-MAX_LOG_LINES:] if len(lines) > MAX_LOG_LINES else lines

def point_in_rect(pos, rect):
    return rect.collidepoint(pos[0], pos[1])


def _wrap_pixels(text, font, max_w):
    words = text.split()
    if not words:
        return [""]
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _format_log_lines_for_view(log_lines, font, font_bold, max_w):
    out = []
    for raw in log_lines:
        text = str(raw)
        is_bold = text.startswith("\n")
        if is_bold:
            text = text[1:]
        f = font_bold if is_bold else font
        c = (240, 240, 240) if is_bold else (220, 220, 220)
        for part in text.split("\n"):
            part = part.strip()
            if not part:
                out.append((None, None, None))
                continue
            for seg in _wrap_pixels(part, f, max_w):
                out.append((seg, f, c))

    # Keep at most one blank line in a row.
    collapsed = []
    last_blank = False
    for txt, ff, cc in out:
        is_blank = txt is None
        if is_blank and last_blank:
            continue
        collapsed.append((txt, ff, cc))
        last_blank = is_blank
    return collapsed


def save_game_state(state):
    try:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SAVE_FILE.open("w", encoding="utf-8") as f:
            json.dump(state.snapshot(), f, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        pass


def load_game_state():
    try:
        if not SAVE_FILE.exists():
            return None
        with SAVE_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        state = GameState()
        if state.apply_snapshot(payload):
            return state
    except Exception:
        return None
    return None


def clear_game_state():
    try:
        if SAVE_FILE.exists():
            SAVE_FILE.unlink()
    except Exception:
        pass

def draw_button(screen, rect, text, font, hovered, enabled=True):
    if enabled:
        bg = (60, 60, 60) if hovered else (45, 45, 45)
        border = (90, 90, 90)
        fg = (245, 245, 245)
    else:
        bg = (30, 30, 30)
        border = (58, 58, 58)
        fg = (125, 125, 125)
    pygame.draw.rect(screen, bg, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, width=2, border_radius=10)
    lbl = font.render(text, True, fg)
    screen.blit(lbl, lbl.get_rect(center=rect.center))


def run_instructions(screen, clock):
    fh = pygame.font.SysFont(None, 40, bold=True)
    fs = pygame.font.SysFont(None, 24, bold=True)
    fb = pygame.font.SysFont(None, 22)
    ff = pygame.font.SysFont(None, 19)
    fn = pygame.font.SysFont(None, 28, bold=True)
    br = pygame.Rect(0,0,200,46); br.center = (WIDTH//2, HEIGHT-48)

    SECS = [
        ("GOAL",
         "You wake up alone in a dark forest with no memory of how you got here.",
         "Explore, gather resources, and find a way to escape.",
        ),
        ("CONTROLS",
         "Arrow keys move. Enter sends your typed command. Backspace erases text.",
         "M opens map. I opens inventory. Esc closes map or inventory.",
         "F5 or type save to save now. Esc from game view returns to menu and saves.",
         "In inventory: Up/Down select, D drops selected item, R reads selected item.",
        ),
        ("COMMANDS",
         "Movement words: go north/south/east/west, or shortcuts n s e w.",
         "look (or l) to re-read the room. Walk near objects to see clues.",
         "take <item>, examine <feature>, enter <feature>, use <item>, read <item>.",
         "gather wood, gather stone, or gather food. drop <item> places one carried item in the room.",
        ),
        ("THE MAP  (press M)",
         "One connected map that reveals as you explore.",
         "@ is you.  ? is an area you know of but have not entered.",
         "Obstacles like rivers, brambles, and cliffs are shown where they block the path.",
         "Arrow keys and typing still work while the map is open.",
        ),
        ("SAVE AND RESET",
         "Your game auto-saves after movement and commands.",
         "Main menu has Continue Saved Game and Reset Save options.",
         "Reset Save clears your progress and starts fresh.",
        ),
    ]

    while True:
        clock.tick(FPS)
        mp = pygame.mouse.get_pos(); bh = point_in_rect(mp, br)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE): return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and bh: return

        screen.fill((14,14,14))
        ts = fh.render("HOW TO PLAY", True, (240,240,240))
        screen.blit(ts, ts.get_rect(center=(WIDTH//2, 34)))
        pygame.draw.line(screen, (50,50,50), (PADDING*4, 58), (WIDTH-PADDING*4, 58), 1)
        y = 72; col = PADDING*5
        for sec in SECS:
            screen.blit(fs.render(sec[0], True, (170,150,90)), (col, y)); y += 20
            for ln in sec[1:]:
                screen.blit(fb.render(ln.strip(), True, (200,200,200)), (col+6, y)); y += 17
            y += 8
        draw_button(screen, br, "Back to Menu", fn, bh)
        foot = ff.render("ESC / ENTER / SPACE to go back", True, (65,65,65))
        screen.blit(foot, foot.get_rect(center=(WIDTH//2, HEIGHT-16)))
        pygame.display.flip()


def run_menu(screen, clock):
    ft = pygame.font.SysFont(None, 52, bold=True)
    fb = pygame.font.SysFont(None, 30, bold=True)
    fh = pygame.font.SysFont(None, 22)
    ff = pygame.font.SysFont(None, 20)
    cy = HEIGHT // 2 - 20
    cr = pygame.Rect(0, 0, 320, 52); cr.center = (WIDTH//2, cy)
    sr = pygame.Rect(0, 0, 320, 52); sr.center = (WIDTH//2, cy + 58)
    hr = pygame.Rect(0, 0, 320, 52); hr.center = (WIDTH//2, cy + 116)
    rr = pygame.Rect(0, 0, 320, 52); rr.center = (WIDTH//2, cy + 174)
    qr = pygame.Rect(0, 0, 320, 52); qr.center = (WIDTH//2, cy + 232)
    reset_armed = False
    reset_until = 0

    while True:
        clock.tick(FPS)
        mp = pygame.mouse.get_pos()
        has_save = SAVE_FILE.exists()
        if reset_armed and pygame.time.get_ticks() > reset_until:
            reset_armed = False

        ch = point_in_rect(mp, cr) and has_save
        sh = point_in_rect(mp, sr)
        hh = point_in_rect(mp, hr)
        rh = point_in_rect(mp, rr) and has_save
        qh = point_in_rect(mp, qr)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return "quit"
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_c and has_save:
                    return "continue"
                if ev.key == pygame.K_n:
                    return "start"
                if ev.key == pygame.K_h:
                    return "how"
                if ev.key == pygame.K_r and has_save:
                    if reset_armed:
                        return "reset"
                    reset_armed = True
                    reset_until = pygame.time.get_ticks() + 3000
                if ev.key == pygame.K_RETURN:
                    return "continue" if has_save else "start"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if ch: return "continue"
                if sh: return "start"
                if hh: return "how"
                if rh:
                    if reset_armed:
                        return "reset"
                    reset_armed = True
                    reset_until = pygame.time.get_ticks() + 3000
                if qh: return "quit"
        screen.fill((14,14,14))
        t = ft.render("THE DARK FOREST", True, (240,240,240))
        screen.blit(t, t.get_rect(center=(WIDTH//2, 108)))
        hint = fh.render("A text-based survival adventure", True, (190,190,190))
        screen.blit(hint, hint.get_rect(center=(WIDTH//2, 144)))
        draw_button(screen, cr, "Continue Saved Game", fb, ch, has_save)
        draw_button(screen, sr, "New Game", fb, sh)
        draw_button(screen, hr, "How to Play", fb, hh)
        draw_button(screen, rr, "Reset Save", fb, rh, has_save)
        draw_button(screen, qr, "Quit", fb, qh)
        if has_save:
            k_hint = "Shortcuts: C continue   N new game   H help   R reset save   ESC quit"
        else:
            k_hint = "Shortcuts: N new game   H help   ESC quit"
        screen.blit(ff.render(k_hint, True, (112, 112, 112)), (PADDING * 2, HEIGHT - 24))
        if reset_armed and has_save:
            warn = "Press Reset Save again within 3 seconds to confirm."
            ws = ff.render(warn, True, (196, 145, 110))
            screen.blit(ws, ws.get_rect(center=(WIDTH // 2, rr.bottom + 20)))
        pygame.display.flip()


def draw_game_screen(screen, font, font_bold, log_lines, input_text, scroll_offset, cursor_on):
    screen.fill((18,18,18))
    ol = PADDING; ot = PADDING; ob = HEIGHT - GAME_INPUT_HEIGHT - PADDING
    oh = ob - ot
    pygame.draw.rect(screen, (28,28,28), (ol-8, ot-8, WIDTH-PADDING*2+16, oh+16), border_radius=8)
    max_text_w = WIDTH - (PADDING * 3)
    view_lines = _format_log_lines_for_view(log_lines, font, font_bold, max_text_w)
    lf = max(1, oh // LINE_HEIGHT)
    si = max(0, len(view_lines) - lf - scroll_offset)
    y = ot
    for text, ff, cc in view_lines[si:si+lf]:
        if text:
            screen.blit(ff.render(text, True, cc), (ol, y))
        y += LINE_HEIGHT
    iy = HEIGHT - GAME_INPUT_HEIGHT
    pygame.draw.rect(screen, (40,40,40), (0, iy, WIDTH, GAME_INPUT_HEIGHT))
    pygame.draw.rect(screen, (60,60,60), (0, iy, WIDTH, 2))
    display_text = "> " + input_text
    text_x = PADDING
    text_y = iy + 10
    screen.blit(font.render(display_text, True, (255,255,255)), (text_x, text_y))
    if cursor_on:
        cursor_x = text_x + font.size(display_text)[0]
        pygame.draw.line(screen, (255,255,255), (cursor_x, text_y + 22), (cursor_x + 10, text_y + 22), 2)


MAP_ROOM_SIZE = {
    "thick_forest":   (19, 13),
    "clearing":       (17, 17),
    "riverbank":      (17, 13),
    "cave_entrance":  (13, 11),
    "far_shore":      ( 9,  5),
    "mountain_pass":  (13, 11),
    "lighthouse_interior": (1, 1),
    "lighthouse_top":      (1, 1),
}

# Item-gated blockers between regions. Water is procedural.
OBSTACLE_ZONES = {
    "thick_forest":   ("bramble",   12, 14, 20, 30),
    "cave_entrance":  ("darkness",  17, 25, 31, 33),
    "mountain_pass":  ("cliff",     17, 25, 14, 16),
}

# Free path between clearing and riverbank (south, no obstacle)
FREE_CORRIDORS = [
    (30, 30, 23, 26),
]

OBS_COL = {
    "bramble":   (30,  60,  25),
    "river":     (30,  80, 120),
    "bay":       (24,  74, 116),
    "cliff":     (80,  72,  62),
    "darkness":  (18,  18,  22),
}

FEATURE_COLORS = {
    "stump":        (145, 110,  65),
    "firepit":      (210, 115,  45),
    "trail_marker": (145, 130,  80),
    "cabin":        (155, 115,  75),
    "fallen_tree":  (110,  90,  55),
    "rope_post":    (155, 152, 145),
    "flat_rock":    (130, 125, 115),
    "flat_stone":   (122, 122, 128),
    "lighthouse":   (230, 225, 170),
    "cliff_edge":   (175, 170, 162),
    "spiral_stairs": (185, 175, 140),
    "signal_brazier": (220, 120, 65),
    "signal_lens":    (210, 235, 240),
}

ITEM_MAP_COLORS = {
    "resource":  ( 85, 155,  75),
    "tool":      (195, 155,  50),
    "crafted":   ( 95, 125, 185),
    "readable":  (155, 115, 185),
    "equipment": (110, 175, 155),
}

FOREST_CHARS_NEAR  = ["'", ",", "'", "."]
FOREST_CHARS_MID   = ["*", "'", "*", ",", "*"]
FOREST_CHARS_FAR   = ["^", "*", "^", "'", "^", "*"]
FOREST_CHARS_DENSE = ["^", "^", "*", "^"]

REVEAL_RADIUS = 2

MAP_WIN_COL0, MAP_WIN_ROW0 = 2, -3
MAP_WIN_COLS, MAP_WIN_ROWS  = 44, 55

MAP_CENTER_COL = 22
MAP_CENTER_ROW = 23
MAP_RING_RADIUS = 29

RIVER_PATH = [
    (34, 45),
    (30, 45),
    (26, 45),
    (22, 44),
    (18, 42),
    (15, 39),
    (12, 35),
    (10, 31),
    (8, 27),
    (7, 24),
    (6, 22),
]

RAFT_CROSSING_TILES = {
    (23, 45), (24, 45), (25, 45), (26, 45), (27, 45),
    (24, 46), (25, 46), (26, 46),
}


def _build_river_samples(path):
    samples = []
    if len(path) < 2:
        return samples
    seg_count = len(path) - 1
    for idx, ((x0, y0), (x1, y1)) in enumerate(zip(path, path[1:])):
        steps = max(abs(x1 - x0), abs(y1 - y0)) * 2
        steps = max(steps, 1)
        width = 1.9 + (idx / max(seg_count - 1, 1)) * 0.9
        dx = x1 - x0
        dy = y1 - y0
        mag = max((dx * dx + dy * dy) ** 0.5, 0.001)
        ndx = dx / mag
        ndy = dy / mag
        flow = idx / max(seg_count - 1, 1)
        for s in range(steps + 1):
            t = s / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            samples.append((x, y, width, ndx, ndy, flow))
    return samples


RIVER_SAMPLES = _build_river_samples(RIVER_PATH)


def _room_at(wcol, wrow, rooms):
    for rid, (rx, ry) in MAP_ROOM_POS.items():
        if rid not in MAP_ROOM_SIZE:
            continue
        rw, rh = MAP_ROOM_SIZE[rid]
        if rx <= wcol < rx+rw and ry <= wrow < ry+rh:
            return (rid, wcol - rx, wrow - ry)
    return None


def _in_room_shape(wcol, wrow):
    info = _room_at(wcol, wrow, {})
    if not info:
        return False
    rid, lc, lr = info
    rw, rh = MAP_ROOM_SIZE.get(rid, (1, 1))
    return _ellipse_zone(lc, lr, rw, rh) != "outside"


def _ellipse_zone(col, row, rw, rh):
    cx = (rw-1)/2.0; cy = (rh-1)/2.0
    ax = max(cx-0.4, 1.0); ay = max(cy-0.4, 1.0)
    d  = ((col-cx)/ax)**2 + ((row-cy)/ay)**2
    if   d > 1.2:  return "outside"
    elif d > 0.70: return "border"
    else:          return "inside"


def _obstacle_at(wcol, wrow):
    if _is_river_tile(wcol, wrow):
        return "river", "riverbank"
    if _is_bay_tile(wcol, wrow):
        return "bay", "mountain_pass"
    for rid, (otype, r0, r1, c0, c1) in OBSTACLE_ZONES.items():
        if r0 <= wrow <= r1 and c0 <= wcol <= c1:
            return otype, rid
    return None, None


def _in_free_corridor(wcol, wrow):
    for r0, r1, c0, c1 in FREE_CORRIDORS:
        if r0 <= wrow <= r1 and c0 <= wcol <= c1:
            return True
    return False


def _nearest_river_sample(wcol, wrow):
    best = None
    best_d2 = 10**9
    for sample in RIVER_SAMPLES:
        sx, sy = sample[0], sample[1]
        dx = wcol - sx
        dy = wrow - sy
        d2 = dx * dx + dy * dy
        if d2 < best_d2:
            best_d2 = d2
            best = sample
    return best, best_d2


def _is_river_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    sample, d2 = _nearest_river_sample(wcol, wrow)
    if sample is None:
        return False
    width = sample[2]
    return d2 <= width * width


def _is_bay_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    # Open ocean off-map to the west.
    if wcol <= 4 and 4 <= wrow <= 48:
        return True
    # Main bay body near the lighthouse cliffs.
    cx1, cy1 = 7.0, 22.0
    rx1, ry1 = 7.8, 10.4
    d1 = ((wcol - cx1) / rx1) ** 2 + ((wrow - cy1) / ry1) ** 2
    # Upper lobe that gives the coastline a curved bite.
    cx2, cy2 = 5.0, 16.0
    rx2, ry2 = 5.5, 5.5
    d2 = ((wcol - cx2) / rx2) ** 2 + ((wrow - cy2) / ry2) ** 2
    return (d1 <= 1.0 and wcol <= 14) or (d2 <= 1.0 and wcol <= 11)


def _is_water_tile(wcol, wrow):
    return _is_bay_tile(wcol, wrow) or _is_river_tile(wcol, wrow)


def _is_coast_cliff_tile(wcol, wrow):
    if _is_water_tile(wcol, wrow):
        return False
    room_info = _room_at(wcol, wrow, {})
    if room_info:
        rid, lc, lr = room_info
        rw, rh = MAP_ROOM_SIZE.get(rid, (1, 1))
        zone = _ellipse_zone(lc, lr, rw, rh)
        if zone != "outside" and rid != "mountain_pass":
            return False
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            # Keep cliffs as coastline near the bay only. River banks stay forest.
            if _is_bay_tile(wcol + dx, wrow + dy):
                return True
    return False


def _river_flow_char(dx, dy):
    ax, ay = abs(dx), abs(dy)
    if ax > ay * 1.7:
        return "="
    if ay > ax * 1.7:
        return "|"
    return "\\" if dx * dy > 0 else "/"


def _zone_char(otype, wcol, wrow):
    seed = (wcol * 5 + wrow * 11) % 16
    if otype == "river":
        sample, d2 = _nearest_river_sample(wcol, wrow)
        if sample is None:
            return "~", (18, 92, 145)
        width = sample[2]
        depth = max(0.0, 1.0 - d2 / max(width * width, 0.01))
        center_char = _river_flow_char(sample[3], sample[4])
        if depth > 0.62:
            c = center_char if seed % 3 else "~"
        else:
            c = "~" if seed % 2 else "-"
        blue = int(152 + sample[5] * 36)
        green = int(84 + sample[5] * 22)
        col = (16, green + (seed % 3) * 3, blue + (seed % 3) * 2)
        return c, col
    if otype == "bay":
        chars = "~~~---~~"
        c = chars[seed % len(chars)]
        col = (12, 76 + (seed % 4) * 4, 126 + (seed % 5) * 3)
        return c, col
    if otype == "bramble":
        chars = "#x#*#x##"
        c = chars[seed % len(chars)]
        v = 28 + seed * 2
        return c, (v, v + 32, v - 4)
    if otype == "cliff":
        chars = "^n|^nn^|"
        c = chars[seed % len(chars)]
        v = 96 + seed
        return c, (v + 8, v + 8, v + 8)
    if otype == "darkness":
        chars = ".:.:..:"
        c = chars[seed % len(chars)]
        v = 18 + seed
        return c, (v, v, v + 4)
    return "?", (100, 100, 100)


def _dist_to_nearest_room(wcol, wrow):
    best = 999
    for rid, (rx, ry) in MAP_ROOM_POS.items():
        if rid not in MAP_ROOM_SIZE:
            continue
        rw, rh = MAP_ROOM_SIZE[rid]
        dc = max(0, rx - wcol, wcol - (rx+rw-1))
        dr = max(0, ry - wrow, wrow - (ry+rh-1))
        best = min(best, dc+dr)
    return best





def draw_map_overlay(screen, font_title, font_body, state, last_cmd=""):
    CELL = 9
    try:
        mf = pygame.font.SysFont("Courier New", CELL+1)
    except Exception:
        mf = pygame.font.SysFont(None, CELL+2)

    # Map pixel origin: centre the map window on screen
    map_px_w = MAP_WIN_COLS * CELL
    map_px_h = MAP_WIN_ROWS * CELL
    map_area_h = HEIGHT - MAP_INPUT_HEIGHT - 36
    opx = (WIDTH  - map_px_w) // 2
    opy = (HEIGHT - MAP_INPUT_HEIGHT - map_px_h) // 2 + 18

    # Title
    ts = font_title.render("MAP", True, (140, 170, 110))
    screen.blit(ts, ts.get_rect(center=(WIDTH//2, opy-22)))

    visited = state.player.visited_tiles
    cur_rid  = state.current_room_id
    explored = state.player.explored_rooms
    discovered = state.player.discovered_rooms
    has_raft = state.player.inventory.get("raft", 0) > 0
    rooms    = state.rooms

    # Colour palette
    C = {
        "room_floor_cur":  (62, 55, 42),
        "room_floor_exp":  (30, 27, 20),
        "room_floor_fog":  (16, 16, 12),
        "cliff_floor_cur": (104, 104, 106),
        "cliff_floor_exp": (72, 72, 76),
        "cliff_floor_fog": (38, 38, 42),
        "cave_floor_cur":  (8, 8, 10),
        "cave_floor_exp":  (6, 6, 8),
        "cave_floor_fog":  (3, 3, 4),
        "tree_cur":        (80,130, 60),
        "tree_exp":        (48, 80, 42),
        "tree_fog":        (26, 38, 20),
        "cliff_edge_cur":  (150, 150, 155),
        "cliff_edge_exp":  (108, 108, 114),
        "cliff_edge_fog":  (58, 58, 62),
        "cave_edge_cur":   (18, 18, 22),
        "cave_edge_exp":   (12, 12, 16),
        "cave_edge_fog":   (7, 7, 9),
        "coast_cliff":     (128, 130, 136),
        "path":            (48, 42, 30),
        "player":          (245,245,215),
        "feature":         (195,165, 55),
        "label_exp":       (100,125, 78),
        "label_fog":       (38,  48, 28),
        "forest_near":     (35, 58, 30),
        "forest_mid":      (28, 48, 22),
        "forest_far":      (22, 38, 16),
        "forest_dense":    (14, 24, 10),
        "obs_path":        (45, 40, 28),
    }

    TREE_CHARS = ["*","'","*",",","*","'","*"]

    def tchar(lc, lr, rw, rh):
        if (lc in (0,rw-1)) and (lr in (0,rh-1)):
            return chr(9670)  # ♦
        return TREE_CHARS[(lc + lr*3) % len(TREE_CHARS)]

    def put(wcol, wrow, ch, color):
        px = opx + (wcol - MAP_WIN_COL0)*CELL
        py = opy + (wrow - MAP_WIN_ROW0)*CELL
        if 0 <= px < WIDTH and 0 <= py < HEIGHT - MAP_INPUT_HEIGHT:
            screen.blit(mf.render(ch, True, color), (px, py))

    for wrow in range(MAP_WIN_ROW0, MAP_WIN_ROW0 + MAP_WIN_ROWS):
        for wcol in range(MAP_WIN_COL0, MAP_WIN_COL0 + MAP_WIN_COLS):

            # Outside the circular overall boundary: skip
            ddx = wcol - MAP_CENTER_COL; ddy = wrow - MAP_CENTER_ROW
            if ddx*ddx*0.9 + ddy*ddy > MAP_RING_RADIUS*MAP_RING_RADIUS:
                continue

            tile_visited = (wcol, wrow) in visited

            room_info = _room_at(wcol, wrow, rooms)
            if room_info:
                rid, lc, lr = room_info
                rw, rh = MAP_ROOM_SIZE.get(rid, (1,1))
                zone = _ellipse_zone(lc, lr, rw, rh)

                if zone == "outside":
                    pass  # part of bounding box but outside circle: treat as forest
                else:
                    is_cur  = (rid == cur_rid)
                    is_exp  = rid in explored
                    is_disc = rid in discovered
                    is_cliff_room = (rid == "mountain_pass")
                    is_cave_room = (rid == "cave_entrance")

                    if zone == "border":
                        # Check if exit gap
                        room = rooms.get(rid)
                        is_gap = room and (
                            (lr==0     and lc==rw//2 and "north" in room.exits) or
                            (lr==rh-1  and lc==rw//2 and "south" in room.exits) or
                            (lc==0     and lr==rh//2 and "west"  in room.exits) or
                            (lc==rw-1  and lr==rh//2 and "east"  in room.exits)
                        )
                        if is_gap and tile_visited:
                            put(wcol, wrow, ".", C["path"])
                        elif tile_visited:
                            if is_cliff_room:
                                tc = C["cliff_edge_cur"] if is_cur else (C["cliff_edge_exp"] if is_exp else C["cliff_edge_fog"])
                                edge_ch = "^" if _is_coast_cliff_tile(wcol, wrow) and (lc + lr) % 2 else (":" if (lc + lr) % 2 else ".")
                                put(wcol, wrow, edge_ch, tc)
                            elif is_cave_room:
                                tc = C["cave_edge_cur"] if is_cur else (C["cave_edge_exp"] if is_exp else C["cave_edge_fog"])
                                put(wcol, wrow, "#" if (lc + lr) % 2 else ":", tc)
                            else:
                                tc = C["tree_cur"] if is_cur else (C["tree_exp"] if is_exp else C["tree_fog"])
                                put(wcol, wrow, tchar(lc,lr,rw,rh), tc)
                        elif is_disc:
                            if is_cliff_room:
                                put(wcol, wrow, ".", C["cliff_edge_fog"])
                            elif is_cave_room:
                                put(wcol, wrow, ".", C["cave_edge_fog"])
                            else:
                                put(wcol, wrow, ".", C["tree_fog"])

                    else:  # inside
                        if is_cur and tile_visited:
                            if is_cliff_room:
                                ch = ":" if (lc + lr) % 4 == 0 else "."
                                put(wcol, wrow, ch, C["cliff_floor_cur"])
                            elif is_cave_room:
                                ch = "." if (lc + lr) % 4 == 0 else " "
                                put(wcol, wrow, ch, C["cave_floor_cur"])
                            else:
                                ch = "," if (lc+lr)%4==0 else "."
                                put(wcol, wrow, ch, C["room_floor_cur"])
                        elif is_exp and tile_visited:
                            if is_cliff_room:
                                ch = ":" if (lc + lr) % 5 == 0 else "."
                                put(wcol, wrow, ch, C["cliff_floor_exp"])
                            elif is_cave_room:
                                ch = "." if (lc + lr) % 5 == 0 else " "
                                put(wcol, wrow, ch, C["cave_floor_exp"])
                            else:
                                ch = "," if (lc+lr)%5==0 else "."
                                put(wcol, wrow, ch, C["room_floor_exp"])
                        elif is_disc:
                            # Fog: faint silhouette
                            if (lc+lr)%6 == 0:
                                if is_cliff_room:
                                    put(wcol, wrow, ":", C["cliff_floor_fog"])
                                elif is_cave_room:
                                    put(wcol, wrow, ".", C["cave_floor_fog"])
                                else:
                                    put(wcol, wrow, ",", C["room_floor_fog"])

                    # Shore cliffs blend into the lighthouse room edge only where water touches.
                    if is_cliff_room and (tile_visited or is_exp) and _is_coast_cliff_tile(wcol, wrow):
                        shore_col = C["coast_cliff"] if tile_visited else C["cliff_edge_exp"]
                        put(wcol, wrow, "^" if (wcol + wrow) % 2 else "|", shore_col)

                    # Features (explored only, inside only)
                    if is_exp and zone == "inside":
                        room = rooms.get(rid)
                        if room:
                            for feat in room.features:
                                fx, fy = feat.get("pos",(-1,-1))
                                if feat.get("id") == "lighthouse":
                                    for dx, dy, ch, col in [
                                        (0, -2, "^", (230, 50, 55)),
                                        (-1, -1, "/", (230, 230, 230)),
                                        (0, -1, "A", (245, 245, 245)),
                                        (1, -1, "\\", (230, 230, 230)),
                                        (-1, 0, "|", (210, 48, 52)),
                                        (0, 0, "H", (248, 248, 248)),
                                        (1, 0, "|", (210, 48, 52)),
                                        (-1, 1, "|", (210, 48, 52)),
                                        (0, 1, "|", (244, 244, 244)),
                                        (1, 1, "|", (210, 48, 52)),
                                    ]:
                                        if fx + dx == lc and fy + dy == lr and tile_visited:
                                            put(wcol, wrow, ch, col)
                                elif fx == lc and fy == lr:
                                    if tile_visited:
                                        fcol = FEATURE_COLORS.get(feat.get("id",""), C["feature"])
                                        put(wcol, wrow, feat.get("label","?"), fcol)

                    # Visible loot items (explored only, inside only)
                    if is_exp and zone == "inside":
                        room = rooms.get(rid)
                        if room:
                            visible = room.visible_loot()
                            if visible:
                                item_list = list(visible.keys())
                                half = len(item_list) // 2
                                item_row = rh // 2 + 2
                                for ii, item_name in enumerate(item_list):
                                    ix = rw // 2 + ii - half
                                    if lc == ix and lr == item_row and tile_visited:
                                        item_info = state.game_data.get("items", {}).get(item_name, {})
                                        itype = item_info.get("type", "")
                                        icol = ITEM_MAP_COLORS.get(itype, (200, 180, 80))
                                        put(wcol, wrow, item_name[0].upper(), icol)

                    # Player marker
                    if is_cur:
                        room = rooms.get(rid)
                        if room and room.is_walkable:
                            plx = MAP_ROOM_POS[rid][0] + state.local_x
                            ply = MAP_ROOM_POS[rid][1] + state.local_y
                        else:
                            plx = MAP_ROOM_POS[rid][0] + rw//2
                            ply = MAP_ROOM_POS[rid][1] + rh//2
                        if wcol == plx and wrow == ply:
                            put(wcol, wrow, "@", C["player"])

                    # Room initial label for explored unexplored-here rooms
                    if is_disc and not is_cur:
                        cx_label = MAP_ROOM_POS[rid][0] + rw//2
                        cy_label = MAP_ROOM_POS[rid][1] + rh//2
                        if wcol == cx_label and wrow == cy_label:
                            room = rooms.get(rid)
                            ch = "?" if not is_exp else (room.name[0].upper() if room else "?")
                            col = C["label_fog"] if not is_exp else C["label_exp"]
                            put(wcol, wrow, ch, col)
                    continue

            if has_raft and (wcol, wrow) in RAFT_CROSSING_TILES:
                crossing_known = ("riverbank" in discovered) or ("far_shore" in discovered)
                if tile_visited or crossing_known:
                    put(wcol, wrow, ".", C["obs_path"])
                continue

            obs, trigger_rid = _obstacle_at(wcol, wrow)
            if obs:
                zone_known = trigger_rid in discovered
                if tile_visited or zone_known:
                    ch, col = _zone_char(obs, wcol, wrow)
                    put(wcol, wrow, ch, col)
                elif _dist_to_nearest_room(wcol, wrow) <= REVEAL_RADIUS + 2:
                    put(wcol, wrow, ".", (18, 18, 14))
                continue

            if _in_free_corridor(wcol, wrow) and tile_visited:
                put(wcol, wrow, ".", C["path"])
                continue

            coast_known = any(r in discovered for r in ("mountain_pass", "riverbank", "far_shore"))
            if (tile_visited or coast_known) and _is_coast_cliff_tile(wcol, wrow):
                c = "^" if (wcol + wrow) % 2 else "|"
                put(wcol, wrow, c, C["coast_cliff"])
                continue

            if not tile_visited:
                continue
            dist = _dist_to_nearest_room(wcol, wrow)
            seed = (wcol*7 + wrow*13) % 8
            if dist == 1:
                if seed < 3:
                    ch = FOREST_CHARS_NEAR[seed % len(FOREST_CHARS_NEAR)]
                    put(wcol, wrow, ch, C["forest_near"])
            elif dist <= 3:
                ch = FOREST_CHARS_MID[seed % len(FOREST_CHARS_MID)]
                put(wcol, wrow, ch, C["forest_mid"])
            elif dist <= 6:
                ch = FOREST_CHARS_FAR[seed % len(FOREST_CHARS_FAR)]
                put(wcol, wrow, ch, C["forest_far"])
            else:
                ch = FOREST_CHARS_DENSE[seed % len(FOREST_CHARS_DENSE)]
                put(wcol, wrow, ch, C["forest_dense"])

    lf = pygame.font.SysFont(None, 20)
    leg = "@ you   ? undiscovered   . path   ~~~ river and bay   ### bramble   ^^^ cliff   |!| deep woods   use <item> to cross"
    ls = lf.render(leg, True, (55, 75, 45))
    screen.blit(ls, ls.get_rect(center=(WIDTH//2, HEIGHT-MAP_INPUT_HEIGHT-8)))


def draw_map_screen(screen, font_mt, font_mb, font_in, state, input_text, cursor_on, last_cmd, last_response):
    screen.fill((9, 11, 8))
    draw_map_overlay(screen, font_mt, font_mb, state)
    iy = HEIGHT - MAP_INPUT_HEIGHT
    pygame.draw.rect(screen, (26, 32, 22), (0, iy, WIDTH, MAP_INPUT_HEIGHT))
    pygame.draw.rect(screen, (48, 65, 38), (0, iy, WIDTH, 2))

    cmd_y = iy + 6
    resp_y = iy + 30
    input_y = iy + MAP_INPUT_HEIGHT - font_in.get_height() - 12

    # Last command sent: dim green
    if last_cmd:
        screen.blit(font_in.render(f"> {last_cmd}", True, (90, 115, 70)), (PADDING, cmd_y))

    # Last game response: brighter, so it reads as feedback
    if last_response:
        wrapped = _wrap(last_response, font_in, WIDTH - (PADDING * 3))
        if wrapped:
            screen.blit(font_in.render(wrapped[0], True, (185, 205, 160)), (PADDING + 14, resp_y))

    # Keep map input anchored to the left with a cursor on the line below.
    display_text = f"> {input_text}"
    text_x = PADDING
    text_y = input_y
    screen.blit(font_in.render(display_text, True, (220, 235, 200)), (text_x, text_y))
    if cursor_on:
        cursor_x = text_x + font_in.size("> ")[0]
        cursor_y = min(HEIGHT - 6, text_y + font_in.get_height() + 2)
        pygame.draw.line(screen, (220, 235, 200), (cursor_x, cursor_y), (cursor_x + 10, cursor_y), 2)

    hf = pygame.font.SysFont(None, 18)
    hint = hf.render("M  close map     arrow keys or type to move", True, (42, 58, 32))
    screen.blit(hint, hint.get_rect(right=WIDTH - PADDING, top=iy + 8))


BASE_CARRY_LIMIT = 20

ITEM_TYPE_COLORS = {
    "resource": (70,  140,  65),
    "tool":     (175, 140,  45),
    "crafted":  (85,  115, 170),
}
ITEM_TYPE_LABELS = {
    "resource": "RESOURCE",
    "tool":     "TOOL",
    "crafted":  "CRAFTED",
}
EQUIP_SLOTS = [("Back", "backpack"), ("Hand", "hand"), ("Body", "body")]

# Inventory screen state (persists between opens)
_inv_selected   = 0      # selected card index
_inv_detail_msg = []     # lines shown in detail panel


def draw_inventory_screen(screen, state, selected_idx, detail_lines, flash_msg=""):
    """Draw inventory. Returns (new_selected_idx, drop_requested_item_or_None)."""
    ft  = pygame.font.SysFont(None, 40, bold=True)
    fh  = pygame.font.SysFont(None, 23, bold=True)
    fb  = pygame.font.SysFont(None, 21)
    fs  = pygame.font.SysFont(None, 18)
    ftg = pygame.font.SysFont(None, 16, bold=True)

    screen.fill((12, 14, 11))

    registry   = getattr(state, "item_registry", {})
    items_list = state.player.inventory_items()   # [(name, count), ...]
    carried    = state.player.carried_weight(registry)
    limit      = state.player.carry_limit(registry) if hasattr(state.player, "carry_limit") else BASE_CARRY_LIMIT

    ts = ft.render("INVENTORY", True, (200, 215, 185))
    screen.blit(ts, ts.get_rect(center=(WIDTH // 2, 26)))
    pygame.draw.line(screen, (40, 52, 33), (PADDING*2, 48), (WIDTH-PADDING*2, 48), 1)

    bx, by, bw, bh = PADDING*2, 56, WIDTH - PADDING*4, 12
    pygame.draw.rect(screen, (28, 33, 22), (bx, by, bw, bh), border_radius=3)
    ratio = min(carried / limit, 1.0)
    fill_col = (55,130,55) if ratio < 0.6 else (160,130,40) if ratio < 0.85 else (175,55,45)
    if ratio > 0:
        pygame.draw.rect(screen, fill_col, (bx, by, max(4,int(bw*ratio)), bh), border_radius=3)
    pygame.draw.rect(screen, (48, 60, 38), (bx, by, bw, bh), width=1, border_radius=3)
    torch_str = ""
    if hasattr(state.player, "torch_uses") and state.player.torch_uses is not None:
        torch_str = f"   Torch: {state.player.torch_uses} uses left"
    screen.blit(fs.render(f"Carried: {int(carried)} / {int(limit)} kg{torch_str}", True, (110,130,90)),
                (bx, by + bh + 4))

    LIST_LEFT  = PADDING * 2
    LIST_TOP   = by + bh + 24
    LIST_W     = int(WIDTH * 0.52)
    DETAIL_L   = LIST_LEFT + LIST_W + PADDING * 3
    DETAIL_W   = WIDTH - DETAIL_L - PADDING * 2
    CARD_H, CARD_GAP = 46, 5

    selected_idx = max(0, min(selected_idx, len(items_list) - 1)) if items_list else 0

    if not items_list:
        screen.blit(fb.render("Your pack is empty.", True, (70, 85, 60)),
                    (LIST_LEFT, LIST_TOP + 8))
    else:
        y = LIST_TOP
        for i, (name, count) in enumerate(items_list):
            rect = pygame.Rect(LIST_LEFT, y, LIST_W, CARD_H)
            selected = (i == selected_idx)

            bg  = (30, 38, 24) if selected else (18, 22, 15)
            bdr = (90,140,65)  if selected else (40, 50, 33)
            pygame.draw.rect(screen, bg,  rect, border_radius=5)
            pygame.draw.rect(screen, bdr, rect, width=1 if not selected else 2, border_radius=5)

            display = name.replace("_", " ")
            screen.blit(fh.render(f"{display}  ×{count}", True, (215,220,200) if selected else (170,178,158)),
                        (rect.x+10, rect.y+7))

            data   = registry.get(name, {})
            uw     = data.get("weight", 0)
            screen.blit(fs.render(f"{uw*count} kg", True, (100,115,85)), (rect.x+10, rect.y+28))

            itype  = data.get("type", "")
            ttext  = ITEM_TYPE_LABELS.get(itype, itype.upper())
            if data.get("readable"): ttext = "READABLE"
            if data.get("carry_bonus"): ttext = f"+{data['carry_bonus']}kg PACK"
            tcol   = ITEM_TYPE_COLORS.get(itype, (80,80,80))
            if data.get("readable"): tcol = (140, 100, 170)
            if data.get("carry_bonus"): tcol = (100, 160, 140)
            tsurf  = ftg.render(ttext, True, tcol)
            screen.blit(tsurf, (rect.right - tsurf.get_width() - 10, rect.y + 15))

            y += CARD_H + CARD_GAP

    pygame.draw.line(screen, (38, 48, 30), (DETAIL_L - PADDING, LIST_TOP),
                     (DETAIL_L - PADDING, HEIGHT - 60), 1)

    if items_list and 0 <= selected_idx < len(items_list):
        sel_name, sel_count = items_list[selected_idx]
        data = registry.get(sel_name, {})

        screen.blit(fh.render(sel_name.replace("_"," ").upper(), True, (190,205,170)),
                    (DETAIL_L, LIST_TOP))
        screen.blit(fs.render(f"Weight: {data.get('weight',0)} kg each  ·  Carrying: {sel_count}", True, (100,115,85)),
                    (DETAIL_L, LIST_TOP + 22))
        pygame.draw.line(screen, (38,48,30), (DETAIL_L, LIST_TOP+36),
                         (DETAIL_L+DETAIL_W, LIST_TOP+36), 1)

        # Description
        desc = data.get("desc","No description.")
        dy   = LIST_TOP + 44
        for word_line in _wrap(desc, fb, DETAIL_W):
            screen.blit(fb.render(word_line, True, (165,178,148)), (DETAIL_L, dy))
            dy += 20

        # Detail lines (from examine / feedback)
        if detail_lines:
            dy += 10
            for dl in detail_lines:
                screen.blit(fs.render(dl, True, (120,140,100)), (DETAIL_L, dy))
                dy += 17

        # DROP button
        drop_rect = pygame.Rect(DETAIL_L, HEIGHT - 88, 120, 34)
        mp = pygame.mouse.get_pos()
        drop_hov = drop_rect.collidepoint(mp)
        pygame.draw.rect(screen, (55,30,25) if drop_hov else (35,20,18),
                         drop_rect, border_radius=5)
        pygame.draw.rect(screen, (120,60,50) if drop_hov else (70,38,32),
                         drop_rect, width=1, border_radius=5)
        screen.blit(fb.render("Drop", True, (210,140,130) if drop_hov else (160,100,90)),
                    (drop_rect.x+28, drop_rect.y+8))

    eq_y = LIST_TOP
    eq_title_x = DETAIL_L
    # (drawn below detail if room)

    # Flash message
    if flash_msg:
        fms = fb.render(flash_msg, True, (200,215,160))
        screen.blit(fms, fms.get_rect(center=(WIDTH//2, HEIGHT - 40)))

    # Controls hint
    screen.blit(fs.render("↑↓  select    D  drop    R  read    I / ESC  close", True, (50, 65, 40)),
                (PADDING*2, HEIGHT - 18))

    pygame.display.flip()
    return selected_idx


def _wrap(text, font, max_w):
    """Word-wrap text to fit max_w pixels."""
    words  = text.split()
    lines  = []
    cur    = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


ARROW_DIRS = {
    pygame.K_UP:    "north",
    pygame.K_DOWN:  "south",
    pygame.K_RIGHT: "east",
    pygame.K_LEFT:  "west",
}


def _dispatch(cmd, state, log_lines):
    log_lines.append(f"> {cmd}")
    from engine.parser import parse_command
    v, t = parse_command(cmd)
    result = state.process_command(v, t)
    log_lines.extend(result)
    # Return last meaningful line for the map status bar
    for line in reversed(result):
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _is_save_command(cmd: str) -> bool:
    norm = cmd.strip().lower()
    return norm in ("save", "savegame", "save game")



def run_game(screen, clock, state=None):
    font    = pygame.font.SysFont(None, 24)
    font_b  = pygame.font.SysFont(None, 24, bold=True)
    font_mt = pygame.font.SysFont(None, 42, bold=True)
    font_mb = pygame.font.SysFont(None, 24)

    if state is None:
        state = load_game_state()
    if state is None:
        state = GameState()
        log_lines = list(state.get_intro_lines()) + list(state.describe_current_room())
    else:
        log_lines = ["\nSession resumed."] + list(state.describe_current_room())
    input_text = ""
    scroll = 0
    mode          = "game"   # "game" | "map" | "inventory"
    inv_selected  = 0
    inv_detail    = []
    inv_flash     = ""
    inv_flash_t   = 0
    last_cmd      = ""
    last_response = ""   # last game reply shown on map

    while True:
        clock.tick(FPS)
        cursor_on = (pygame.time.get_ticks() % 900) < 450

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                save_game_state(state)
                return "quit", state
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if mode in ("map", "inventory"):
                        mode = "game"; continue
                    save_game_state(state)
                    return "menu", state
                if ev.key == pygame.K_F5:
                    save_game_state(state)
                    log_lines.extend(["> save", "Game saved."])
                    log_lines = clamp_log(log_lines)
                    last_cmd = "save"
                    last_response = "Game saved."
                    continue
                if ev.key == pygame.K_m and not input_text:
                    mode = "map" if mode != "map" else "game"; continue
                if ev.key == pygame.K_i and not input_text:
                    mode = "inventory" if mode != "inventory" else "game"; continue

                if ev.key in ARROW_DIRS:
                    scroll = 0
                    cmd = f"go {ARROW_DIRS[ev.key]}"
                    last_cmd = cmd
                    last_response = _dispatch(cmd, state, log_lines)
                    save_game_state(state)
                    log_lines = clamp_log(log_lines)
                    if not state.is_running:
                        clear_game_state()
                        return "menu", None
                    continue

                if mode == "inventory":
                    items_list = state.player.inventory_items()
                    if ev.key == pygame.K_UP:
                        inv_selected = max(0, inv_selected - 1)
                    elif ev.key == pygame.K_DOWN:
                        inv_selected = min(len(items_list)-1, inv_selected+1) if items_list else 0
                    elif ev.key == pygame.K_d and items_list:
                        sel_name = items_list[inv_selected][0]
                        result   = state.process_command("drop", sel_name)
                        inv_flash   = result[0] if result else ""
                        inv_flash_t = pygame.time.get_ticks()
                        log_lines.extend(result)
                        log_lines   = clamp_log(log_lines)
                        save_game_state(state)
                        inv_selected = min(inv_selected, max(0, len(state.player.inventory_items())-1))
                    elif ev.key == pygame.K_r and items_list:
                        sel_name = items_list[inv_selected][0]
                        result   = state.process_command("read", sel_name)
                        inv_detail  = result
                        inv_flash   = result[0] if result else ""
                        inv_flash_t = pygame.time.get_ticks()
                        log_lines.extend(result)
                        log_lines   = clamp_log(log_lines)
                        save_game_state(state)

                elif mode == "game":
                    if   ev.key == pygame.K_PAGEUP:    scroll += 5
                    elif ev.key == pygame.K_PAGEDOWN:  scroll = max(0, scroll-5)
                    elif ev.key == pygame.K_RETURN:
                        cmd = input_text.strip(); input_text = ""
                        if cmd:
                            if _is_save_command(cmd):
                                last_cmd = cmd
                                save_game_state(state)
                                log_lines.extend([f"> {cmd}", "Game saved."])
                                log_lines = clamp_log(log_lines)
                                last_response = "Game saved."
                                continue
                            scroll = 0; last_cmd = cmd
                            last_response = _dispatch(cmd, state, log_lines)
                            save_game_state(state)
                            log_lines = clamp_log(log_lines)
                            if not state.is_running:
                                clear_game_state()
                                return "menu", None
                    elif ev.key == pygame.K_BACKSPACE:  input_text = input_text[:-1]
                    elif ev.unicode and ev.unicode.isprintable(): input_text += ev.unicode
                elif mode == "map":
                    if ev.key == pygame.K_RETURN:
                        cmd = input_text.strip(); input_text = ""
                        if cmd:
                            if _is_save_command(cmd):
                                last_cmd = cmd
                                save_game_state(state)
                                log_lines.extend([f"> {cmd}", "Game saved."])
                                log_lines = clamp_log(log_lines)
                                last_response = "Game saved."
                                continue
                            last_cmd = cmd
                            last_response = _dispatch(cmd, state, log_lines)
                            save_game_state(state)
                            log_lines = clamp_log(log_lines)
                            if not state.is_running:
                                clear_game_state()
                                return "menu", None
                    elif ev.key == pygame.K_BACKSPACE:  input_text = input_text[:-1]
                    elif ev.unicode and ev.unicode.isprintable(): input_text += ev.unicode

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and mode == "inventory":
                items_list = state.player.inventory_items()
                if items_list and 0 <= inv_selected < len(items_list):
                    DETAIL_L = PADDING*2 + int(WIDTH*0.52) + PADDING*3
                    drop_rect = pygame.Rect(DETAIL_L, HEIGHT - 88, 120, 34)
                    if drop_rect.collidepoint(ev.pos):
                        sel_name    = items_list[inv_selected][0]
                        result      = state.process_command("drop", sel_name)
                        inv_flash   = result[0] if result else ""
                        inv_flash_t = pygame.time.get_ticks()
                        log_lines.extend(result)
                        log_lines   = clamp_log(log_lines)
                        save_game_state(state)
                        inv_selected = min(inv_selected, max(0, len(state.player.inventory_items())-1))

        # Clear flash after 2 seconds
        if inv_flash and pygame.time.get_ticks() - inv_flash_t > 2000:
            inv_flash = ""

        if mode == "inventory":
            inv_selected = draw_inventory_screen(screen, state, inv_selected, inv_detail, inv_flash)
        elif mode == "map":
            draw_map_screen(screen, font_mt, font_mb, font, state, input_text, cursor_on, last_cmd, last_response)
        else:
            draw_game_screen(screen, font, font_b, log_lines, input_text, scroll, cursor_on)
        pygame.display.flip()

    return "menu", state


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The Dark Forest")
    clock = pygame.time.Clock()
    saved_state = None
    while True:
        choice = run_menu(screen, clock)
        if choice == "quit": break
        if choice == "how":
            run_instructions(screen, clock)
            continue
        if choice == "reset":
            clear_game_state()
            saved_state = None
            continue
        if choice == "start":
            clear_game_state()
            saved_state = None
            action, saved_state = run_game(screen, clock, None)
            if action == "quit":
                break
            continue
        if choice == "continue":
            action, saved_state = run_game(screen, clock, saved_state)
            if action == "quit":
                break
            continue
    pygame.quit()


if __name__ == "__main__":
    main()
