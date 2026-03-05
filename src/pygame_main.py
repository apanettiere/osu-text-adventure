import pygame
from engine.game_state import GameState, MAP_ROOM_POS
from engine.parser import parse_command

WIDTH  = 960
HEIGHT = 640
FPS    = 60
PADDING     = 16
LINE_HEIGHT = 26
INPUT_HEIGHT = 56
MAX_LOG_LINES = 300


def clamp_log(lines):
    return lines[-MAX_LOG_LINES:] if len(lines) > MAX_LOG_LINES else lines

def point_in_rect(pos, rect):
    return rect.collidepoint(pos[0], pos[1])

def draw_button(screen, rect, text, font, hovered):
    pygame.draw.rect(screen, (60,60,60) if hovered else (45,45,45), rect, border_radius=10)
    pygame.draw.rect(screen, (90,90,90), rect, width=2, border_radius=10)
    lbl = font.render(text, True, (245,245,245))
    screen.blit(lbl, lbl.get_rect(center=rect.center))

# ── How to Play ───────────────────────────────────────────────────────────────

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
        ("MOVING",
         "Arrow keys move you one tile at a time — no typing needed.",
         "Or type:  go north / south / east / west     Shortcuts: n s e w",
         "Rooms are walkable. Reach the edge to move to the next area.",
        ),
        ("LOOKING & GATHERING",
         "look (or l) to re-read the room.  Walk near objects to see clues.",
         "g wood / g stone / g food to gather.   i to check inventory.",
        ),
        ("THE MAP  (press M)",
         "One connected map that reveals as you explore.",
         "@ is you.  ? is an area you know of but have not entered.",
         "Obstacles — rivers, brambles, cliffs — are shown where they block the path.",
         "Arrow keys and typing still work while the map is open.",
        ),
        ("OTHER",
         "inventory/i   items        look/l    room",
         "quit/q        exit         ESC       main menu",
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
    sr = pygame.Rect(0,0,260,56); sr.center = (WIDTH//2, HEIGHT//2+10)
    hr = pygame.Rect(0,0,260,56); hr.center = (WIDTH//2, HEIGHT//2+80)
    qr = pygame.Rect(0,0,260,56); qr.center = (WIDTH//2, HEIGHT//2+150)

    while True:
        clock.tick(FPS)
        mp = pygame.mouse.get_pos()
        sh = point_in_rect(mp,sr); hh = point_in_rect(mp,hr); qh = point_in_rect(mp,qr)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return "quit"
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return "quit"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if sh: return "start"
                if hh: return "how"
                if qh: return "quit"
        screen.fill((14,14,14))
        t = ft.render("THE DARK FOREST", True, (240,240,240))
        screen.blit(t, t.get_rect(center=(WIDTH//2, HEIGHT//2-100)))
        hint = fh.render("A text-based survival adventure", True, (190,190,190))
        screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT//2-58)))
        draw_button(screen, sr, "Start Game",  fb, sh)
        draw_button(screen, hr, "How to Play", fb, hh)
        draw_button(screen, qr, "Quit",        fb, qh)
        pygame.display.flip()

# ── Game text screen ──────────────────────────────────────────────────────────

def draw_game_screen(screen, font, font_bold, log_lines, input_text, scroll_offset, cursor_on):
    screen.fill((18,18,18))
    ol = PADDING; ot = PADDING; ob = HEIGHT - INPUT_HEIGHT - PADDING
    oh = ob - ot
    pygame.draw.rect(screen, (28,28,28), (ol-8, ot-8, WIDTH-PADDING*2+16, oh+16), border_radius=8)
    lf = max(1, oh // LINE_HEIGHT)
    si = max(0, len(log_lines) - lf - scroll_offset)
    y = ot
    for line in log_lines[si:si+lf]:
        sf = font_bold.render(line.strip(), True, (240,240,240)) if line.startswith("\n")              else font.render(line, True, (220,220,220))
        screen.blit(sf, (ol, y)); y += LINE_HEIGHT
    iy = HEIGHT - INPUT_HEIGHT
    pygame.draw.rect(screen, (40,40,40), (0, iy, WIDTH, INPUT_HEIGHT))
    pygame.draw.rect(screen, (60,60,60), (0, iy, WIDTH, 2))
    # Blinking cursor: append | when cursor_on
    display_text = "> " + input_text + ("|" if cursor_on else " ")
    screen.blit(font.render(display_text, True, (255,255,255)), (PADDING, iy+18))


MAP_ROOM_SIZE = {
    "shadow_trees":    (15, 9),
    "clearing":        (13, 13),
    "soggy_path":      (9,  15),
    "stone_foothills": (13, 9),
    "fallen_pines":    (13, 9),
}

OBSTACLE_PASSAGES = [
    ("col", 20, 9,  11, "bramble"),   # between shadow_trees (bottom row 8) and clearing (top row 12)
    ("col", 21, 25, 27, "river"),     # between clearing (bottom row 24) and soggy_path (top row 28)
    ("row", 18, 27, 29, "cliff"),     # between clearing (right col 26) and stone_foothills (left col 30)
    ("row", 18, 11, 13, "deepwood"),  # between fallen_pines (right col 12) and clearing (left col 14)
]

OBS_ART = {
    "bramble":  ["#","x","#","x","#"],
    "river":    ["~","~","~","~","~"],
    "cliff":    ["^","n","^","n","^"],
    "deepwood": ["|","!","|","!","|"],
}

OBS_COL = {
    "bramble":  (30,  60,  25),
    "river":    (30,  80, 120),
    "cliff":    (80,  72,  62),
    "deepwood": (25,  55,  20),
}

# Deep forest fill characters (vary by distance from room)
FOREST_CHARS_NEAR   = ["'", ",", "'", "."]
FOREST_CHARS_MID    = ["*", "'", "*", ",", "*"]
FOREST_CHARS_FAR    = ["^", "*", "^", "'", "^", "*"]
FOREST_CHARS_DENSE  = ["^", "^", "*", "^"]

# Map display area (cols, rows) — we render this window of world coords
REVEAL_RADIUS = 2  # must match game_state.py

MAP_WIN_COL0, MAP_WIN_ROW0 = -6, -4
MAP_WIN_COLS, MAP_WIN_ROWS = 60, 52

MAP_CENTER_COL = 21
MAP_CENTER_ROW = 20
MAP_RING_RADIUS = 26


def _room_at(wcol, wrow, rooms):
    """Return (room_id, local_col, local_row, is_inside_ellipse) or None."""
    for rid, (rx, ry) in MAP_ROOM_POS.items():
        if rid not in MAP_ROOM_SIZE:
            continue
        rw, rh = MAP_ROOM_SIZE[rid]
        if rx <= wcol < rx+rw and ry <= wrow < ry+rh:
            lc, lr = wcol - rx, wrow - ry
            return (rid, lc, lr)
    return None


def _ellipse_zone(col, row, rw, rh):
    cx = (rw-1)/2.0; cy = (rh-1)/2.0
    ax = max(cx-0.4, 1.0); ay = max(cy-0.4, 1.0)
    dx = (col-cx)/ax; dy = (row-cy)/ay
    d  = dx*dx + dy*dy
    if   d > 1.2:  return "outside"
    elif d > 0.70: return "border"
    else:          return "inside"


def _obstacle_at(wcol, wrow):
    """Return obstacle type string or None."""
    for axis, fixed, r0, r1, otype in OBSTACLE_PASSAGES:
        if axis == "col" and wcol == fixed and r0 <= wrow <= r1:
            return otype
        if axis == "row" and wrow == fixed and r0 <= wcol <= r1:
            return otype
    return None


def _dist_to_nearest_room(wcol, wrow):
    """Manhattan distance to nearest in-bounds room tile."""
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
    CELL = 11
    try:
        mf = pygame.font.SysFont("Courier New", CELL+1)
    except Exception:
        mf = pygame.font.SysFont(None, CELL+2)

    # Map pixel origin: centre the map window on screen
    map_px_w = MAP_WIN_COLS * CELL
    map_px_h = MAP_WIN_ROWS * CELL
    map_area_h = HEIGHT - INPUT_HEIGHT - 36
    opx = (WIDTH  - map_px_w) // 2
    opy = (HEIGHT - INPUT_HEIGHT - map_px_h) // 2 + 18

    # Title
    ts = font_title.render("MAP", True, (140, 170, 110))
    screen.blit(ts, ts.get_rect(center=(WIDTH//2, opy-22)))

    visited = state.player.visited_tiles
    cur_rid  = state.current_room_id
    explored = state.player.explored_rooms
    discovered = state.player.discovered_rooms
    rooms    = state.rooms

    # Colour palette
    C = {
        "room_floor_cur":  (62, 55, 42),
        "room_floor_exp":  (30, 27, 20),
        "room_floor_fog":  (16, 16, 12),
        "tree_cur":        (80,130, 60),
        "tree_exp":        (48, 80, 42),
        "tree_fog":        (26, 38, 20),
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
        if 0 <= px < WIDTH and 0 <= py < HEIGHT - INPUT_HEIGHT:
            screen.blit(mf.render(ch, True, color), (px, py))

    for wrow in range(MAP_WIN_ROW0, MAP_WIN_ROW0 + MAP_WIN_ROWS):
        for wcol in range(MAP_WIN_COL0, MAP_WIN_COL0 + MAP_WIN_COLS):

            # Outside the circular overall boundary — skip
            ddx = wcol - MAP_CENTER_COL; ddy = wrow - MAP_CENTER_ROW
            if ddx*ddx*0.9 + ddy*ddy > MAP_RING_RADIUS*MAP_RING_RADIUS:
                continue

            tile_visited = (wcol, wrow) in visited

            obs = _obstacle_at(wcol, wrow)
            if obs:
                if tile_visited:
                    # Pick char based on position along the passage
                    arr = OBS_ART[obs]
                    for axis, fixed, r0, r1, otype in OBSTACLE_PASSAGES:
                        if otype == obs:
                            idx_val = wrow if axis == "col" else wcol
                            ch = arr[(idx_val - r0) % len(arr)]
                            put(wcol, wrow, ch, OBS_COL[obs])
                            break
                elif _dist_to_nearest_room(wcol, wrow) <= REVEAL_RADIUS+1:
                    # Close to an explored room — show dark hint
                    put(wcol, wrow, ".", (22,22,18))
                continue

            room_info = _room_at(wcol, wrow, rooms)
            if room_info:
                rid, lc, lr = room_info
                rw, rh = MAP_ROOM_SIZE.get(rid, (1,1))
                zone = _ellipse_zone(lc, lr, rw, rh)

                if zone == "outside":
                    pass  # part of bounding box but outside circle — treat as forest
                else:
                    is_cur  = (rid == cur_rid)
                    is_exp  = rid in explored
                    is_disc = rid in discovered

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
                            tc = C["tree_cur"] if is_cur else (C["tree_exp"] if is_exp else C["tree_fog"])
                            put(wcol, wrow, tchar(lc,lr,rw,rh), tc)
                        elif is_disc:
                            put(wcol, wrow, ".", C["tree_fog"])

                    else:  # inside
                        if is_cur and tile_visited:
                            ch = "," if (lc+lr)%4==0 else "."
                            put(wcol, wrow, ch, C["room_floor_cur"])
                        elif is_exp and tile_visited:
                            ch = "," if (lc+lr)%5==0 else "."
                            put(wcol, wrow, ch, C["room_floor_exp"])
                        elif is_disc:
                            # Fog — faint silhouette
                            if (lc+lr)%6 == 0:
                                put(wcol, wrow, ",", C["room_floor_fog"])

                    # Features (explored only, inside only)
                    if is_exp and zone == "inside":
                        room = rooms.get(rid)
                        if room:
                            for feat in room.features:
                                fx, fy = feat.get("pos",(-1,-1))
                                if fx == lc and fy == lr:
                                    if tile_visited:
                                        put(wcol, wrow, feat.get("label","?"), C["feature"])

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

    # Legend
    lf = pygame.font.SysFont(None, 20)
    leg = "@ you   ? unexplored   ~~~ river   ### bramble   ^^^ cliff   |!| deep woods"
    ls = lf.render(leg, True, (55, 75, 45))
    screen.blit(ls, ls.get_rect(center=(WIDTH//2, HEIGHT-INPUT_HEIGHT-8)))


def draw_map_screen(screen, font_mt, font_mb, font_in, state, input_text, cursor_on, last_cmd, last_response):
    screen.fill((9, 11, 8))
    draw_map_overlay(screen, font_mt, font_mb, state)
    iy = HEIGHT - INPUT_HEIGHT
    pygame.draw.rect(screen, (26, 32, 22), (0, iy, WIDTH, INPUT_HEIGHT))
    pygame.draw.rect(screen, (48, 65, 38), (0, iy, WIDTH, 2))

    # Last command sent — dim green
    if last_cmd:
        screen.blit(font_in.render(f"> {last_cmd}", True, (90, 115, 70)), (PADDING, iy + 4))

    # Last game response — brighter, so it reads as feedback
    if last_response:
        screen.blit(font_in.render(last_response, True, (185, 205, 160)), (PADDING + 14, iy + 22))

    # Input field: only show if something is being typed, with blinking cursor
    if input_text or cursor_on:
        cur = "|" if cursor_on else ""
        screen.blit(font_in.render(f"> {input_text}{cur}", True, (220, 235, 200)),
                    (WIDTH // 2, iy + 13))

    hf = pygame.font.SysFont(None, 18)
    hint = hf.render("M  close map     arrow keys or type to move", True, (42, 58, 32))
    screen.blit(hint, hint.get_rect(right=WIDTH - PADDING, bottom=HEIGHT - 4))


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

    # ── Detail / action panel ─────────────────────────────────────────────────
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



def run_game(screen, clock):
    font    = pygame.font.SysFont(None, 24)
    font_b  = pygame.font.SysFont(None, 24, bold=True)
    font_mt = pygame.font.SysFont(None, 42, bold=True)
    font_mb = pygame.font.SysFont(None, 24)

    state = GameState()
    log_lines = list(state.describe_current_room())
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
            if ev.type == pygame.QUIT: return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if mode in ("map", "inventory"):
                        mode = "game"; continue
                    return
                if ev.key == pygame.K_m and not input_text:
                    mode = "map" if mode != "map" else "game"; continue
                if ev.key == pygame.K_i and not input_text:
                    mode = "inventory" if mode != "inventory" else "game"; continue

                if ev.key in ARROW_DIRS:
                    scroll = 0
                    cmd = f"go {ARROW_DIRS[ev.key]}"
                    last_cmd = cmd
                    last_response = _dispatch(cmd, state, log_lines)
                    log_lines = clamp_log(log_lines)
                    if not state.is_running: return
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
                        inv_selected = min(inv_selected, max(0, len(state.player.inventory_items())-1))
                    elif ev.key == pygame.K_r and items_list:
                        sel_name = items_list[inv_selected][0]
                        result   = state.process_command("read", sel_name)
                        inv_detail  = result
                        inv_flash   = result[0] if result else ""
                        inv_flash_t = pygame.time.get_ticks()
                        log_lines.extend(result)
                        log_lines   = clamp_log(log_lines)

                elif mode == "game":
                    if   ev.key == pygame.K_PAGEUP:    scroll += 5
                    elif ev.key == pygame.K_PAGEDOWN:  scroll = max(0, scroll-5)
                    elif ev.key == pygame.K_RETURN:
                        cmd = input_text.strip(); input_text = ""
                        if cmd:
                            scroll = 0; last_cmd = cmd
                            last_response = _dispatch(cmd, state, log_lines)
                            log_lines = clamp_log(log_lines)
                            if not state.is_running: return
                    elif ev.key == pygame.K_BACKSPACE:  input_text = input_text[:-1]
                    elif ev.unicode and ev.unicode.isprintable(): input_text += ev.unicode
                elif mode == "map":
                    if ev.key == pygame.K_RETURN:
                        cmd = input_text.strip(); input_text = ""
                        if cmd:
                            last_cmd = cmd
                            last_response = _dispatch(cmd, state, log_lines)
                            log_lines = clamp_log(log_lines)
                            if not state.is_running: return
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


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The Dark Forest")
    clock = pygame.time.Clock()
    while True:
        choice = run_menu(screen, clock)
        if choice == "quit": break
        if choice == "how":  run_instructions(screen, clock)
        if choice == "start": run_game(screen, clock)
    pygame.quit()


if __name__ == "__main__":
    main()