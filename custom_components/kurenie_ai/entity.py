"""Základná entita integrácie Kúrenie AI."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import model
from .const import CONF_URL, DOMAIN, MANUFACTURER
from .coordinator import KurenieCoordinator


class KurenieEntity(CoordinatorEntity[KurenieCoordinator]):
    """Entita patriaca jedinému zariadeniu „Kúrenie AI“."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KurenieCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        info = model.device_info(coordinator.data)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=info["name"],
            model=info["model"],
            sw_version=info["sw_version"],
            configuration_url=entry.data[CONF_URL],
        )
