"""Diagnostics: the last status.json, without the login."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import ThinkLabConfigEntry

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, "ssid"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ThinkLabConfigEntry
) -> dict[str, Any]:
    """Return the entry and the board's last answer."""
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "status": async_redact_data(entry.runtime_data.data or {}, TO_REDACT),
    }
