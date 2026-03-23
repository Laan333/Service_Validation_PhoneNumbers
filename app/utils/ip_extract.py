"""Extract client IPv4 from Bitrix-style COMMENTS blocks."""

from __future__ import annotations

import re

_IP_IN_COMMENTS = re.compile(
    r"IP:\s*\[b\](?P<ip>(?:\d{1,3}\.){3}\d{1,3})\[/b\]",
    re.IGNORECASE,
)


def extract_ipv4_from_comments(comments: str | None) -> str | None:
    """Return first IPv4 from ``IP: [b]x.x.x.x[/b]`` line if present."""
    if not comments:
        return None
    match = _IP_IN_COMMENTS.search(comments)
    return match.group("ip") if match else None
