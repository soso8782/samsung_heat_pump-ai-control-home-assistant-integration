"""Integrácia Samsung Heat Pump AI Control pre Home Assistant."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KurenieClient
from .const import CONF_API_KEY, CONF_URL, PLATFORMS
from .coordinator import KurenieConfigEntry, KurenieCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: KurenieConfigEntry) -> bool:
    """Nastaví konfiguračný záznam."""
    client = KurenieClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_API_KEY])
    coordinator = KurenieCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: KurenieConfigEntry) -> None:
    """Zmena volieb (interval obnovy) = reload."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: KurenieConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
