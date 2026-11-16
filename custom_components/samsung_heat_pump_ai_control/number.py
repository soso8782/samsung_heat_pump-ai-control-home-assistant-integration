"""Cieľová izbová teplota."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import model
from .coordinator import KurenieConfigEntry, KurenieCoordinator
from .entity import KurenieEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: KurenieConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([KurenieRoomTarget(entry.runtime_data)])


class KurenieRoomTarget(KurenieEntity, NumberEntity):
    _attr_translation_key = "room_target"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: KurenieCoordinator) -> None:
        super().__init__(coordinator, "room_target")

    @property
    def native_min_value(self) -> float:
        return model.room_target_range(self.coordinator.data)[0]

    @property
    def native_max_value(self) -> float:
        return model.room_target_range(self.coordinator.data)[1]

    @property
    def native_value(self) -> float | None:
        return model.room_target(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_action(model.action_room_target(value))
