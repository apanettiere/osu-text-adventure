import pygame

from engine.game_state import GameState
from engine.parser import parse_command


WIDTH = 960
HEIGHT = 640
FPS = 60

PADDING = 16
LINE_HEIGHT = 26
INPUT_HEIGHT = 56

MAX_LOG_LINES = 300


def clamp_log(lines: list[str]) -> list[str]:
    if len(lines) > MAX_LOG_LINES:
        return lines[-MAX_LOG_LINES:]
    return lines


def point_in_rect(pos: tuple[int, int], rect: pygame.Rect) -> bool:
    return rect.collidepoint(pos[0], pos[1])


def draw_button(
    screen: pygame.Surface,
    rect: pygame.Rect,
    text: str,
    font: pygame.font.Font,
    hovered: bool,
) -> None:
    bg = (60, 60, 60) if hovered else (45, 45, 45)
    border = (90, 90, 90)

    pygame.draw.rect(screen, bg, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, width=2, border_radius=10)

    label = font.render(text, True, (245, 245, 245))
    label_rect = label.get_rect(center=rect.center)
    screen.blit(label, label_rect)


def run_menu(screen: pygame.Surface, clock: pygame.time.Clock) -> str:
    font_title = pygame.font.SysFont(None, 52, bold=True)
    font_btn = pygame.font.SysFont(None, 30, bold=True)
    font_hint = pygame.font.SysFont(None, 22)

    start_rect = pygame.Rect(0, 0, 260, 56)
    quit_rect = pygame.Rect(0, 0, 260, 56)

    start_rect.center = (WIDTH // 2, HEIGHT // 2 + 30)
    quit_rect.center = (WIDTH // 2, HEIGHT // 2 + 100)

    while True:
        clock.tick(FPS)

        mouse_pos = pygame.mouse.get_pos()
        start_hover = point_in_rect(mouse_pos, start_rect)
        quit_hover = point_in_rect(mouse_pos, quit_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_hover:
                    return "start"
                if quit_hover:
                    return "quit"

        screen.fill((14, 14, 14))

        title = font_title.render("THE DARK FOREST", True, (240, 240, 240))
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
        screen.blit(title, title_rect)

        hint = font_hint.render("A text-based survival adventure", True, (190, 190, 190))
        hint_rect = hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))
        screen.blit(hint, hint_rect)

        draw_button(screen, start_rect, "Start Game", font_btn, start_hover)
        draw_button(screen, quit_rect, "Quit", font_btn, quit_hover)

        pygame.display.flip()


def draw_game_screen(
    screen: pygame.Surface,
    font: pygame.font.Font,
    font_bold: pygame.font.Font,
    log_lines: list[str],
    input_text: str,
    scroll_offset: int,
) -> None:
    screen.fill((18, 18, 18))

    output_top = PADDING
    output_left = PADDING
    output_right = WIDTH - PADDING
    output_bottom = HEIGHT - INPUT_HEIGHT - PADDING
    output_height = output_bottom - output_top

    pygame.draw.rect(
        screen,
        (28, 28, 28),
        (output_left - 8, output_top - 8, (output_right - output_left) + 16, output_height + 16),
        border_radius=8,
    )

    lines_fit = max(1, output_height // LINE_HEIGHT)

    start_index = max(0, len(log_lines) - lines_fit - scroll_offset)
    end_index = start_index + lines_fit
    visible = log_lines[start_index:end_index]

    y = output_top
    for line in visible:
        if line.startswith("\n"):
            surf = font_bold.render(line.strip(), True, (240, 240, 240))
        else:
            surf = font.render(line, True, (220, 220, 220))

        screen.blit(surf, (output_left, y))
        y += LINE_HEIGHT

    input_y = HEIGHT - INPUT_HEIGHT
    pygame.draw.rect(screen, (40, 40, 40), (0, input_y, WIDTH, INPUT_HEIGHT))
    pygame.draw.rect(screen, (60, 60, 60), (0, input_y, WIDTH, 2))

    prompt = "> " + input_text
    surf = font.render(prompt, True, (255, 255, 255))
    screen.blit(surf, (PADDING, input_y + 18))


def draw_map_overlay(
    screen: pygame.Surface,
    font_title: pygame.font.Font,
    font_body: pygame.font.Font,
    state: GameState,
) -> None:
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    screen.blit(overlay, (0, 0))

    CELL = 11
    try:
        mfont = pygame.font.SysFont("Courier New", CELL + 1, bold=False)
    except Exception:
        mfont = pygame.font.SysFont(None, CELL + 2)

    # Each room is drawn as a box RW chars wide x RH chars tall.
    # For walkable rooms the interior is actual tile-sized.
    # For instant-travel rooms we use a compact 7x5 box.
    BASE_RW, BASE_RH = 7, 5      # compact box for instant-travel rooms
    WALK_CELL = 7                 # px per intra-room tile (must fit in CELL)
    GAP_X, GAP_Y = 4, 3          # gap chars between room boxes

    discovered = list(state.player.discovered_rooms)
    positions  = state.player.room_positions

    if not discovered:
        surf = font_body.render("No rooms discovered yet.", True, (170, 170, 170))
        screen.blit(surf, surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        return

    coords = [(rid, positions[rid]) for rid in discovered if rid in positions]
    if not coords:
        surf = font_body.render("Map data missing.", True, (170, 170, 170))
        screen.blit(surf, surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        return

    xs = [p[0] for _, p in coords]
    ys = [p[1] for _, p in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def room_box(room) -> tuple[int, int]:
        """Return (char_w, char_h) for a room's box."""
        if room and room.is_walkable:
            return room.width + 2, room.height + 2   # +2 for border
        return BASE_RW, BASE_RH

    # Compute max box size for uniform grid spacing
    max_rw = BASE_RW
    max_rh = BASE_RH
    for rid, _ in coords:
        r = state.rooms.get(rid)
        rw, rh = room_box(r)
        max_rw = max(max_rw, rw)
        max_rh = max(max_rh, rh)

    GX = max_rw + GAP_X
    GY = max_rh + GAP_Y

    total_char_w = (max_x - min_x) * GX + max_rw
    total_char_h = (max_y - min_y) * GY + max_rh
    origin_px_x  = (WIDTH  - total_char_w * CELL) // 2
    origin_px_y  = (HEIGHT - total_char_h * CELL) // 2 + 18

    # title
    title_surf = font_title.render("MAP", True, (200, 200, 200))
    screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, origin_px_y - 30)))

    C_WALL      = (75,  75,  75)
    C_FLOOR     = (45,  45,  45)
    C_FLOOR_LIT = (100, 100, 100)
    C_PLAYER    = (240, 240, 240)
    C_BLOCKED_W = (50,  50,  50)
    C_BLOCKED_F = (30,  30,  30)
    C_FEATURE   = (150, 150, 110)
    C_CORRIDOR  = (60,  60,  60)
    C_LABEL     = (160, 160, 160)

    def put(cx: int, cy: int, ch: str, color: tuple) -> None:
        sx = origin_px_x + cx * CELL
        sy = origin_px_y + cy * CELL
        screen.blit(mfont.render(ch, True, color), (sx, sy))

    pos_to_room: dict = {}
    for rid, pos in coords:
        pos_to_room[pos] = rid

    DIRS = {"north": (0,-1), "south": (0,1), "east": (1,0), "west": (-1,0)}

    # ── corridors (drawn first, behind rooms) ─────────────────────────────────
    for rid, (gx, gy) in coords:
        room = state.rooms.get(rid)
        if not room:
            continue
        rw, rh = room_box(room)
        cx0 = (gx - min_x) * GX + rw // 2
        cy0 = (gy - min_y) * GY + rh // 2

        for direction, (dx, dy) in DIRS.items():
            if direction not in room.exits:
                continue
            nx2, ny2 = gx + dx, gy + dy
            if (nx2, ny2) not in pos_to_room:
                continue
            if direction == "east":
                for step in range(1, GX - rw + rw // 2 + 1):
                    put(cx0 + rw // 2 + step - 1, cy0, "─", C_CORRIDOR)
            elif direction == "south":
                for step in range(1, GY - rh + rh // 2 + 1):
                    put(cx0, cy0 + rh // 2 + step - 1, "│", C_CORRIDOR)

    for rid, (gx, gy) in coords:
        dest_room  = state.rooms.get(rid)
        is_current = (rid == state.current_room_id)
        is_blocked = bool(dest_room and dest_room.requires)
        rw, rh     = room_box(dest_room)
        rx = (gx - min_x) * GX
        ry = (gy - min_y) * GY

        wall_col  = C_BLOCKED_W if is_blocked else C_WALL
        floor_col = C_FLOOR_LIT if is_current else (C_BLOCKED_F if is_blocked else C_FLOOR)

        # walls + floor
        for row in range(rh):
            for col in range(rw):
                on_edge = (row == 0 or row == rh-1 or col == 0 or col == rw-1)
                cx, cy  = rx + col, ry + row
                if on_edge:
                    if   row == 0     and col == 0:      ch = "┌"
                    elif row == 0     and col == rw-1:   ch = "┐"
                    elif row == rh-1  and col == 0:      ch = "└"
                    elif row == rh-1  and col == rw-1:   ch = "┘"
                    elif row == 0     and col == rw//2 and dest_room and "north" in dest_room.exits: ch = "╨"
                    elif row == rh-1  and col == rw//2 and dest_room and "south" in dest_room.exits: ch = "╥"
                    elif col == 0     and row == rh//2 and dest_room and "west"  in dest_room.exits: ch = "╡"
                    elif col == rw-1  and row == rh//2 and dest_room and "east"  in dest_room.exits: ch = "╞"
                    elif row == 0 or row == rh-1: ch = "─"
                    else:                         ch = "│"
                    put(cx, cy, ch, wall_col)
                else:
                    put(cx, cy, "·", floor_col)

        # features
        if dest_room and not is_blocked:
            for feat in getattr(dest_room, "features", []):
                fx, fy = feat.get("pos", (-1, -1))
                if dest_room.is_walkable:
                    # map tile pos to char pos inside border
                    char_x = rx + 1 + fx
                    char_y = ry + 1 + fy
                else:
                    # fixed corners for compact rooms
                    slots = [(rx+1, ry+1), (rx+rw-2, ry+1),
                             (rx+1, ry+rh-2), (rx+rw-2, ry+rh-2)]
                    idx = dest_room.features.index(feat) if feat in dest_room.features else 0
                    char_x, char_y = slots[min(idx, len(slots)-1)]
                put(char_x, char_y, feat.get("label", "?"), C_FEATURE)

        # blocked X
        if is_blocked:
            put(rx + rw//2, ry + rh//2, "✕", C_BLOCKED_W)

        # player marker - positioned at intra-room tile for walkable rooms
        if is_current:
            if dest_room and dest_room.is_walkable:
                px = rx + 1 + state.local_x   # +1 for border
                py = ry + 1 + state.local_y
            else:
                px = rx + rw // 2
                py = ry + rh // 2
            put(px, py, "@", C_PLAYER)
        elif not is_blocked:
            name = (dest_room.name[0].upper() if dest_room and dest_room.name else "?")
            put(rx + rw//2, ry + rh//2, name, C_LABEL)

    legend = "@ you   · floor   ✕ blocked   M close   ESC menu"
    s = mfont.render(legend, True, (90, 90, 90))
    screen.blit(s, s.get_rect(center=(WIDTH // 2, HEIGHT - 22)))


def run_game(screen: pygame.Surface, clock: pygame.time.Clock) -> None:
    font = pygame.font.SysFont(None, 24)
    font_bold = pygame.font.SysFont(None, 24, bold=True)

    font_overlay_title = pygame.font.SysFont(None, 44, bold=True)
    font_overlay_body = pygame.font.SysFont(None, 26)

    state = GameState()

    log_lines: list[str] = []
    log_lines.extend(state.describe_current_room())

    input_text = ""
    scroll_offset = 0

    mode = "game"  # "game" or "map"

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            if event.type == pygame.KEYDOWN:
                # Always allow ESC to return to menu
                if event.key == pygame.K_ESCAPE:
                    return

                # Toggle map overlay
                if event.key == pygame.K_m:
                    mode = "map" if mode == "game" else "game"
                    continue

                if mode == "map":
                    draw_map_overlay(screen, font_overlay_title, font_overlay_body, state)

                if event.key == pygame.K_PAGEUP:
                    scroll_offset += 5
                elif event.key == pygame.K_PAGEDOWN:
                    scroll_offset -= 5
                    if scroll_offset < 0:
                        scroll_offset = 0

                elif event.key == pygame.K_RETURN:
                    cmd = input_text.strip()
                    input_text = ""

                    if cmd:
                        scroll_offset = 0
                        log_lines.append(f"> {cmd}")

                        verb, target = parse_command(cmd)
                        out = state.process_command(verb, target)

                        log_lines.extend(out)
                        log_lines = clamp_log(log_lines)

                        if not state.is_running:
                            return

                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]

                else:
                    if event.unicode and event.unicode.isprintable():
                        input_text += event.unicode

        # Draw base game screen
        draw_game_screen(screen, font, font_bold, log_lines, input_text, scroll_offset)

        if mode == "map":
            draw_map_overlay(screen, font_overlay_title, font_overlay_body, state)

        pygame.display.flip()


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The Dark Forest")
    clock = pygame.time.Clock()

    while True:
        choice = run_menu(screen, clock)

        if choice == "quit":
            break

        if choice == "start":
            run_game(screen, clock)

    pygame.quit()


if __name__ == "__main__":
    main()