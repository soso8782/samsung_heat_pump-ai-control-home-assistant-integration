"""Senzory Samsung Heat Pump AI Control."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfFrequency, UnitOfTemperature
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import model
from .coordinator import KurenieConfigEntry, KurenieCoordinator
from .entity import KurenieEntity

PARALLEL_UPDATES = 0

TEMP = {
    "device_class": SensorDeviceClass.TEMPERATURE,
    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
    "state_class": SensorStateClass.MEASUREMENT,
}


@dataclass(frozen=True, kw_only=True)
class KurenieSensorDescription(SensorEntityDescription):
    """Popis senzora: hodnota sa berie z model.SENSORS[key]."""

    attrs_fn: Callable[[dict], dict] | None = None
    requires_dhw: bool = False


DESCRIPTIONS: tuple[KurenieSensorDescription, ...] = (
    KurenieSensorDescription(key="outdoor_temperature", translation_key="outdoor_temperature", **TEMP),
    KurenieSensorDescription(key="water_out", translation_key="water_out", **TEMP),
    KurenieSensorDescription(key="water_return", translation_key="water_return", **TEMP),
    KurenieSensorDescription(key="water_target", translation_key="water_target", **TEMP),
    KurenieSensorDescription(
        key="water_delta_t",
        translation_key="water_delta_t",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KurenieSensorDescription(
        key="compressor_frequency",
        translation_key="compressor_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KurenieSensorDescription(
        key="curve_offset",
        translation_key="curve_offset",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KurenieSensorDescription(key="dhw_temperature", translation_key="dhw_temperature", requires_dhw=True, **TEMP),
    KurenieSensorDescription(
        key="error_code",
        translation_key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    KurenieSensorDescription(
        key="agent_state",
        translation_key="agent_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(model.AGENT_STATES),
        attrs_fn=model.agent_attributes,
    ),
    KurenieSensorDescription(key="agent_summary", translation_key="agent_summary", attrs_fn=model.agent_attributes),
    KurenieSensorDescription(
        key="alert_count",
        translation_key="alert_count",
        state_class=SensorStateClass.MEASUREMENT,
        attrs_fn=model.alert_attributes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: KurenieConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[SensorEntity] = []
        for desc in DESCRIPTIONS:
            if desc.key not in known and (not desc.requires_dhw or model.has_dhw(coordinator.data)):
                known.add(desc.key)
                new.append(KurenieSensor(coordinator, desc))
        for room in model.rooms(coordinator.data):
            uid = "room_" + room["kluc"]
            if uid not in known:
                known.add(uid)
                new.append(KurenieRoomSensor(coordinator, room["kluc"]))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class KurenieSensor(KurenieEntity, SensorEntity):
    entity_description: KurenieSensorDescription

    def __init__(self, coordinator: KurenieCoordinator, description: KurenieSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return model.SENSORS[self.entity_description.key](self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        return fn(self.coordinator.data) if fn else None


class KurenieRoomSensor(KurenieEntity, SensorEntity):
    """Teplota jednej izby (názov izby ako placeholder prekladu)."""

    _attr_translation_key = "room_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: KurenieCoordinator, room_key: str) -> None:
        super().__init__(coordinator, "room_" + room_key)
        self._room_key = room_key
        self._attr_translation_placeholders = {"room": model.room_name(coordinator.data, room_key)}

    @property
    def native_value(self) -> Any:
        return model.room_temperature(self.coordinator.data, self._room_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return model.room_attributes(self.coordinator.data, self._room_key)
