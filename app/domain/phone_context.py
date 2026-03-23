"""Client IP / geo context for phone normalization."""

from dataclasses import dataclass


@dataclass(slots=True)
class PhoneValidationContext:
    """Resolved geography used when inferring country code for local numbers."""

    client_ip: str | None
    geo_country_iso: str
    """Uppercase ISO 3166-1 alpha-2 (e.g. ``US``, ``MX``)."""
    default_cc_applied: bool
    """True when IP was missing, private, geo disabled, or lookup failed."""
