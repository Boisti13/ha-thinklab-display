"""Binary sensors: host link problem, fan running."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ThinkLabConfigEntry
from .entity import ThinkLabEntity


@dataclass(frozen=True, kw_only=True)
class ThinkLabBinaryDescription(BinarySensorEntityDescription):
    """How to read one binary sensor from status.json."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[ThinkLabBinaryDescription, ...] = (
    ThinkLabBinaryDescription(
        key="host_link_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.get("host_stale"),
    ),
    ThinkLabBinaryDescription(
        key="fan_stalled",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.get("fan_stalled"),
    ),
    ThinkLabBinaryDescription(
        key="fan_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("fan_on"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThinkLabConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(ThinkLabBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class ThinkLabBinarySensor(ThinkLabEntity, BinarySensorEntity):
    """A flag from status.json."""

    entity_description: ThinkLabBinaryDescription

    def __init__(self, coordinator, description: ThinkLabBinaryDescription) -> None:
        """Remember what to read."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Current state."""
        return self.entity_description.value_fn(self.data)
