def safe_md(text: str) -> str:
    """Escape common Telegram Markdown characters in external text."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("`", "'")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
