"""Fan mode: auto (temperature curve) or manual."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FAN_MODE_AUTO, FAN_MODE_MANUAL
from .coordinator import ThinkLabConfigEntry
from .entity import ThinkLabEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThinkLabConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the fan mode select."""
    async_add_entities([ThinkLabFanMode(entry.runtime_data)])


class ThinkLabFanMode(ThinkLabEntity, SelectEntity):
    """Auto follows the curve; manual holds the current duty (for up to an hour)."""

    _attr_options: ClassVar[list[str]] = [FAN_MODE_AUTO, FAN_MODE_MANUAL]

    def __init__(self, coordinator) -> None:
        """One per board."""
        super().__init__(coordinator, "fan_mode")

    @property
    def current_option(self) -> str | None:
        """Mode the board reports."""
        auto = self.data.get("fan_auto")
        if auto is None:
            return None
        return FAN_MODE_AUTO if auto else FAN_MODE_MANUAL

    async def async_select_option(self, option: str) -> None:
        """Switch mode; manual keeps the duty the fan runs at now."""
        client = self.coordinator.client
        if option == FAN_MODE_AUTO:
            await self._act(client.set_fan_auto())
        else:
            duty = self.data.get("fan_pct")
            duty = duty if isinstance(duty, int) and duty >= 0 else 50
            await self._act(client.set_fan_manual(duty))
