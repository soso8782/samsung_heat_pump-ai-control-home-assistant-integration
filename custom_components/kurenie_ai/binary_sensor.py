"""Binárne senzory Kúrenie AI."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import model
from .coordinator import KurenieConfigEntry, KurenieCoordinator
from .entity import KurenieEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class KurenieBinaryDescription(BinarySensorEntityDescription):
    requires_dhw: bool = False


DESCRIPTIONS: tuple[KurenieBinaryDescription, ...] = (
    KurenieBinaryDescription(key="compressor_running", translation_key="compressor_running", device_class=BinarySensorDeviceClass.RUNNING),
    KurenieBinaryDescription(key="defrost", translation_key="defrost", device_class=BinarySensorDeviceClass.RUNNING),
    KurenieBinaryDescription(key="dhw_heating", translation_key="dhw_heating", device_class=BinarySensorDeviceClass.RUNNING, requires_dhw=True),
    KurenieBinaryDescription(key="problem", translation_key="problem", device_class=BinarySensorDeviceClass.PROBLEM),
    KurenieBinaryDescription(
        key="esp_online", translation_key="esp_online", device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KurenieBinaryDescription(
        key="collector_online", translation_key="collector_online", device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KurenieBinaryDescription(
        key="ha_online", translation_key="ha_online", device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: KurenieConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _discover() -> None:
        new = []
        for desc in DESCRIPTIONS:
            if desc.key not in known and (not desc.requires_dhw or model.has_dhw(coordinator.data)):
                known.add(desc.key)
                new.append(KurenieBinarySensor(coordinator, desc))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class KurenieBinarySensor(KurenieEntity, BinarySensorEntity):
    entity_description: KurenieBinaryDescription

    def __init__(self, coordinator: KurenieCoordinator, description: KurenieBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return model.bool_or_none(model.BINARY_SENSORS[self.entity_description.key](self.coordinator.data))
