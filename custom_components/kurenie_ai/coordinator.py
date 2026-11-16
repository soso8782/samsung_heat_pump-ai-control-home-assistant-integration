"""DataUpdateCoordinator integrácie Kúrenie AI."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KurenieApiError, KurenieAuthError, KurenieClient, KurenieConnectionError
from .const import CONF_SCAN_INTERVAL, DOMAIN
from .model import clamp_interval

_LOGGER = logging.getLogger(__name__)

KurenieConfigEntry = ConfigEntry["KurenieCoordinator"]   # typový alias; entry.runtime_data = KurenieCoordinator


class KurenieCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Pravidelne číta stav aplikácie a vykonáva akcie."""

    config_entry: KurenieConfigEntry

    def __init__(self, hass: HomeAssistant, entry: KurenieConfigEntry, client: KurenieClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=clamp_interval(entry.options.get(CONF_SCAN_INTERVAL))),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_state()
        except KurenieAuthError as err:
            raise ConfigEntryAuthFailed("Integration key was rejected") from err
        except (KurenieConnectionError, KurenieApiError) as err:
            raise UpdateFailed(f"Error communicating with Kúrenie AI: {err}") from err

    async def async_action(self, request: tuple[str, dict]) -> None:
        """Vykoná akciu (cesta, telo), potom okamžite obnoví dáta. Chyby -> HomeAssistantError."""
        path, body = request
        try:
            result = await self.client.async_post(path, body)
        except KurenieAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="action_auth", translation_placeholders={}
            ) from err
        except (KurenieConnectionError, KurenieApiError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="action_failed", translation_placeholders={"error": str(err)}
            ) from err
        if result.get("ok") is False:   # aplikácia akciu odmietla (napr. ohrev TÚV teraz nejde)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_failed",
                translation_placeholders={"error": str(result.get("text") or result.get("error") or "?")},
            )
        await self.async_request_refresh()
