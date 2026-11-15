"""Shared fixtures: a mocked board answering with a recorded status.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thinklab_display.const import DOMAIN

HOST = "192.168.1.50"
URL = f"http://{HOST}"
LOGIN = {CONF_USERNAME: "admin", CONF_PASSWORD: "secret"}
MAC = "aa:bb:cc:dd:ee:01"


def status(**changes: Any) -> dict[str, Any]:
    """Return the recorded status.json, with changes."""
    data = json.loads((Path(__file__).parent / "fixtures" / "status.json").read_text())
    data.update(changes)
    return data


def mock_board(mock: AiohttpClientMocker, **changes: Any) -> None:
    """Answer status.json and accept every command."""
    mock.clear_requests()
    mock.get(f"{URL}/status.json", json=status(**changes))
    for path in ("/api/fan/auto", "/api/esp/reboot", "/api/ui/page/next", "/api/ui/page/update"):
        mock.post(f"{URL}{path}", status=204)
    for pct in range(101):
        mock.post(f"{URL}/api/fan/manual/{pct}", status=204)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    return


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add a configured board."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ThinkLab-esp32",
        unique_id=MAC,
        data={CONF_HOST: HOST} | LOGIN,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_board(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> MockConfigEntry:
    """Set up the board in Home Assistant."""
    mock_board(aioclient_mock)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
