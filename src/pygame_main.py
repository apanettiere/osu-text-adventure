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
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    title = font_title.render("MAP", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 90)))

    discovered = list(state.player.discovered_rooms)
    positions = state.player.room_positions

    if not discovered:
        surf = font_body.render("No rooms discovered yet.", True, (220, 220, 220))
        screen.blit(surf, surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        return

    # Collect discovered positions (only those with coordinates)
    coords = []
    for room_id in discovered:
        pos = positions.get(room_id)
        if pos is not None:
            coords.append(pos)

    if not coords:
        surf = font_body.render("Map data missing.", True, (220, 220, 220))
        screen.blit(surf, surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        return

    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)

    TILE = 16
    DOT = 10

    map_w = (max_x - min_x + 1) * TILE
    map_h = (max_y - min_y + 1) * TILE

    origin_x = (WIDTH // 2) - (map_w // 2)
    origin_y = 150

    # Panel behind the map
    panel_pad = 18
    panel_rect = pygame.Rect(
        origin_x - panel_pad,
        origin_y - panel_pad,
        map_w + panel_pad * 2,
        map_h + panel_pad * 2,
    )
    pygame.draw.rect(screen, (25, 25, 25), panel_rect, border_radius=10)
    pygame.draw.rect(screen, (80, 80, 80), panel_rect, width=2, border_radius=10)

    # Draw discovered rooms
    for room_id in discovered:
        pos = positions.get(room_id)
        if pos is None:
            continue

        x, y = pos
        sx = origin_x + (x - min_x) * TILE + (TILE - DOT) // 2
        sy = origin_y + (y - min_y) * TILE + (TILE - DOT) // 2

        rect = pygame.Rect(sx, sy, DOT, DOT)

        dest_room = state.rooms.get(room_id)
        is_blocked = bool(dest_room and dest_room.requires)

        if room_id == state.current_room_id:
            pygame.draw.rect(screen, (245, 245, 245), rect, border_radius=3)
            at = font_body.render("@", True, (20, 20, 20))
            screen.blit(at, at.get_rect(center=rect.center))

        elif is_blocked:
            pygame.draw.rect(screen, (110, 110, 110), rect, border_radius=3)
            xsurf = font_body.render("X", True, (20, 20, 20))
            screen.blit(xsurf, xsurf.get_rect(center=rect.center))

        else:
            pygame.draw.rect(screen, (170, 170, 170), rect, border_radius=3)

    legend_lines = [
        "@ = you",
        ". = discovered room",
        "X = blocked",
        "",
        "M = close",
        "ESC = menu",
    ]

    y = panel_rect.bottom + 18
    for line in legend_lines:
        surf = font_body.render(line, True, (220, 220, 220))
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
        y += 26


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