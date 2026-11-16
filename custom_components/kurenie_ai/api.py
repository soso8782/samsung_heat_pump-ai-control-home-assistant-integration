"""Klient API Kúrenie AI (v1)."""
from __future__ import annotations

from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT
from .model import API_STATE, validate_state


class KurenieError(Exception):
    """Základná chyba klienta."""


class KurenieConnectionError(KurenieError):
    """Aplikácia je nedostupná."""


class KurenieAuthError(KurenieError):
    """Nesprávny alebo zrušený kľúč integrácie (HTTP 401)."""


class KurenieApiError(KurenieError):
    """Aplikácia odmietla požiadavku; správa je pre používateľa."""


class KurenieClient:
    """Tenký klient nad aiohttp (relácia patrí Home Assistantovi)."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}", "X-Kurenie": "1", "Accept": "application/json"}

    async def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        try:
            async with self._session.request(
                method,
                self._base + path,
                json=body,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status == 401:
                    raise KurenieAuthError("unauthorized")
                try:
                    data = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as err:
                    raise KurenieConnectionError(f"invalid response (HTTP {resp.status})") from err
                if resp.status >= 400:
                    msg = data.get("error") if isinstance(data, dict) else None
                    if resp.status >= 500 and not msg:
                        raise KurenieConnectionError(f"HTTP {resp.status}")
                    raise KurenieApiError(str(msg or f"HTTP {resp.status}"))
                return data
        except (aiohttp.ClientError, TimeoutError) as err:
            raise KurenieConnectionError(str(err) or type(err).__name__) from err

    async def async_get_state(self) -> dict[str, Any]:
        data = await self._request("GET", API_STATE)
        if not validate_state(data):
            raise KurenieConnectionError("unsupported API response")
        return data

    async def async_post(self, path: str, body: dict) -> dict[str, Any]:
        data = await self._request("POST", path, body)
        return data if isinstance(data, dict) else {}
