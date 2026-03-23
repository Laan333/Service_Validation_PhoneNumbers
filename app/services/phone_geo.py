"""Country ISO → E.164 country calling code; fix duplicated leading US trunk ``1``."""

# Primary lead regions from product brief
GEO_TO_DIAL: dict[str, str] = {
    "US": "1",
    "CA": "1",
    "MX": "52",
    "BR": "55",
    "IN": "91",
    "IT": "39",
    "RU": "7",
    "GB": "44",
    "FR": "33",
    "DE": "49",
    "ES": "34",
    "CO": "57",
    "AU": "61",
}

# If digits start with ``1`` and total length is too long for NANP (+1 + 10),
# strip that ``1`` when remainder begins with a known non-US CC (e.g. ``+1393…`` → ``+39…``).
_WRAPPED_AFTER_ONE: tuple[str, ...] = ("44", "49", "52", "55", "57", "61", "91", "39", "33", "34", "7")


def strip_erroneous_leading_us_one(digits: str) -> str:
    """Remove a spurious leading ``1`` before another country's calling code."""
    if len(digits) < 12 or not digits.startswith("1"):
        return digits
    tail = digits[1:]
    for code in _WRAPPED_AFTER_ONE:
        if tail.startswith(code):
            return tail
    return digits


def dial_for_geo(iso_country: str) -> str | None:
    """Return numeric country calling code without ``+``, or None if unknown."""
    return GEO_TO_DIAL.get(iso_country.upper())
