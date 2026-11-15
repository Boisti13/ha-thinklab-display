"""Fan duty: setting it switches the fan to manual at that duty."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ThinkLabConfigEntry
from .entity import ThinkLabEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThinkLabConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the fan duty number."""
    async_add_entities([ThinkLabFanDuty(entry.runtime_data)])


class ThinkLabFanDuty(ThinkLabEntity, NumberEntity):
    """Shows the duty the fan gets; a new value sets manual mode."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        """One per board."""
        super().__init__(coordinator, "fan_manual_duty")

    @property
    def native_value(self) -> float | None:
        """Duty now (auto or manual)."""
        duty = self.data.get("fan_pct")
        return duty if isinstance(duty, (int, float)) and duty >= 0 else None

    async def async_set_native_value(self, value: float) -> None:
        """Manual at this duty; the board returns to auto after an hour or at 50 °C."""
        await self._act(self.coordinator.client.set_fan_manual(round(value)))
