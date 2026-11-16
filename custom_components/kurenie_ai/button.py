"""Tlačidlá: spustiť agenta teraz, ohrev TÚV."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import model
from .coordinator import KurenieConfigEntry, KurenieCoordinator
from .entity import KurenieEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class KurenieButtonDescription(ButtonEntityDescription):
    request_fn: Callable[[], tuple[str, dict]]
    requires_dhw: bool = False


DESCRIPTIONS: tuple[KurenieButtonDescription, ...] = (
    KurenieButtonDescription(key="run_now", translation_key="run_now", request_fn=model.action_run_now),
    KurenieButtonDescription(key="dhw_boost", translation_key="dhw_boost", request_fn=model.action_tuv_boost, requires_dhw=True),
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
                new.append(KurenieButton(coordinator, desc))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class KurenieButton(KurenieEntity, ButtonEntity):
    entity_description: KurenieButtonDescription

    def __init__(self, coordinator: KurenieCoordinator, description: KurenieButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_action(self.entity_description.request_fn())
