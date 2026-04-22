import json
from pathlib import Path
from functools import lru_cache
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
MAP_GLYPH_CACHE: dict[tuple[int, str, tuple[int, int, int]], pygame.Surface] = {}


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
         "Delete removes forward. Left/Right move cursor. Home/End jump to line start or end.",
         "M opens map. I opens inventory. Esc closes map or inventory.",
         "F5 or type save to save now. Esc from game view returns to menu and saves.",
         "In inventory: Up/Down select, D drops selected item, R reads selected item.",
        ),
        ("COMMANDS",
         "Movement words: go north/south/east/west, or shortcuts n s e w.",
         "look (or l) to re-read the room. Walk near objects to see clues.",
         "take <item>, examine <feature>, enter <feature>, use <item>, read <item>.",
         "gather wood, gather stone, or gather food. craft list shows recipes; craft <item> builds gear.",
         "drop <item> places one carried item in the room.",
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


def run_victory_screen(screen, clock, state):
    ft = pygame.font.SysFont("Courier New", 54, bold=True)
    fs = pygame.font.SysFont("Courier New", 34, bold=True)
    fb = pygame.font.SysFont(None, 23)
    ff = pygame.font.SysFont(None, 20)
    fa = pygame.font.SysFont("Courier New", 21, bold=True)
    f_map_t = pygame.font.SysFont(None, 42, bold=True)
    f_map_b = pygame.font.SysFont(None, 24)
    br = pygame.Rect(0, 0, 250, 48)
    br.center = (WIDTH // 2, HEIGHT - 54)

    end_lines = list(getattr(state, "end_lines", []))
    shown_lines = [ln for ln in end_lines if ln and ln.strip()][:6]
    if not shown_lines:
        shown_lines = [
            "You strike the dry fuel in the lantern room and the fire catches.",
            "The lighthouse lens turns and a white beam punches through the dark sky.",
            "You signal three long, three short, three long flashes: SOS.",
            "A small seaplane skims the bay and lands near the cliff base.",
            "The sky opens at dawn and rescue crews pull you aboard.",
            "You made it. Rescue has arrived.",
        ]

    cell_w = fa.size("M")[0]
    cell_h = 22

    while True:
        clock.tick(FPS)

        mp = pygame.mouse.get_pos()
        bh = point_in_rect(mp, br)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and bh:
                return

        # Use the existing world map renderer to keep the game's visual language,
        # focused on the mountain pass where the external lighthouse sits.
        screen.fill((9, 11, 8))
        draw_map_overlay(
            screen,
            f_map_t,
            f_map_b,
            state,
            show_title=False,
            show_legend=False,
            focus_room_id="mountain_pass",
        )

        # Slight dark veil to unify contrast and keep text readable.
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 12, 20, 82))
        screen.blit(veil, (0, 0))

        # Text section: isolated from art and beam; wrap lines to avoid overlap.
        panel = pygame.Rect(56, 36, WIDTH - 112, 278)
        pygame.draw.rect(screen, (2, 16, 28), panel, border_radius=10)
        pygame.draw.rect(screen, (58, 66, 74), panel, width=1, border_radius=10)

        title = ft.render("SOS SIGNAL SEEN", True, (234, 238, 228))
        subtitle = fs.render("RESCUE CONFIRMED", True, (170, 188, 162))
        screen.blit(title, (panel.x + 44, panel.y + 30))
        screen.blit(subtitle, (panel.x + 44, panel.y + 76))

        text_x = panel.x + 44
        text_y = panel.y + 132
        text_w = panel.width - 88
        wrapped_lines = []
        for ln in shown_lines:
            wrapped_lines.extend(_wrap(ln, fb, text_w))
        line_h = fb.get_height() + 6
        max_lines = max(1, (panel.bottom - 16 - text_y) // line_h)
        wrapped_lines = wrapped_lines[:max_lines]
        for ln in wrapped_lines:
            line = fb.render(ln, True, (212, 218, 206))
            screen.blit(line, (text_x, text_y))
            text_y += line_h

        # Scene section: map lighthouse in the middle with a yellow beam over water.
        scene_anchor_y = panel.bottom + 142
        scene_mid_x = WIDTH // 2 - cell_w
        water_y = HEIGHT - 116

        # Water band in map palette.
        for row in range(2):
            wline = "~ " * 42
            surf = fa.render(wline, True, (104, 146, 180))
            screen.blit(surf, (panel.x + 44, water_y + row * 20))

        # Draw the existing map lighthouse sprite in the middle.
        for dx, dy, ch, col in LIGHTHOUSE_SPRITE:
            x = scene_mid_x + dx * cell_w
            yrow = scene_anchor_y + dy * cell_h
            # Keep the scene clean and readable; preserve lighthouse colors from map sprite.
            surf = fa.render(ch, True, col)
            screen.blit(surf, (x, yrow))

        # Keep only the SOS signal readout (no long yellow beam line).
        sig = "SOS"
        sig_x = scene_mid_x + cell_w * 3
        sig_y = scene_anchor_y - cell_h + 4
        if sig_y < panel.bottom + 12:
            sig_y = panel.bottom + 12
        sig_prefix_surf = fa.render("signal: ", True, (226, 206, 132))
        sig_value_surf = fa.render(sig, True, (226, 206, 132))
        screen.blit(sig_prefix_surf, (sig_x, sig_y))
        screen.blit(sig_value_surf, (sig_x + sig_prefix_surf.get_width(), sig_y))

        draw_button(screen, br, "Return to Menu", fb, bh)
        foot = ff.render("ENTER / SPACE / ESC to continue", True, (118, 132, 114))
        screen.blit(foot, foot.get_rect(center=(WIDTH // 2, HEIGHT - 16)))
        pygame.display.flip()


def _finish_after_game_end(screen, clock, state):
    if getattr(state, "game_outcome", None) == "won":
        run_victory_screen(screen, clock, state)
    clear_game_state()
    return "menu", None


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


def draw_game_screen(screen, font, font_bold, log_lines, input_text, cursor_idx, scroll_offset, cursor_on):
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
        prefix = "> " + input_text[:max(0, min(cursor_idx, len(input_text)))]
        cursor_x = text_x + font.size(prefix)[0]
        pygame.draw.line(screen, (255,255,255), (cursor_x, text_y + 22), (cursor_x + 10, text_y + 22), 2)


MAP_ROOM_SIZE = {
    "thick_forest":   (19, 13),
    "clearing":       (17, 17),
    "riverbank":      (17, 13),
    "river_run":      (13, 11),
    "river_lake":     (11,  9),
    "cave_entrance":  (13, 11),
    "cabin_interior": (13,  9),
    "cave_chamber":   (13,  9),
    "far_shore":      (13,  9),
    "shed_interior":  ( 9,  7),
    "open_waters":    (36, 52),
    "mountain_pass":  (17, 13),
    "lighthouse_interior": (15, 11),
    "lighthouse_top":      (17, 11),
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
    "lake_channel": (132, 176, 198),
    "jagged_reef":  (142, 146, 156),
    "cave_tunnel":  (100, 126, 136),
    "loft_ladder":  (165, 148, 108),
    "cabin_bunk":   (142, 120, 95),
    "worktable":    (152, 126, 92),
    "stone_column": (160, 160, 166),
    "echo_pool":    (86, 130, 168),
    "chamber_ledge": (132, 132, 138),
    "lighthouse":   (230, 225, 170),
    "cliff_edge":   (175, 170, 162),
    "tide_pool":     (80, 135, 170),
    "spiral_stairs": (185, 175, 140),
    "fogged_window": (145, 165, 175),
    "maintenance_locker": (130, 135, 145),
    "winch_console": (160, 145, 110),
    "signal_brazier": (220, 120, 65),
    "signal_lens":    (210, 235, 240),
    "shutter_crank":  (180, 150, 90),
    "signal_lever":   (205, 180, 105),
    "catwalk_hatch":  (165, 150, 130),
    "tool_shed":      (140, 115, 75),
    "hook_wall":      (155, 140, 115),
    "broken_shelf":   (130, 110, 80),
    "x_marks_spot":   (210, 175, 60),
    "driftwood_pile": (165, 150, 120),
    "reed_bank":      (85, 120, 70),
    "north_island":   (206, 190, 120),
    "main_island":    (195, 178, 110),
    "west_isle":      (160, 155, 145),
}

LIGHTHOUSE_SPRITE = [
    (0, -4, "^", (255, 72, 72)),
    (1, -4, "-", (255, 160, 115)),
    (2, -4, "-", (255, 184, 126)),
    (3, -4, "-", (255, 210, 136)),
    (-1, -3, "/", (238, 238, 238)),
    (0, -3, "A", (250, 250, 250)),
    (1, -3, "\\", (238, 238, 238)),
    (-1, -2, "|", (210, 58, 60)),
    (0, -2, "H", (248, 248, 248)),
    (1, -2, "|", (210, 58, 60)),
    (-1, -1, "|", (210, 58, 60)),
    (0, -1, "O", (246, 246, 246)),
    (1, -1, "|", (210, 58, 60)),
    (-1, 0, "|", (210, 58, 60)),
    (0, 0, "H", (248, 248, 248)),
    (1, 0, "|", (210, 58, 60)),
    (-2, 1, "/", (214, 214, 214)),
    (-1, 1, "_", (214, 214, 214)),
    (0, 1, "_", (214, 214, 214)),
    (1, 1, "_", (214, 214, 214)),
    (2, 1, "\\", (214, 214, 214)),
]

CABIN_EXTERIOR_SPRITE = [
    (-2, -1, "/", (186, 162, 122)),
    (-1, -1, "^", (212, 186, 142)),
    (0, -1, "^", (212, 186, 142)),
    (1, -1, "\\", (186, 162, 122)),
    (-2, 0, "|", (162, 132, 96)),
    (-1, 0, "_", (176, 146, 108)),
    (0, 0, "_", (176, 146, 108)),
    (1, 0, "|", (162, 132, 96)),
    (-1, 1, "|", (148, 120, 86)),
    (0, 1, "|", (148, 120, 86)),
]

SPIRAL_STAIRS_SPRITE = [
    (-1, -1, "/", (208, 208, 206)),
    (0, -1, "@", (234, 220, 172)),
    (1, -1, "\\", (208, 208, 206)),
    (-1, 0, "|", (172, 172, 170)),
    (0, 0, "S", (224, 206, 152)),
    (1, 0, "|", (172, 172, 170)),
    (-1, 1, "\\", (196, 196, 194)),
    (0, 1, "o", (210, 200, 176)),
    (1, 1, "/", (196, 196, 194)),
]

FOGGED_WINDOW_SPRITE = [
    (-1, 0, "[", (160, 170, 182)),
    (0, 0, "=", (176, 196, 212)),
    (1, 0, "]", (160, 170, 182)),
    (0, -1, "^", (128, 144, 156)),
]

LOCKER_SPRITE = [
    (-1, 0, "[", (132, 140, 152)),
    (0, 0, "#", (160, 168, 178)),
    (1, 0, "]", (132, 140, 152)),
    (0, 1, "|", (118, 126, 138)),
]

WINCH_CONSOLE_SPRITE = [
    (-1, 0, "{", (158, 142, 114)),
    (0, 0, "O", (184, 168, 136)),
    (1, 0, "}", (158, 142, 114)),
    (0, 1, "|", (142, 126, 98)),
]

SIGNAL_LENS_SPRITE = [
    (0, -1, "^", (214, 230, 238)),
    (-1, 0, "(", (190, 212, 220)),
    (0, 0, "O", (236, 246, 250)),
    (1, 0, ")", (190, 212, 220)),
    (0, 1, "|", (164, 182, 190)),
]

SIGNAL_BRAZIER_SPRITE = [
    (0, -1, "^", (244, 166, 86)),
    (-1, 0, "(", (202, 148, 86)),
    (0, 0, "#", (230, 126, 68)),
    (1, 0, ")", (202, 148, 86)),
    (0, 1, "|", (168, 118, 70)),
]

SHUTTER_CRANK_SPRITE = [
    (-1, 0, "-", (174, 150, 102)),
    (0, 0, "@", (202, 180, 120)),
    (1, 0, "-", (174, 150, 102)),
    (0, 1, "|", (156, 134, 92)),
]

SIGNAL_LEVER_SPRITE = [
    (0, 0, "/", (216, 190, 124)),
    (1, -1, "o", (232, 210, 146)),
    (-1, 1, "|", (174, 150, 98)),
]

CATWALK_HATCH_SPRITE = [
    (-1, 0, "[", (172, 156, 136)),
    (0, 0, "=", (198, 180, 156)),
    (1, 0, "]", (172, 156, 136)),
    (0, 1, "|", (150, 136, 116)),
]

LOFT_LADDER_SPRITE = [
    (0, -1, "|", (176, 150, 110)),
    (1, -1, "|", (176, 150, 110)),
    (0, 0, "#", (196, 168, 126)),
    (1, 0, "#", (196, 168, 126)),
    (0, 1, "#", (196, 168, 126)),
    (1, 1, "#", (196, 168, 126)),
]

CABIN_BUNK_SPRITE = [
    (-2, 0, "[", (150, 126, 92)),
    (-1, 0, "_", (170, 142, 106)),
    (0, 0, "_", (170, 142, 106)),
    (1, 0, "]", (150, 126, 92)),
    (-1, -1, "~", (132, 116, 96)),
    (0, -1, "~", (132, 116, 96)),
    (1, -1, "~", (132, 116, 96)),
]

WORKTABLE_SPRITE = [
    (-1, 0, "_", (174, 144, 104)),
    (0, 0, "_", (174, 144, 104)),
    (1, 0, "_", (174, 144, 104)),
    (-1, 1, "|", (150, 122, 86)),
    (1, 1, "|", (150, 122, 86)),
    (0, -1, "i", (220, 194, 136)),
]

CABIN_DOOR_SPRITE = [
    (0, -1, "_", (150, 124,  90)),
    (0,  0, "D", (212, 178, 130)),
]

FIREPLACE_SPRITE = [
    (0, -1, "_", (140, 120,  96)),
    (0,  0, "*", (224, 128,  48)),
    (0,  1, "=", (116, 108,  96)),
]

SHELVES_SPRITE = [
    (-1, 0, "_", (170, 142, 106)),
    ( 0, 0, "_", (170, 142, 106)),
    (-1, 1, "o", (192, 168,  96)),
    ( 0, 1, "i", (218, 186, 122)),
]

RUG_SPRITE = [
    (-1, 0, "=", (140,  92,  52)),
    ( 0, 0, "~", (174, 114,  64)),
    ( 1, 0, "=", (140,  92,  52)),
]

STORAGE_CHEST_SPRITE = [
    (0, -1, "_", (140, 110,  72)),
    (0,  0, "#", (176, 138,  92)),
]

HANGING_HERBS_SPRITE = [
    (0, -1, "/", (120,  98,  64)),
    (0,  0, "y", (132, 158,  86)),
]

CAVE_TUNNEL_SPRITE = [
    (-1, -1, "/", (150, 158, 168)),
    (0, -1, "-", (154, 162, 170)),
    (1, -1, "\\", (150, 158, 168)),
    (-1, 0, "|", (138, 146, 154)),
    (1, 0, "|", (138, 146, 154)),
    (-1, 1, "\\", (126, 134, 144)),
    (0, 1, "_", (126, 134, 144)),
    (1, 1, "/", (126, 134, 144)),
]

FLAT_STONE_SPRITE = [
    (-1, 0, "_", (150, 150, 158)),
    (0, 0, "o", (176, 176, 184)),
    (1, 0, "_", (150, 150, 158)),
    (0, 1, "_", (136, 136, 144)),
]

STONE_COLUMN_SPRITE = [
    (0, -1, "|", (188, 188, 194)),
    (-1, 0, "(", (162, 162, 170)),
    (0, 0, "#", (198, 198, 204)),
    (1, 0, ")", (162, 162, 170)),
    (0, 1, "|", (176, 176, 182)),
]

ECHO_POOL_SPRITE = [
    (-1, 0, "(", (114, 160, 198)),
    (0, 0, "~", (138, 186, 224)),
    (1, 0, ")", (114, 160, 198)),
    (-1, 1, "~", (92, 136, 176)),
    (0, 1, "~", (92, 136, 176)),
    (1, 1, "~", (92, 136, 176)),
]

CHAMBER_LEDGE_SPRITE = [
    (-2, 0, "_", (154, 154, 162)),
    (-1, 0, "_", (154, 154, 162)),
    (0, 0, "_", (154, 154, 162)),
    (1, 0, "_", (154, 154, 162)),
    (2, 0, "_", (154, 154, 162)),
    (-2, 1, "/", (126, 126, 134)),
    (2, 1, "\\", (126, 126, 134)),
]

FEATURE_SPRITES = {
    "cabin": CABIN_EXTERIOR_SPRITE,
    "lighthouse": LIGHTHOUSE_SPRITE,
    "spiral_stairs": SPIRAL_STAIRS_SPRITE,
    "fogged_window": FOGGED_WINDOW_SPRITE,
    "maintenance_locker": LOCKER_SPRITE,
    "winch_console": WINCH_CONSOLE_SPRITE,
    "signal_lens": SIGNAL_LENS_SPRITE,
    "signal_brazier": SIGNAL_BRAZIER_SPRITE,
    "shutter_crank": SHUTTER_CRANK_SPRITE,
    "signal_lever": SIGNAL_LEVER_SPRITE,
    "catwalk_hatch": CATWALK_HATCH_SPRITE,
    "loft_ladder": LOFT_LADDER_SPRITE,
    "cabin_bunk": CABIN_BUNK_SPRITE,
    "worktable": WORKTABLE_SPRITE,
    "cabin_door": CABIN_DOOR_SPRITE,
    "fireplace": FIREPLACE_SPRITE,
    "shelves": SHELVES_SPRITE,
    "rug": RUG_SPRITE,
    "storage_chest": STORAGE_CHEST_SPRITE,
    "hanging_herbs": HANGING_HERBS_SPRITE,
    "cave_tunnel": CAVE_TUNNEL_SPRITE,
    "flat_stone": FLAT_STONE_SPRITE,
    "stone_column": STONE_COLUMN_SPRITE,
    "echo_pool": ECHO_POOL_SPRITE,
    "chamber_ledge": CHAMBER_LEDGE_SPRITE,
}

ITEM_MAP_COLORS = {
    "resource":  ( 85, 155,  75),
    "tool":      (195, 155,  50),
    "crafted":   ( 95, 125, 185),
    "readable":  (155, 115, 185),
    "equipment": (110, 175, 155),
}

FOREST_CHARS_NEAR  = ["'", ",", ".", "`", ";", "t"]
FOREST_CHARS_MID   = ["*", "'", "*", ",", "^", "t", "n"]
FOREST_CHARS_FAR   = ["^", "*", "^", "'", "^", "*", "n", "t"]
FOREST_CHARS_DENSE = ["^", "^", "*", "^", "T", "n"]

REVEAL_RADIUS = 2

INTERIOR_ONLY_ROOMS = {
    "cabin_interior",
    "cave_chamber",
    "shed_interior",
    "lighthouse_interior",
    "lighthouse_top",
}

FOCUSED_INTERIOR_ROOMS = {
    "cabin_interior",
    "lighthouse_interior",
    "lighthouse_top",
    "cave_entrance",
    "cave_chamber",
    "shed_interior",
}

TRANSPARENT_ROOMS = {
    "open_waters",
}

MAP_WIN_COL0, MAP_WIN_ROW0 = 0, 0
MAP_WIN_COLS, MAP_WIN_ROWS  = 114, 72

MAP_CENTER_COL = 24
MAP_CENTER_ROW = 24
MAP_RING_RADIUS = 120

RIVER_PATH_MAIN = [
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

RIVER_PATH_LAKE_BRANCH = [
    (26, 45),
    (30, 43),
    (34, 40),
    (39, 37),
    (43, 35),
    (47, 33),
    (50, 32),
    (53, 31),
]

RAFT_CROSSING_TILES = {
    (23, 45), (24, 45), (25, 45), (26, 45), (27, 45),
    (24, 46), (25, 46), (26, 46),
}

RAFT_ROUTE_TILES = {
    (26, 45), (30, 43), (34, 40), (39, 37), (43, 35), (47, 33), (50, 32), (53, 31),
}

RAFT_OCEAN_SPRITE_ANCHOR = (1, 24)
RAFT_OCEAN_SPRITE = [
    (-1, 0, "/", (214, 136, 58)),
    (0, 0, "=", (234, 154, 66)),
    (1, 0, "\\", (214, 136, 58)),
    (0, -1, "^", (246, 176, 86)),
    (0, 1, "_", (184, 112, 52)),
]

ISLAND_PATCHES = [
    (-15.0, 9.5, 6.2, 3.8),
    (-24.0, 23.5, 11.8, 7.4),
    (-13.5, 39.5, 8.9, 5.6),
    (-31.0, 35.0, 5.4, 3.3),
]

# Right-side highland biome: broader mountain pass descending into a lake valley.
MOUNTAIN_HIGHLAND_PATCHES = [
    (67.5, 12.0, 12.2, 8.4),
    (65.0, 20.8, 11.8, 8.4),
    (73.8, 17.8, 11.2, 7.8),
    (81.5, 15.8, 7.8, 6.0),   # narrowed right flank
    (84.2, 22.4, 5.8, 4.8),   # narrowed to taper the lower-right
    (87.0, 16.8, 4.0, 3.6),   # much narrower upper-right shoulder
    (85.8, 11.4, 3.4, 2.8),   # tight top-right patch — forms the peak corner
]

MOUNTAIN_PEAK_PATCHES = [
    (70.8, 6.3, 6.6, 4.6),
    (77.8, 7.6, 5.4, 3.8),   # slightly narrowed
    (83.4, 9.0, 3.6, 2.8),   # tight right-shoulder peak
    # far-right wide patch removed — replaced by a descending ridge line below
]

MOUNTAIN_RIDGE_LINES = [
    [(68, 7), (65, 11), (62, 15), (59, 19), (57, 23), (55, 27), (53, 30)],
    [(72, 8), (69, 12), (66, 16), (63, 20), (60, 24), (58, 28), (56, 31)],
    [(76, 9), (73, 13), (70, 17), (67, 21), (64, 25), (62, 29)],
    [(80, 10), (77, 14), (74, 18), (71, 22), (68, 26), (65, 30)],
    [(84, 10), (81, 14), (78, 18), (75, 22), (72, 26), (69, 29)],
    [(87, 11), (84, 15), (81, 19), (78, 23), (75, 27)],
    [(74, 6), (77, 7), (80, 8), (83, 9), (86, 10)],  # top crest left→right
    [(86, 10), (88, 13), (89, 16), (90, 19), (90, 22), (89, 25)],  # right-flank descent
]

MOUNTAIN_VALLEY_AXIS = [
    (67, 12),
    (65, 16),
    (63, 20),
    (61, 24),
    (59, 28),
    (57, 31),
    (55, 33),
]

CAVE_TUNNEL_PATH = [
    (39, 21),
    (40, 19),
    (41, 17),
    (42, 15),
    (43, 13),
    (44, 11),
    (45, 9),
]


def _compute_default_map_origin() -> tuple[int, int]:
    min_col, min_row = 10**9, 10**9
    max_col, max_row = -10**9, -10**9

    def include(col, row):
        nonlocal min_col, min_row, max_col, max_row
        c = int(round(col))
        r = int(round(row))
        min_col = min(min_col, c)
        min_row = min(min_row, r)
        max_col = max(max_col, c)
        max_row = max(max_row, r)

    for rid, (rx, ry) in MAP_ROOM_POS.items():
        if rid not in MAP_ROOM_SIZE or rid in INTERIOR_ONLY_ROOMS:
            continue
        rw, rh = MAP_ROOM_SIZE[rid]
        include(rx, ry)
        include(rx + rw - 1, ry + rh - 1)

    for x, y in (RIVER_PATH_MAIN + RIVER_PATH_LAKE_BRANCH + CAVE_TUNNEL_PATH):
        include(x, y)

    # Bay and open ocean envelope.
    include(-8, 0)
    include(20, 55)

    # Lake envelope.
    include(45, 24)
    include(63, 39)

    for cx, cy, rx, ry in ISLAND_PATCHES:
        include(cx - rx - 3, cy - ry - 3)
        include(cx + rx + 3, cy + ry + 3)

    for cx, cy, rx, ry in MOUNTAIN_HIGHLAND_PATCHES:
        include(cx - rx - 3, cy - ry - 3)
        include(cx + rx + 3, cy + ry + 3)
    for cx, cy, rx, ry in MOUNTAIN_PEAK_PATCHES:
        include(cx - rx - 3, cy - ry - 3)
        include(cx + rx + 3, cy + ry + 3)
    for x, y in MOUNTAIN_VALLEY_AXIS:
        include(x, y)
    for ridge in MOUNTAIN_RIDGE_LINES:
        for x, y in ridge:
            include(x, y)

    if min_col > max_col or min_row > max_row:
        return 0, 0

    center_col = (min_col + max_col) // 2
    center_row = (min_row + max_row) // 2
    return center_col - MAP_WIN_COLS // 2, center_row - MAP_WIN_ROWS // 2


MAP_WIN_COL0, MAP_WIN_ROW0 = _compute_default_map_origin()

MAP_ROOM_BOUNDS = []
MAP_NON_INTERIOR_BOUNDS = []
_interior_entries = []
_overworld_entries = []
for _rid, (_rx, _ry) in MAP_ROOM_POS.items():
    if _rid not in MAP_ROOM_SIZE:
        continue
    _rw, _rh = MAP_ROOM_SIZE[_rid]
    _entry = (_rid, _rx, _ry, _rw, _rh)
    if _rid in INTERIOR_ONLY_ROOMS:
        _interior_entries.append(_entry)
    else:
        _overworld_entries.append(_entry)
        MAP_NON_INTERIOR_BOUNDS.append(_entry)
MAP_ROOM_BOUNDS = _interior_entries + _overworld_entries


def _build_river_samples(path):
    samples = []
    if len(path) < 2:
        return samples
    seg_count = len(path) - 1
    for idx, ((x0, y0), (x1, y1)) in enumerate(zip(path, path[1:])):
        steps = max(abs(x1 - x0), abs(y1 - y0)) * 2
        steps = max(steps, 1)
        width = 2.2 + (idx / max(seg_count - 1, 1)) * 1.0
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


RIVER_SAMPLES = _build_river_samples(RIVER_PATH_MAIN) + _build_river_samples(RIVER_PATH_LAKE_BRANCH)


def _build_path_tiles(path, thickness=1):
    tiles = set()
    if len(path) < 2:
        return tiles
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        steps = max(abs(x1 - x0), abs(y1 - y0)) * 3
        steps = max(steps, 1)
        for s in range(steps + 1):
            t = s / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            for dy in range(-thickness, thickness + 1):
                for dx in range(-thickness, thickness + 1):
                    if dx * dx + dy * dy <= thickness * thickness + 1:
                        tiles.add((x + dx, y + dy))
    return tiles


CAVE_TUNNEL_TILES = _build_path_tiles(CAVE_TUNNEL_PATH, thickness=1)


@lru_cache(maxsize=131072)
def _room_at_cached(wcol, wrow):
    for rid, rx, ry, rw, rh in MAP_ROOM_BOUNDS:
        if rx <= wcol < rx + rw and ry <= wrow < ry + rh:
            return (rid, wcol - rx, wrow - ry)
    return None


@lru_cache(maxsize=131072)
def _overworld_room_at_cached(wcol, wrow):
    for rid, rx, ry, rw, rh in MAP_NON_INTERIOR_BOUNDS:
        if rx <= wcol < rx + rw and ry <= wrow < ry + rh:
            return (rid, wcol - rx, wrow - ry)
    return None


def _room_at(wcol, wrow, rooms, focus_room_id=None):
    if focus_room_id:
        return _room_at_cached(wcol, wrow)
    return _overworld_room_at_cached(wcol, wrow)


@lru_cache(maxsize=131072)
def _in_room_shape(wcol, wrow):
    for rid, rx, ry, rw, rh in MAP_NON_INTERIOR_BOUNDS:
        if rid in TRANSPARENT_ROOMS:
            continue
        if rx <= wcol < rx + rw and ry <= wrow < ry + rh:
            lc = wcol - rx
            lr = wrow - ry
            return _ellipse_zone(lc, lr, rw, rh) != "outside"
    return False


def _ellipse_zone(col, row, rw, rh):
    cx = (rw-1)/2.0; cy = (rh-1)/2.0
    ax = max(cx-0.4, 1.0); ay = max(cy-0.4, 1.0)
    d  = ((col-cx)/ax)**2 + ((row-cy)/ay)**2
    if   d > 1.2:  return "outside"
    elif d > 0.70: return "border"
    else:          return "inside"


@lru_cache(maxsize=131072)
def _is_cave_tunnel_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    return (wcol, wrow) in CAVE_TUNNEL_TILES


@lru_cache(maxsize=131072)
def _obstacle_at(wcol, wrow):
    if _is_cave_tunnel_tile(wcol, wrow):
        return "tunnel", "cave_entrance"
    if _is_island_tile(wcol, wrow):
        return "island", "mountain_pass"
    if _is_jagged_rock_tile(wcol, wrow):
        return "reef", "mountain_pass"
    if _is_river_tile(wcol, wrow):
        return "river", "riverbank"
    if _is_lake_tile(wcol, wrow):
        return "lake", "river_lake"
    if _is_island_shoal_tile(wcol, wrow):
        return "shoal", "mountain_pass"
    if _is_bay_tile(wcol, wrow):
        return "bay", "mountain_pass"
    for rid, (otype, r0, r1, c0, c1) in OBSTACLE_ZONES.items():
        if r0 <= wrow <= r1 and c0 <= wcol <= c1:
            return otype, rid
    return None, None


@lru_cache(maxsize=131072)
def _in_free_corridor(wcol, wrow):
    for r0, r1, c0, c1 in FREE_CORRIDORS:
        if r0 <= wrow <= r1 and c0 <= wcol <= c1:
            return True
    return False


@lru_cache(maxsize=131072)
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


@lru_cache(maxsize=131072)
def _is_river_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    sample, d2 = _nearest_river_sample(wcol, wrow)
    if sample is None:
        return False
    width = sample[2]
    return d2 <= width * width


@lru_cache(maxsize=131072)
def _is_lake_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    cx1, cy1 = 54.2, 31.6
    rx1, ry1 = 9.8, 6.6
    d1 = ((wcol - cx1) / rx1) ** 2 + ((wrow - cy1) / ry1) ** 2
    cx2, cy2 = 60.0, 30.2
    rx2, ry2 = 5.8, 4.4
    d2 = ((wcol - cx2) / rx2) ** 2 + ((wrow - cy2) / ry2) ** 2
    cx3, cy3 = 49.8, 33.8
    rx3, ry3 = 5.2, 3.8
    d3 = ((wcol - cx3) / rx3) ** 2 + ((wrow - cy3) / ry3) ** 2
    return d1 <= 1.0 or d2 <= 1.0 or d3 <= 1.0


@lru_cache(maxsize=131072)
def _west_ocean_limit(wrow):
    # Irregular coastline so the ocean edge reads naturally instead of a hard box.
    band = abs(wrow - 27)
    coast = 11 - min(6, band // 5)  # wider around mid-latitudes, narrower near top/bottom
    if (wrow * 7 + 3) % 11 in (0, 1):
        coast += 1
    if (wrow * 5 + 9) % 13 == 0:
        coast -= 1
    return coast


@lru_cache(maxsize=131072)
def _is_bay_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    if _is_lake_tile(wcol, wrow):
        return False
    # Open ocean to the west with an organic coastline.
    if -16 <= wrow <= 86 and wcol <= _west_ocean_limit(wrow):
        return True
    # Main bay body near the lighthouse cliffs.
    cx1, cy1 = 5.0, 22.0
    rx1, ry1 = 13.0, 15.0
    d1 = ((wcol - cx1) / rx1) ** 2 + ((wrow - cy1) / ry1) ** 2
    # Mid cove that wraps around the base of the lighthouse rock.
    cx2, cy2 = 2.0, 15.0
    rx2, ry2 = 9.0, 9.0
    d2 = ((wcol - cx2) / rx2) ** 2 + ((wrow - cy2) / ry2) ** 2
    # Upper water lobe so the tower feels surrounded at higher elevation.
    cx3, cy3 = 3.0, 8.0
    rx3, ry3 = 8.5, 6.4
    d3 = ((wcol - cx3) / rx3) ** 2 + ((wrow - cy3) / ry3) ** 2
    return (
        (d1 <= 1.0 and wcol <= 20)
        or (d2 <= 1.0 and wcol <= 18)
        or (d3 <= 1.0 and wcol <= 16)
    )


@lru_cache(maxsize=131072)
def _is_island_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    if not _is_bay_tile(wcol, wrow):
        return False
    for cx, cy, rx, ry in ISLAND_PATCHES:
        d = ((wcol - cx) / rx) ** 2 + ((wrow - cy) / ry) ** 2
        if d <= 1.0:
            return True
    return False


@lru_cache(maxsize=131072)
def _is_island_shoal_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    if _is_island_tile(wcol, wrow):
        return False
    if not _is_bay_tile(wcol, wrow):
        return False
    for cx, cy, rx, ry in ISLAND_PATCHES:
        d = ((wcol - cx) / (rx + 2.6)) ** 2 + ((wrow - cy) / (ry + 2.2)) ** 2
        if d <= 1.0:
            return True
    return False


@lru_cache(maxsize=131072)
def _is_jagged_rock_tile(wcol, wrow):
    if not _is_bay_tile(wcol, wrow):
        return False
    if _is_island_shoal_tile(wcol, wrow):
        return False
    # Jagged reefs around islands.
    near_island = False
    for cx, cy, rx, ry in ISLAND_PATCHES:
        d = ((wcol - cx) / (rx + 3.8)) ** 2 + ((wrow - cy) / (ry + 3.2)) ** 2
        if d <= 1.0:
            near_island = True
            break
    if near_island and (wcol * 7 + wrow * 5) % 4 in (0, 1):
        return True
    # Outer west-ocean knife rocks near the irregular coastline.
    coast = _west_ocean_limit(wrow)
    if wcol <= coast - 1 and -8 <= wrow <= 64:
        return (wcol * 3 + wrow * 11) % 7 in (0, 1)
    # Rock band where bay meets cliff shelves.
    if 8 <= wcol <= 20 and 8 <= wrow <= 40:
        return (wcol * 5 + wrow * 7) % 6 in (0, 1)
    return False


@lru_cache(maxsize=131072)
def _bay_depth_factor(wcol, wrow):
    # 0.0 shallow near coast, 1.0 deep in west ocean.
    coast = _west_ocean_limit(wrow)
    return max(0.0, min(1.0, (coast - wcol) / 18.0))


def _dist2_to_path(wcol, wrow, path):
    if len(path) < 2:
        return 10**9
    best = 10**9
    px = float(wcol)
    py = float(wrow)
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        vx = float(x1 - x0)
        vy = float(y1 - y0)
        wx = px - float(x0)
        wy = py - float(y0)
        vv = vx * vx + vy * vy
        if vv <= 1e-9:
            dx = px - float(x0)
            dy = py - float(y0)
            d2 = dx * dx + dy * dy
        else:
            t = (wx * vx + wy * vy) / vv
            t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            qx = float(x0) + vx * t
            qy = float(y0) + vy * t
            dx = px - qx
            dy = py - qy
            d2 = dx * dx + dy * dy
        if d2 < best:
            best = d2
    return best


@lru_cache(maxsize=131072)
def _is_highland_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    if _is_water_tile(wcol, wrow):
        return False
    if wcol < 50:
        return False
    for cx, cy, rx, ry in MOUNTAIN_HIGHLAND_PATCHES:
        d = ((wcol - cx) / rx) ** 2 + ((wrow - cy) / ry) ** 2
        if d <= 1.0:
            return True
    return False


@lru_cache(maxsize=131072)
def _is_peak_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    if _is_water_tile(wcol, wrow):
        return False
    if wcol < 60:
        return False
    for cx, cy, rx, ry in MOUNTAIN_PEAK_PATCHES:
        d = ((wcol - cx) / rx) ** 2 + ((wrow - cy) / ry) ** 2
        if d <= 1.0:
            return True
    return False


@lru_cache(maxsize=131072)
def _is_valley_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    if _is_water_tile(wcol, wrow):
        return False
    if wcol < 50:
        return False
    d2 = _dist2_to_path(wcol, wrow, MOUNTAIN_VALLEY_AXIS)
    return d2 <= 2.8 * 2.8


@lru_cache(maxsize=131072)
def _is_ridge_tile(wcol, wrow):
    if not _is_highland_tile(wcol, wrow):
        return False
    if _is_valley_tile(wcol, wrow):
        return False
    if _is_peak_tile(wcol, wrow):
        return False
    for ridge in MOUNTAIN_RIDGE_LINES:
        if _dist2_to_path(wcol, wrow, ridge) <= 1.5 * 1.5:
            return True
    return False


@lru_cache(maxsize=131072)
def _is_water_tile(wcol, wrow):
    if _is_island_tile(wcol, wrow):
        return False
    return _is_bay_tile(wcol, wrow) or _is_river_tile(wcol, wrow) or _is_lake_tile(wcol, wrow)


@lru_cache(maxsize=131072)
def _is_freshwater_bank_tile(wcol, wrow):
    if _in_room_shape(wcol, wrow):
        return False
    if _is_water_tile(wcol, wrow):
        return False
    if _is_bay_tile(wcol, wrow):
        return False
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            if _is_river_tile(wcol + dx, wrow + dy) or _is_lake_tile(wcol + dx, wrow + dy):
                return True
    return False


@lru_cache(maxsize=131072)
def _is_coast_cliff_tile(wcol, wrow):
    if _is_water_tile(wcol, wrow):
        return False
    room_info = _room_at_cached(wcol, wrow)
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


@lru_cache(maxsize=131072)
def _zone_char(otype, wcol, wrow):
    seed = (wcol * 5 + wrow * 11) % 16
    if otype == "tunnel":
        chars = "/=\\::"
        c = chars[seed % len(chars)]
        v = 96 + (seed % 5) * 6
        return c, (v, v, v + 8)
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
    if otype == "lake":
        ripple = (wcol * 13 + wrow * 7) % 23
        chars = "~=-.`~,=~"
        c = "." if ripple in (0, 11, 19) else chars[seed % len(chars)]
        col = (
            22 + (seed % 3),
            96 + (seed % 5) * 6,
            154 + (seed % 6) * 6,
        )
        return c, col
    if otype == "shoal":
        chars = "~-~~-~"
        c = chars[seed % len(chars)]
        col = (48, 150 + (seed % 4) * 5, 186 + (seed % 5) * 4)
        return c, col
    if otype == "bay":
        depth = _bay_depth_factor(wcol, wrow)
        if depth < 0.28:
            chars = "~.,-=~"
        elif depth < 0.62:
            chars = "~~-=.`~"
        else:
            chars = "=~~-`.,~"
        c = chars[seed % len(chars)]
        if (wcol * 9 + wrow * 5) % 31 == 0:
            c = "'"
        if depth >= 0.72:
            # Deep water pocket: visually distinct navy area.
            c = "~" if seed % 3 else "="
            col = (
                6 + (seed % 2),
                26 + (seed % 3) * 3,
                106 + (seed % 4) * 4,
            )
        else:
            blue = int(116 + depth * 102)
            green = int(66 + (1.0 - depth) * 36)
            col = (
                8 + (seed % 2),
                green + (seed % 4) * 3,
                blue + (seed % 5) * 3,
            )
        return c, col
    if otype == "reef":
        chars = "xX^/\\|#n"
        c = chars[seed % len(chars)]
        col = (
            122 + (seed % 5) * 4,
            124 + (seed % 5) * 3,
            134 + (seed % 4) * 4,
        )
        return c, col
    if otype == "island":
        bush = ((wcol * 3 + wrow * 5) % 9) == 0
        if bush:
            chars = "\"'"
            c = chars[seed % len(chars)]
            col = (118 + (seed % 4) * 6, 168 + (seed % 4) * 7, 86 + (seed % 3) * 4)
            return c, col
        chars = "._-."
        c = chars[seed % len(chars)]
        col = (206 + (seed % 4) * 6, 178 + (seed % 4) * 5, 96 + (seed % 3) * 3)
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


@lru_cache(maxsize=131072)
def _dist_to_nearest_room(wcol, wrow):
    best = 999
    for _, rx, ry, rw, rh in MAP_NON_INTERIOR_BOUNDS:
        dc = max(0, rx - wcol, wcol - (rx + rw - 1))
        dr = max(0, ry - wrow, wrow - (ry + rh - 1))
        best = min(best, dc + dr)
    return best





def draw_map_overlay(
    screen,
    font_title,
    font_body,
    state,
    last_cmd="",
    show_title=True,
    show_legend=True,
    focus_room_id=None,
):
    avail_w = WIDTH - (PADDING * 2)
    avail_h = HEIGHT - MAP_INPUT_HEIGHT - 32
    # Fill the available map panel while preserving the world orientation.
    base_cols = MAP_WIN_COLS
    base_rows = MAP_WIN_ROWS
    CELL = max(6, min(9, avail_w // max(base_cols, 1)))
    win_cols = max(80, avail_w // CELL)
    win_rows = max(56, avail_h // CELL)
    try:
        mf = pygame.font.SysFont("Courier New", CELL+1)
    except Exception:
        mf = pygame.font.SysFont(None, CELL+2)

    map_col0 = MAP_WIN_COL0 - (win_cols - base_cols) // 2
    map_row0 = MAP_WIN_ROW0 - (win_rows - base_rows) // 2
    if focus_room_id and focus_room_id in MAP_ROOM_POS and focus_room_id in MAP_ROOM_SIZE:
        rx, ry = MAP_ROOM_POS[focus_room_id]
        rw, rh = MAP_ROOM_SIZE[focus_room_id]
        map_col0 = rx + rw // 2 - win_cols // 2
        map_row0 = ry + rh // 2 - win_rows // 2

    # Map pixel origin: centre the map window on screen
    map_px_w = win_cols * CELL
    map_px_h = win_rows * CELL
    opx = (WIDTH  - map_px_w) // 2
    opy = (HEIGHT - MAP_INPUT_HEIGHT - map_px_h) // 2 + 18

    # Title
    if show_title:
        ts = font_title.render("MAP", True, (140, 170, 110))
        screen.blit(ts, ts.get_rect(center=(WIDTH//2, opy-22)))

    visited = state.player.visited_tiles
    cur_rid  = state.current_room_id
    explored = state.player.explored_rooms
    discovered = state.player.discovered_rooms
    has_raft = state.player.inventory.get("raft", 0) > 0
    has_lantern = state.player.inventory.get("lantern", 0) > 0
    panoramic_unlocked = any(r in explored or r in discovered for r in ("mountain_pass", "lighthouse_interior", "lighthouse_top"))
    panoramic_view = (not focus_room_id) and (cur_rid in {"mountain_pass", "lighthouse_interior", "lighthouse_top"} or panoramic_unlocked)
    bay_unlocked = panoramic_view or ("mountain_pass" in discovered) or (has_raft and cur_rid in {"river_run", "river_lake", "far_shore"}) or cur_rid == "open_waters"
    mountain_unlocked = panoramic_view or any(
        rid in discovered or rid in explored
        for rid in ("mountain_pass", "lighthouse_interior", "lighthouse_top")
    )
    rooms    = state.rooms
    flicker = (pygame.time.get_ticks() // 170) % 4

    plx = None
    ply = None
    if cur_rid in MAP_ROOM_POS and cur_rid in MAP_ROOM_SIZE:
        cur_room = rooms.get(cur_rid)
        cur_rw, cur_rh = MAP_ROOM_SIZE[cur_rid]
        if cur_room and cur_room.is_walkable:
            plx = MAP_ROOM_POS[cur_rid][0] + state.local_x
            ply = MAP_ROOM_POS[cur_rid][1] + state.local_y
        else:
            plx = MAP_ROOM_POS[cur_rid][0] + cur_rw // 2
            ply = MAP_ROOM_POS[cur_rid][1] + cur_rh // 2

    # Colour palette
    C = {
        "room_floor_cur":  (62, 55, 42),
        "room_floor_exp":  (30, 27, 20),
        "room_floor_fog":  (16, 16, 12),
        "cabin_floor_cur": (92, 74, 52),
        "cabin_floor_exp": (58, 44, 30),
        "cabin_floor_fog": (30, 24, 16),
        "cliff_floor_cur": (104, 104, 106),
        "cliff_floor_exp": (72, 72, 76),
        "cliff_floor_fog": (38, 38, 42),
        "tower_floor_cur": (86, 94, 104),
        "tower_floor_exp": (56, 64, 72),
        "tower_floor_fog": (32, 36, 42),
        "cave_floor_cur":  (8, 8, 10),
        "cave_floor_exp":  (6, 6, 8),
        "cave_floor_fog":  (3, 3, 4),
        "lake_floor_cur":  (20, 104, 164),
        "lake_floor_exp":  (16, 84, 138),
        "lake_floor_fog":  (8, 34, 56),
        "tree_cur":        (80,130, 60),
        "tree_exp":        (48, 80, 42),
        "tree_fog":        (26, 38, 20),
        "cabin_edge_cur":  (176, 146, 112),
        "cabin_edge_exp":  (126, 102, 76),
        "cabin_edge_fog":  (62, 48, 34),
        "cliff_edge_cur":  (150, 150, 155),
        "cliff_edge_exp":  (108, 108, 114),
        "cliff_edge_fog":  (58, 58, 62),
        "tower_edge_cur":  (176, 182, 192),
        "tower_edge_exp":  (126, 134, 146),
        "tower_edge_fog":  (66, 72, 80),
        "cave_edge_cur":   (18, 18, 22),
        "cave_edge_exp":   (12, 12, 16),
        "cave_edge_fog":   (7, 7, 9),
        "lake_edge_cur":   (94, 176, 208),
        "lake_edge_exp":   (72, 132, 160),
        "lake_edge_fog":   (28, 56, 74),
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
        "cave_forest_near": (72, 74, 78),
        "cave_forest_mid":  (58, 60, 64),
        "cave_forest_far":  (46, 48, 52),
        "cave_forest_dense": (34, 36, 40),
        "obs_path":        (45, 40, 28),
        "lantern_glow_hot":  (246, 224, 132),
        "lantern_glow_warm": (228, 176, 88),
        "lantern_glow_dim":  (176, 122, 62),
        "raft_glow_hot":   (250, 178, 94),
        "raft_glow_warm":  (236, 152, 78),
        "raft_glow_dim":   (194, 122, 64),
        "highland_green":  (66, 108, 64),
        "highland_dark":   (48, 84, 48),
        "ridge_stone":     (126, 134, 128),
        "peak_snow":       (194, 202, 204),
        "peak_rock":       (156, 166, 170),
        "valley_grass":    (90, 142, 84),
        "valley_shadow":   (64, 106, 60),
    }

    TREE_CHARS = ["*","'","*",",","*","'","*"]

    focus_bg_col = (14, 22, 18)
    if focus_room_id in {"lighthouse_interior", "lighthouse_top", "mountain_pass"}:
        focus_bg_col = (10, 16, 24)
    elif focus_room_id == "cabin_interior":
        focus_bg_col = (24, 18, 12)
    elif focus_room_id == "river_lake":
        focus_bg_col = (12, 30, 42)
    elif focus_room_id in {"cave_entrance", "cave_chamber"}:
        focus_bg_col = (9, 10, 14)
    elif focus_room_id == "shed_interior":
        focus_bg_col = (22, 18, 10)

    def tchar(lc, lr, rw, rh):
        if (lc in (0,rw-1)) and (lr in (0,rh-1)):
            return chr(9670)  # ♦
        return TREE_CHARS[(lc + lr*3) % len(TREE_CHARS)]

    def put(wcol, wrow, ch, color):
        px = opx + (wcol - map_col0)*CELL
        py = opy + (wrow - map_row0)*CELL
        if 0 <= px < WIDTH and 0 <= py < HEIGHT - MAP_INPUT_HEIGHT:
            key = (CELL, ch, color)
            surf = MAP_GLYPH_CACHE.get(key)
            if surf is None:
                surf = mf.render(ch, True, color)
                MAP_GLYPH_CACHE[key] = surf
            screen.blit(surf, (px, py))

    def in_cave_gray_biome(wcol, wrow):
        # Keep grey tone tightly scoped to the cave tunnel path itself.
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (wcol + dx, wrow + dy) in CAVE_TUNNEL_TILES:
                    return True
        return False

    # Fill the map panel background to avoid empty black gutters.
    pygame.draw.rect(screen, (9, 14, 10), (opx, opy, map_px_w, map_px_h))

    focus_bounds = None
    if focus_room_id and focus_room_id in MAP_ROOM_POS and focus_room_id in MAP_ROOM_SIZE:
        _frx, _fry = MAP_ROOM_POS[focus_room_id]
        _frw, _frh = MAP_ROOM_SIZE[focus_room_id]
        focus_bounds = (_frx, _fry, _frx + _frw, _fry + _frh)

    for wrow in range(map_row0, map_row0 + win_rows):
        for wcol in range(map_col0, map_col0 + win_cols):
            tile_visited = panoramic_view or ((wcol, wrow) in visited)
            if not tile_visited and focus_bounds is not None:
                fx0, fy0, fx1, fy1 = focus_bounds
                if fx0 <= wcol < fx1 and fy0 <= wrow < fy1:
                    tile_visited = True

            if not focus_room_id:
                # Faint terrain noise so the map window never looks like a hard black void.
                if not tile_visited:
                    bg_seed = (wcol * 11 + wrow * 7) % 19
                    if bg_seed == 0:
                        put(wcol, wrow, ".", (10, 15, 11))
                    elif bg_seed == 1:
                        put(wcol, wrow, "'", (12, 18, 13))

            room_info = _room_at(wcol, wrow, rooms, focus_room_id)
            transparent_room_info = None
            if room_info and room_info[0] in TRANSPARENT_ROOMS:
                transparent_room_info = room_info
                room_info = None
            if room_info:
                rid, lc, lr = room_info
                if focus_room_id and rid != focus_room_id:
                    continue
                rw, rh = MAP_ROOM_SIZE.get(rid, (1,1))
                zone = _ellipse_zone(lc, lr, rw, rh)

                if zone == "outside":
                    pass  # part of bounding box but outside circle: treat as forest
                else:
                    is_cur  = (rid == cur_rid)
                    actual_exp = rid in explored
                    is_exp  = actual_exp or panoramic_view
                    is_disc = (rid in discovered) or panoramic_view
                    is_lake_room = (rid == "river_lake")
                    is_cabin_room = (rid == "cabin_interior")
                    is_cliff_room = (rid == "mountain_pass")
                    is_tower_room = rid in ("lighthouse_interior", "lighthouse_top")
                    is_cave_room = rid in ("cave_entrance", "cave_chamber")

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
                            if is_lake_room:
                                tc = C["lake_edge_cur"] if is_cur else (C["lake_edge_exp"] if is_exp else C["lake_edge_fog"])
                                put(wcol, wrow, "~" if (lc + lr) % 2 else "-", tc)
                            elif is_cabin_room:
                                tc = C["cabin_edge_cur"] if is_cur else (C["cabin_edge_exp"] if is_exp else C["cabin_edge_fog"])
                                put(wcol, wrow, "+" if (lc + lr) % 2 else "|", tc)
                            elif is_cliff_room:
                                tc = C["cliff_edge_cur"] if is_cur else (C["cliff_edge_exp"] if is_exp else C["cliff_edge_fog"])
                                edge_ch = "^" if _is_coast_cliff_tile(wcol, wrow) and (lc + lr) % 2 else (":" if (lc + lr) % 2 else ".")
                                put(wcol, wrow, edge_ch, tc)
                            elif is_tower_room:
                                tc = C["tower_edge_cur"] if is_cur else (C["tower_edge_exp"] if is_exp else C["tower_edge_fog"])
                                put(wcol, wrow, "#" if (lc + lr) % 2 else "|", tc)
                            elif is_cave_room:
                                tc = C["cave_edge_cur"] if is_cur else (C["cave_edge_exp"] if is_exp else C["cave_edge_fog"])
                                put(wcol, wrow, "#" if (lc + lr) % 2 else ":", tc)
                            else:
                                tc = C["tree_cur"] if is_cur else (C["tree_exp"] if is_exp else C["tree_fog"])
                                put(wcol, wrow, tchar(lc,lr,rw,rh), tc)
                        elif is_disc:
                            if is_lake_room:
                                put(wcol, wrow, ".", C["lake_edge_fog"])
                            elif is_cabin_room:
                                put(wcol, wrow, ".", C["cabin_edge_fog"])
                            elif is_cliff_room:
                                put(wcol, wrow, ".", C["cliff_edge_fog"])
                            elif is_tower_room:
                                put(wcol, wrow, ".", C["tower_edge_fog"])
                            elif is_cave_room:
                                put(wcol, wrow, ".", C["cave_edge_fog"])
                            else:
                                put(wcol, wrow, ".", C["tree_fog"])

                    else:  # inside
                        if is_cur and tile_visited:
                            if is_lake_room:
                                ch = "~" if (lc + lr) % 3 else "="
                                put(wcol, wrow, ch, C["lake_floor_cur"])
                            elif is_cabin_room:
                                ch = "'" if (lc + lr) % 4 == 0 else "."
                                put(wcol, wrow, ch, C["cabin_floor_cur"])
                            elif is_cliff_room:
                                ch = ":" if (lc + lr) % 4 == 0 else "."
                                put(wcol, wrow, ch, C["cliff_floor_cur"])
                            elif is_tower_room:
                                ch = ":" if (lc + lr) % 4 == 0 else "."
                                put(wcol, wrow, ch, C["tower_floor_cur"])
                            elif is_cave_room:
                                ch = "." if (lc + lr) % 4 == 0 else " "
                                put(wcol, wrow, ch, C["cave_floor_cur"])
                            else:
                                ch = "," if (lc+lr)%4==0 else "."
                                put(wcol, wrow, ch, C["room_floor_cur"])
                        elif is_exp and tile_visited:
                            if is_lake_room:
                                ch = "~" if (lc + lr) % 4 else "-"
                                put(wcol, wrow, ch, C["lake_floor_exp"])
                            elif is_cabin_room:
                                ch = "'" if (lc + lr) % 5 == 0 else "."
                                put(wcol, wrow, ch, C["cabin_floor_exp"])
                            elif is_cliff_room:
                                ch = ":" if (lc + lr) % 5 == 0 else "."
                                put(wcol, wrow, ch, C["cliff_floor_exp"])
                            elif is_tower_room:
                                ch = ":" if (lc + lr) % 5 == 0 else "."
                                put(wcol, wrow, ch, C["tower_floor_exp"])
                            elif is_cave_room:
                                ch = "." if (lc + lr) % 5 == 0 else " "
                                put(wcol, wrow, ch, C["cave_floor_exp"])
                            else:
                                ch = "," if (lc+lr)%5==0 else "."
                                put(wcol, wrow, ch, C["room_floor_exp"])
                        elif is_disc:
                            # Fog: faint silhouette
                            if (lc+lr)%6 == 0:
                                if is_lake_room:
                                    put(wcol, wrow, ".", C["lake_floor_fog"])
                                elif is_cabin_room:
                                    put(wcol, wrow, ".", C["cabin_floor_fog"])
                                elif is_cliff_room:
                                    put(wcol, wrow, ":", C["cliff_floor_fog"])
                                elif is_tower_room:
                                    put(wcol, wrow, ".", C["tower_floor_fog"])
                                elif is_cave_room:
                                    put(wcol, wrow, ".", C["cave_floor_fog"])
                                else:
                                    put(wcol, wrow, ",", C["room_floor_fog"])

                    # Cave lantern halo: warm ASCII light around the player only.
                    if is_cave_room and is_cur and tile_visited and has_lantern and plx is not None and ply is not None:
                        dist = max(abs(wcol - plx), abs(wrow - ply))
                        phase = (flicker + wcol + wrow) % 4
                        if dist == 1:
                            glow_ch = "*" if phase % 2 == 0 else "+"
                            put(wcol, wrow, glow_ch, C["lantern_glow_hot"])
                        elif dist == 2:
                            glow_ch = ":" if phase in (0, 2) else "."
                            put(wcol, wrow, glow_ch, C["lantern_glow_warm"])
                        elif dist == 3 and phase == 0:
                            put(wcol, wrow, "'", C["lantern_glow_dim"])

                    # Raft marker: stable orange/white square around player on water routes.
                    water_nav_room = rid in {"river_run", "river_lake", "far_shore", "open_waters"}
                    if water_nav_room and is_cur and tile_visited and has_raft and plx is not None and ply is not None:
                        dx = wcol - plx
                        dy = wrow - ply
                        if max(abs(dx), abs(dy)) == 1 and (abs(dx) == 1 or abs(dy) == 1):
                            corner = abs(dx) == 1 and abs(dy) == 1
                            ch = "#" if corner else "O"
                            col = (246, 244, 236) if corner else C["raft_glow_hot"]
                            put(wcol, wrow, ch, col)

                    # Shore cliffs blend into the lighthouse room edge only where water touches.
                    if is_cliff_room and (tile_visited or is_exp) and _is_coast_cliff_tile(wcol, wrow):
                        shore_col = C["coast_cliff"] if tile_visited else C["cliff_edge_exp"]
                        put(wcol, wrow, "^" if (wcol + wrow) % 2 else "|", shore_col)

                    # Features (explored only, inside only)
                    if actual_exp and zone == "inside":
                        room = rooms.get(rid)
                        if room:
                            for feat in room.features:
                                feat_id = feat.get("id", "")
                                fx, fy = feat.get("pos",(-1,-1))
                                sprite = FEATURE_SPRITES.get(feat_id)
                                if sprite:
                                    for dx, dy, ch, col in sprite:
                                        if ch and fx + dx == lc and fy + dy == lr and tile_visited:
                                            put(wcol, wrow, ch, col)
                                elif fx == lc and fy == lr:
                                    if tile_visited:
                                        fcol = FEATURE_COLORS.get(feat_id, C["feature"])
                                        put(wcol, wrow, feat.get("label","?"), fcol)

                    # Visible loot items (explored only, inside only)
                    if actual_exp and zone == "inside":
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

            if focus_room_id:
                if (wcol * 7 + wrow * 11) % 13 == 0:
                    put(wcol, wrow, ".", focus_bg_col)
                continue

            if has_raft and ((wcol, wrow) in RAFT_CROSSING_TILES or (wcol, wrow) in RAFT_ROUTE_TILES):
                crossing_known = any(r in discovered for r in ("riverbank", "far_shore", "river_lake"))
                if tile_visited or crossing_known:
                    put(wcol, wrow, ".", C["obs_path"])
                continue

            obs, trigger_rid = _obstacle_at(wcol, wrow)
            if obs:
                if obs in {"bay", "reef", "island", "shoal"} and not bay_unlocked:
                    continue
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

            coast_known = "mountain_pass" in discovered
            if (tile_visited or coast_known) and _is_coast_cliff_tile(wcol, wrow):
                c = "^" if (wcol + wrow) % 2 else "|"
                put(wcol, wrow, c, C["coast_cliff"])
                continue

            if (tile_visited or mountain_unlocked) and _is_peak_tile(wcol, wrow):
                seed = (wcol * 13 + wrow * 11) % 13
                if seed in (0, 5, 9):
                    ch = "A"
                    col = C["peak_snow"]
                elif seed in (2, 6):
                    ch = "/"
                    col = C["peak_rock"]
                elif seed in (3, 7):
                    ch = "\\"
                    col = C["ridge_stone"]
                elif seed in (10, 12):
                    ch = "_"
                    col = C["peak_rock"]
                else:
                    ch = "^"
                    col = C["peak_snow"] if seed % 2 else C["peak_rock"]
                put(wcol, wrow, ch, col)
                continue

            if (tile_visited or mountain_unlocked) and _is_valley_tile(wcol, wrow):
                seed = (wcol * 7 + wrow * 5) % 8
                chars = ".,'`..,,"
                ch = chars[seed % len(chars)]
                col = C["valley_grass"] if seed not in (2, 6) else C["valley_shadow"]
                put(wcol, wrow, ch, col)
                continue

            if (tile_visited or mountain_unlocked) and _is_ridge_tile(wcol, wrow):
                seed = (wcol * 9 + wrow * 7) % 12
                if seed in (0, 4):
                    ch = "/"
                    col = C["ridge_stone"]
                elif seed in (1, 5):
                    ch = "\\"
                    col = C["ridge_stone"]
                elif seed in (2, 8):
                    ch = "^"
                    col = C["peak_rock"]
                elif seed in (3, 9):
                    ch = "_"
                    col = C["highland_dark"]
                else:
                    ch = "|" if seed in (6, 10) else "^"
                    col = C["ridge_stone"] if (wcol + wrow) % 2 else C["highland_dark"]
                put(wcol, wrow, ch, col)
                continue

            if (tile_visited or mountain_unlocked) and _is_highland_tile(wcol, wrow):
                seed = (wcol * 5 + wrow * 3) % 10
                if seed in (0, 4, 7):
                    ch = ":"
                elif seed in (1, 6):
                    ch = "."
                elif seed in (2, 8):
                    ch = ","
                else:
                    ch = "`"
                col = C["highland_dark"] if seed in (5, 8, 9) else C["highland_green"]
                put(wcol, wrow, ch, col)
                continue

            if tile_visited and _is_freshwater_bank_tile(wcol, wrow):
                seed = (wcol * 9 + wrow * 7) % 8
                bank_chars = ["!", "|", "^", "|", "!", "^", "|", "!"]
                put(wcol, wrow, bank_chars[seed], C["forest_dense"])
                continue

            if not tile_visited:
                continue
            dist = _dist_to_nearest_room(wcol, wrow)
            seed = (wcol*7 + wrow*13) % 8
            is_cave_gray = in_cave_gray_biome(wcol, wrow)
            if dist == 1:
                if seed < 6:
                    ch = FOREST_CHARS_NEAR[seed % len(FOREST_CHARS_NEAR)]
                    put(wcol, wrow, ch, C["cave_forest_near"] if is_cave_gray else C["forest_near"])
            elif dist <= 3:
                ch = FOREST_CHARS_MID[seed % len(FOREST_CHARS_MID)]
                put(wcol, wrow, ch, C["cave_forest_mid"] if is_cave_gray else C["forest_mid"])
            elif dist <= 6:
                ch = FOREST_CHARS_FAR[seed % len(FOREST_CHARS_FAR)]
                put(wcol, wrow, ch, C["cave_forest_far"] if is_cave_gray else C["forest_far"])
            else:
                ch = FOREST_CHARS_DENSE[seed % len(FOREST_CHARS_DENSE)]
                put(wcol, wrow, ch, C["cave_forest_dense"] if is_cave_gray else C["forest_dense"])

            if transparent_room_info:
                trid, tlc, tlr = transparent_room_info
                trw, trh = MAP_ROOM_SIZE.get(trid, (1, 1))
                tzone = _ellipse_zone(tlc, tlr, trw, trh)
                if tzone != "outside":
                    t_is_cur = (trid == cur_rid)
                    t_actual_exp = trid in explored
                    if t_actual_exp and tzone == "inside":
                        room = rooms.get(trid)
                        if room:
                            for feat in room.features:
                                feat_id = feat.get("id", "")
                                fx, fy = feat.get("pos", (-1, -1))
                                if fx == tlc and fy == tlr and tile_visited:
                                    fcol = FEATURE_COLORS.get(feat_id, C["feature"])
                                    put(wcol, wrow, feat.get("label", "?"), fcol)
                            visible = room.visible_loot()
                            if visible:
                                item_list = list(visible.keys())
                                half = len(item_list) // 2
                                item_row = trh // 2 + 2
                                for ii, item_name in enumerate(item_list):
                                    ix = trw // 2 + ii - half
                                    if tlc == ix and tlr == item_row and tile_visited:
                                        item_info = state.game_data.get("items", {}).get(item_name, {})
                                        itype = item_info.get("type", "")
                                        icol = ITEM_MAP_COLORS.get(itype, (200, 180, 80))
                                        put(wcol, wrow, item_name[0].upper(), icol)
                    if t_is_cur and wcol == plx and wrow == ply:
                        put(wcol, wrow, "@", C["player"])

    if cur_rid in TRANSPARENT_ROOMS and cur_rid in MAP_ROOM_POS and cur_rid in MAP_ROOM_SIZE and not focus_room_id:
        trid = cur_rid
        trx, try_row = MAP_ROOM_POS[trid]
        trw, trh = MAP_ROOM_SIZE[trid]
        t_room = rooms.get(trid)
        if t_room:
            for feat in t_room.features:
                fx, fy = feat.get("pos", (-1, -1))
                wcol = trx + fx
                wrow = try_row + fy
                if panoramic_view or (wcol, wrow) in visited:
                    fcol = FEATURE_COLORS.get(feat.get("id", ""), C["feature"])
                    put(wcol, wrow, feat.get("label", "?"), fcol)
            visible = t_room.visible_loot()
            if visible:
                item_list = list(visible.keys())
                half = len(item_list) // 2
                item_row = trh // 2 + 2
                for ii, item_name in enumerate(item_list):
                    ix = trw // 2 + ii - half
                    wcol = trx + ix
                    wrow = try_row + item_row
                    if panoramic_view or (wcol, wrow) in visited:
                        item_info = state.game_data.get("items", {}).get(item_name, {})
                        itype = item_info.get("type", "")
                        icol = ITEM_MAP_COLORS.get(itype, (200, 180, 80))
                        put(wcol, wrow, item_name[0].upper(), icol)
        if plx is not None and ply is not None:
            put(plx, ply, "@", C["player"])

    if has_raft and not focus_room_id and bay_unlocked:
        ax, ay = RAFT_OCEAN_SPRITE_ANCHOR
        for dx, dy, ch, col in RAFT_OCEAN_SPRITE:
            tx = ax + dx
            ty = ay + dy
            if _is_bay_tile(tx, ty) and not _is_island_tile(tx, ty):
                put(tx, ty, ch, col)
        if cur_rid == "open_waters" and plx is not None and ply is not None:
            for dx, dy, ch, col in RAFT_OCEAN_SPRITE:
                tx = plx + dx
                ty = ply + dy
                if tx == plx and ty == ply:
                    continue
                put(tx, ty, ch, col)

    if show_legend:
        lf = pygame.font.SysFont(None, 20)
        leg = "@ you   ? undiscovered   . path   ~~~ water   ### bramble   ^^^ cliff   |!| deep woods   raft for deep navy water"
        ls = lf.render(leg, True, (55, 75, 45))
        screen.blit(ls, ls.get_rect(center=(WIDTH//2, HEIGHT-MAP_INPUT_HEIGHT-8)))


def draw_map_screen(screen, font_mt, font_mb, font_in, state, input_text, cursor_idx, cursor_on, last_cmd, last_response):
    screen.fill((9, 11, 8))
    focus_room_id = (
        state.current_room_id
        if state.current_room_id in FOCUSED_INTERIOR_ROOMS
        else None
    )
    draw_map_overlay(screen, font_mt, font_mb, state, focus_room_id=focus_room_id)
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
        prefix = "> " + input_text[:max(0, min(cursor_idx, len(input_text)))]
        cursor_x = text_x + font_in.size(prefix)[0]
        cursor_y = min(HEIGHT - 6, text_y + font_in.get_height() + 2)
        pygame.draw.line(screen, (220, 235, 200), (cursor_x, cursor_y), (cursor_x + 10, cursor_y), 2)

    hf = pygame.font.SysFont(None, 18)
    hint = hf.render("M close map   arrows move when input is empty   Left/Right edit text", True, (42, 58, 32))
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


def _edit_input_line(ev, text: str, cursor_idx: int) -> tuple[bool, str, int]:
    cursor_idx = max(0, min(cursor_idx, len(text)))
    if ev.key == pygame.K_LEFT:
        return True, text, max(0, cursor_idx - 1)
    if ev.key == pygame.K_RIGHT:
        return True, text, min(len(text), cursor_idx + 1)
    if ev.key == pygame.K_HOME:
        return True, text, 0
    if ev.key == pygame.K_END:
        return True, text, len(text)
    if ev.key == pygame.K_BACKSPACE:
        if cursor_idx <= 0:
            return True, text, cursor_idx
        return True, text[:cursor_idx - 1] + text[cursor_idx:], cursor_idx - 1
    if ev.key == pygame.K_DELETE:
        if cursor_idx >= len(text):
            return True, text, cursor_idx
        return True, text[:cursor_idx] + text[cursor_idx + 1:], cursor_idx

    is_modifier = ev.mod & (pygame.KMOD_CTRL | pygame.KMOD_META | pygame.KMOD_ALT)
    if ev.unicode and ev.unicode.isprintable() and not is_modifier:
        updated = text[:cursor_idx] + ev.unicode + text[cursor_idx:]
        return True, updated, cursor_idx + len(ev.unicode)
    return False, text, cursor_idx



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
    cursor_idx = 0
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
                    continue

                if mode == "game":
                    if ev.key == pygame.K_PAGEUP:
                        scroll += 5
                        continue
                    if ev.key == pygame.K_PAGEDOWN:
                        scroll = max(0, scroll - 5)
                        continue

                if mode in ("game", "map"):
                    if ev.key in ARROW_DIRS and not input_text and cursor_idx == 0:
                        scroll = 0
                        cmd = f"go {ARROW_DIRS[ev.key]}"
                        last_cmd = cmd
                        last_response = _dispatch(cmd, state, log_lines)
                        if not state.is_running:
                            return _finish_after_game_end(screen, clock, state)
                        save_game_state(state)
                        log_lines = clamp_log(log_lines)
                        continue

                    if ev.key == pygame.K_RETURN:
                        cmd = input_text.strip()
                        input_text = ""
                        cursor_idx = 0
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
                            if not state.is_running:
                                return _finish_after_game_end(screen, clock, state)
                            save_game_state(state)
                            log_lines = clamp_log(log_lines)
                        continue

                    edited, input_text, cursor_idx = _edit_input_line(ev, input_text, cursor_idx)
                    if edited:
                        continue

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
            draw_map_screen(screen, font_mt, font_mb, font, state, input_text, cursor_idx, cursor_on, last_cmd, last_response)
        else:
            draw_game_screen(screen, font, font_b, log_lines, input_text, cursor_idx, scroll, cursor_on)
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
