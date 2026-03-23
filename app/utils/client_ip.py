"""Resolve client IP from proxy headers, explicit CRM field, or COMMENTS."""

from __future__ import annotations

from app.utils.ip_extract import extract_ipv4_from_comments


def resolve_client_ip_for_lead(
    comments: str | None,
    visitor_ip: str | None,
    x_forwarded_for: str | None,
) -> str | None:
    """Prefer ``X-Forwarded-For``, then ``VISITOR_IP``, then IPv4 embedded in ``COMMENTS``."""
    if x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()
        if first:
            return first
    if visitor_ip and visitor_ip.strip():
        return visitor_ip.strip()
    return extract_ipv4_from_comments(comments)
