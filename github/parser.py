import re


def parse_git_url(raw_url: str) -> str | None:
    """Extract owner/repo from common GitHub URL formats or owner/repo input."""
    raw = raw_url.strip()
    if raw.endswith(".git"):
        raw = raw[:-4]

    match = re.search(r"github\.com[/:]([^/]+)/([^/]+)", raw)
    if match:
        repo = match.group(2).rstrip("/")
        return f"{match.group(1)}/{repo}"

    parts = [part for part in raw.strip("/").split("/") if part]
    if len(parts) == 2:
        return f"{parts[0]}/{parts[1]}"

    return None
