from typing import Set


def create_panel(content, title, border_style="blue"):
    from rich.box import HEAVY
    from rich.panel import Panel

    return Panel(
        content, title=title, title_align="left", border_style=border_style, box=HEAVY, expand=True, padding=(1, 1)
    )

def escape_markdown_tags(content: str, tags: Set[str]) -> str:
    """Escape special tags in markdown content."""
    escaped_content = content
    for tag in tags:
        # Escape opening tag
        escaped_content = escaped_content.replace(f"<{tag}>", f"&lt;{tag}&gt;")
        # Escape closing tag
        escaped_content = escaped_content.replace(f"</{tag}>", f"&lt;/{tag}&gt;")
    return escaped_content
