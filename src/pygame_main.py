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


def draw_map_overlay(screen: pygame.Surface, font_title: pygame.font.Font, font_body: pygame.font.Font) -> None:
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    title = font_title.render("MAP", True, (240, 240, 240))
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))

    body_lines = [
        "Map system coming soon.",
        "",
        "This overlay is here to prove the UI architecture:",
        "- Press M to toggle map overlay",
        "- Later: discovered rooms, player marker, paths, icons",
        "",
        "Press M to return to the game.",
        "Press ESC to return to the main menu."
    ]

    y = 200
    for line in body_lines:
        surf = font_body.render(line, True, (220, 220, 220))
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
        y += 30


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
                    continue

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
            draw_map_overlay(screen, font_overlay_title, font_overlay_body)

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