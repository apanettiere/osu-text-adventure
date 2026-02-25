def parse_command(text: str) -> tuple[str, str | None]:
    parts = text.strip().lower().split()

    if not parts:
        return "", None

    verb = parts[0]
    target = parts[1] if len(parts) > 1 else None

    return verb, target