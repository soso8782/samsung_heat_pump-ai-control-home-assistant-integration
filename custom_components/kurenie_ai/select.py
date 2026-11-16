"""Výber režimu agenta."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import model
from .coordinator import KurenieConfigEntry, KurenieCoordinator
from .entity import KurenieEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: KurenieConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([KurenieAgentMode(entry.runtime_data)])


class KurenieAgentMode(KurenieEntity, SelectEntity):
    _attr_translation_key = "agent_mode"
    _attr_options = list(model.MODES)

    def __init__(self, coordinator: KurenieCoordinator) -> None:
        super().__init__(coordinator, "agent_mode")

    @property
    def current_option(self) -> str | None:
        return model.agent_mode(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_action(model.action_mode(option))
