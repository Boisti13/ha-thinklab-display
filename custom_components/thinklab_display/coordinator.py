"""Polls the board's status.json."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ThinkLabAuthError, ThinkLabClient, ThinkLabError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type ThinkLabConfigEntry = ConfigEntry[ThinkLabCoordinator]


class ThinkLabCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One board, one poll."""

    config_entry: ThinkLabConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ThinkLabConfigEntry, client: ThinkLabClient):
        """Set the poll interval from the options."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.status()
        except ThinkLabAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ThinkLabError as err:
            raise UpdateFailed(f"Board not reachable: {err}") from err
