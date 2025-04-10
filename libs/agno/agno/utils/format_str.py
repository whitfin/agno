from typing import Optional


def remove_indent(s: Optional[str]) -> Optional[str]:
    """
    Remove the indent from a string.

    Args:
        s (str): String to remove indent from

    Returns:
        str: String with indent removed
    """
    if s is not None and isinstance(s, str):
        return "\n".join([line.strip() for line in s.split("\n")])
    return None


def url_safe(s: Optional[str]) -> Optional[str]:
    """
    Convert a string to a URL-safe string.

    Args:
        s (str): String to convert to URL-safe
    """
    if s is None:
        return None
    return "-".join("".join(c.lower() for c in s if c.isalnum() or c == " ").split())
