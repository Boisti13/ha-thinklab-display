"""Sensors: case temperature, fan, host link, Wi-Fi, boot time."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import BOOT_TIME_TOLERANCE
from .coordinator import ThinkLabConfigEntry
from .entity import ThinkLabEntity


def _non_negative(key: str) -> Callable[[dict[str, Any]], Any]:
    """Read a value the firmware sends as -1 when there is no reading."""

    def value(data: dict[str, Any]) -> Any:
        v = data.get(key)
        return v if isinstance(v, (int, float)) and v >= 0 else None

    return value


@dataclass(frozen=True, kw_only=True)
class ThinkLabSensorDescription(SensorEntityDescription):
    """How to read one sensor from status.json."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[ThinkLabSensorDescription, ...] = (
    ThinkLabSensorDescription(
        key="case_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.get("case_c"),
    ),
    ThinkLabSensorDescription(
        key="fan_speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_non_negative("fan_rpm"),
    ),
    ThinkLabSensorDescription(
        key="fan2_speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_non_negative("fan2_rpm"),
    ),
    ThinkLabSensorDescription(
        key="fan_duty",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_non_negative("fan_pct"),
    ),
    ThinkLabSensorDescription(
        key="fan_curve_demand",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("fan_curve_pct"),
    ),
    ThinkLabSensorDescription(
        key="fan_manual_time_left",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        value_fn=lambda d: d.get("fan_manual_left_s"),
    ),
    ThinkLabSensorDescription(
        key="fan_min_duty",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("fan_min_pct"),
    ),
    ThinkLabSensorDescription(
        key="fan_stall_kicks",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("fan_stall_kicks"),
    ),
    ThinkLabSensorDescription(
        key="host_answer_age",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("host_age_s"),
    ),
    ThinkLabSensorDescription(
        key="parse_errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("parse_err"),
    ),
    ThinkLabSensorDescription(
        key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("rssi_dbm"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThinkLabConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [ThinkLabSensor(coordinator, d) for d in SENSORS]
    entities.append(ThinkLabBootTime(coordinator))
    async_add_entities(entities)


class ThinkLabSensor(ThinkLabEntity, SensorEntity):
    """A value from status.json."""

    entity_description: ThinkLabSensorDescription

    def __init__(self, coordinator, description: ThinkLabSensorDescription) -> None:
        """Remember what to read."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Current value."""
        return self.entity_description.value_fn(self.data)


class ThinkLabBootTime(ThinkLabEntity, SensorEntity):
    """When the board last started (from its uptime)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """No boot time known yet."""
        super().__init__(coordinator, "last_restart")
        self._boot: datetime | None = None

    @property
    def native_value(self) -> datetime | None:
        """Boot time, held steady against poll jitter."""
        uptime = self.data.get("esp_uptime_sec")
        if not isinstance(uptime, (int, float)):
            return self._boot
        boot = dt_util.utcnow() - timedelta(seconds=uptime)
        if self._boot is None or abs(boot - self._boot) > BOOT_TIME_TOLERANCE:
            self._boot = boot.replace(microsecond=0)
        return self._boot
