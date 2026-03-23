"""Resolve country ISO code via IPinfo Lite API with in-memory TTL cache."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from typing import ClassVar

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class IpGeoService:
    """Async IP → ISO country; caches results per process."""

    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _cache: ClassVar[dict[str, tuple[float, str]]] = {}

    async def resolve(self, ip: str | None) -> tuple[str, bool]:
        """Return ``(iso_country_upper, default_applied)``.

        ``default_applied`` is True when lookup was skipped or failed.
        """
        default = settings.ip_geo_default_country.upper()
        if not ip or not ip.strip():
            return default, True
        candidate = ip.strip()
        if not self._is_public_ip(candidate):
            return default, True
        if not settings.ip_geo_enabled:
            return default, True

        now = time.monotonic()
        ttl = float(settings.ip_geo_cache_ttl_seconds)
        async with self._lock:
            hit = self._cache.get(candidate)
            if hit is not None:
                ts, country = hit
                if now - ts < ttl:
                    return country, False

        country = await self._fetch_country(candidate)
        if country is None:
            return default, True

        async with self._lock:
            self._cache[candidate] = (now, country)
        return country, False

    async def _fetch_country(self, ip: str) -> str | None:
        token = (settings.ipinfo_token or "").strip()
        if not token:
            logger.warning("IPINFO_TOKEN is empty; set it from https://ipinfo.io/signup (Lite API). Skipping lookup.")
            return None

        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            logger.warning("Invalid IP for geo lookup: %s", ip)
            return None

        if parsed.version == 6:
            url = f"https://v6.api.ipinfo.io/lite/{ip}"
        else:
            url = f"https://api.ipinfo.io/lite/{ip}"

        try:
            async with httpx.AsyncClient(timeout=settings.ip_geo_timeout_seconds) as client:
                response = await client.get(url, params={"token": token})
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("IPinfo Lite lookup failed for %s: %s", ip, exc)
            return None

        code = data.get("country_code")
        if not isinstance(code, str) or len(code) != 2:
            logger.warning("IPinfo Lite response missing country_code for %s: %s", ip, data)
            return None
        return code.upper()

    @staticmethod
    def _is_public_ip(ip: str) -> bool:
        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return bool(parsed.is_global)
