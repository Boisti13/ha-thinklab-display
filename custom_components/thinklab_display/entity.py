"""Base entity: everything belongs to the one board device."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.const import CONF_HOST
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import ThinkLabError, base_url
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ThinkLabCoordinator


class ThinkLabEntity(CoordinatorEntity[ThinkLabCoordinator]):
    """An entity of the board."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ThinkLabCoordinator, key: str) -> None:
        """Derive the unique ID from the board's MAC; one device per board."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        data = coordinator.data
        mac = format_mac(data["mac"])
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=str(data.get("build", "")).removeprefix("v") or None,
            configuration_url=base_url(entry.data[CONF_HOST]),
        )

    @property
    def data(self) -> dict:
        """The latest status.json."""
        return self.coordinator.data

    async def _act(self, call: Awaitable[None]) -> None:
        """Run a command on the board, then read the status again."""
        try:
            await call
        except ThinkLabError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_request_refresh()
