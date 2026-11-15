"""Buttons: restart the board, turn or redraw the e-paper page."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import ThinkLabClient
from .coordinator import ThinkLabConfigEntry
from .entity import ThinkLabEntity


@dataclass(frozen=True, kw_only=True)
class ThinkLabButtonDescription(ButtonEntityDescription):
    """Which command a button sends."""

    press_fn: Callable[[ThinkLabClient], Awaitable[None]]


BUTTONS: tuple[ThinkLabButtonDescription, ...] = (
    ThinkLabButtonDescription(
        key="next_page",
        press_fn=lambda c: c.next_page(),
    ),
    ThinkLabButtonDescription(
        key="refresh_page",
        press_fn=lambda c: c.refresh_page(),
    ),
    ThinkLabButtonDescription(
        key="restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c: c.reboot(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThinkLabConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the buttons."""
    coordinator = entry.runtime_data
    async_add_entities(ThinkLabButton(coordinator, d) for d in BUTTONS)


class ThinkLabButton(ThinkLabEntity, ButtonEntity):
    """Sends one command."""

    entity_description: ThinkLabButtonDescription

    def __init__(self, coordinator, description: ThinkLabButtonDescription) -> None:
        """Remember the command."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Send it."""
        await self._act(self.entity_description.press_fn(self.coordinator.client))
