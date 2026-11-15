"""Entities: values from status.json, and the commands they send."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import URL, mock_board, status


def posts(mock: AiohttpClientMocker) -> list[str]:
    """Paths of the POSTs sent so far."""
    return [str(url.path) for method, url, *_ in mock.mock_calls if method == "POST"]


async def test_values(hass: HomeAssistant, setup_board: MockConfigEntry):
    assert hass.states.get("sensor.thinklab_esp32_case_temperature").state == "34.5"
    assert hass.states.get("sensor.thinklab_esp32_fan_1_speed").state == "720"
    assert hass.states.get("sensor.thinklab_esp32_fan_duty").state == "14"
    assert hass.states.get("sensor.thinklab_esp32_fan_curve_demand").state == "13.7"
    assert hass.states.get("sensor.thinklab_esp32_host_answer_age").state == "20"
    assert hass.states.get("sensor.thinklab_esp32_wi_fi_signal").state == "-52"
    assert hass.states.get("sensor.thinklab_esp32_last_restart").state not in ("unknown", None)
    assert hass.states.get("binary_sensor.thinklab_esp32_host_link").state == "off"
    assert hass.states.get("binary_sensor.thinklab_esp32_fan").state == "on"
    assert hass.states.get("binary_sensor.thinklab_esp32_fan_stalled").state == "off"
    assert hass.states.get("sensor.thinklab_esp32_fan_2_speed").state == "705"
    assert hass.states.get("sensor.thinklab_esp32_fan_minimum_duty").state == "8"
    assert hass.states.get("sensor.thinklab_esp32_fan_stall_kicks") is None  # disabled by default
    assert hass.states.get("select.thinklab_esp32_fan_mode").state == "auto"
    assert hass.states.get("number.thinklab_esp32_fan_duty_setting").state == "14"
    assert hass.states.get("sensor.thinklab_esp32_parse_errors") is None  # disabled by default


async def test_no_tach_reading(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
):
    mock_board(aioclient_mock, fan_rpm=-1, fan2_rpm=-1, fan_pct=-1, case_c=None)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.thinklab_esp32_fan_1_speed").state == "unknown"
    assert hass.states.get("sensor.thinklab_esp32_fan_2_speed").state == "unknown"
    assert hass.states.get("number.thinklab_esp32_fan_duty_setting").state == "unknown"
    assert hass.states.get("sensor.thinklab_esp32_case_temperature").state == "unknown"


async def test_number_sets_manual(
    hass: HomeAssistant, setup_board: MockConfigEntry, aioclient_mock: AiohttpClientMocker
):
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.thinklab_esp32_fan_duty_setting", "value": 42},
        blocking=True,
    )
    assert "/api/fan/manual/42" in posts(aioclient_mock)


async def test_select(
    hass: HomeAssistant, setup_board: MockConfigEntry, aioclient_mock: AiohttpClientMocker
):
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.thinklab_esp32_fan_mode", "option": "manual"},
        blocking=True,
    )
    assert "/api/fan/manual/14" in posts(aioclient_mock)  # keeps the current duty
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.thinklab_esp32_fan_mode", "option": "auto"},
        blocking=True,
    )
    assert "/api/fan/auto" in posts(aioclient_mock)


@pytest.mark.parametrize(
    ("entity_id", "path"),
    [
        ("button.thinklab_esp32_next_page", "/api/ui/page/next"),
        ("button.thinklab_esp32_redraw_page", "/api/ui/page/update"),
        ("button.thinklab_esp32_restart", "/api/esp/reboot"),
    ],
)
async def test_buttons(
    hass: HomeAssistant,
    setup_board: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    entity_id: str,
    path: str,
):
    await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
    assert path in posts(aioclient_mock)


async def test_command_error(
    hass: HomeAssistant, setup_board: MockConfigEntry, aioclient_mock: AiohttpClientMocker
):
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{URL}/api/ui/page/next", status=500)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.thinklab_esp32_next_page"}, blocking=True
        )


async def test_board_offline_then_back(
    hass: HomeAssistant,
    setup_board: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
):
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/status.json", exc=TimeoutError())
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.thinklab_esp32_case_temperature").state == STATE_UNAVAILABLE

    mock_board(aioclient_mock, case_c=36.0)
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.thinklab_esp32_case_temperature").state == "36.0"


async def test_wrong_login_starts_reauth(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
):
    aioclient_mock.get(f"{URL}/status.json", status=401)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)


async def test_unload(hass: HomeAssistant, setup_board: MockConfigEntry):
    assert await hass.config_entries.async_unload(setup_board.entry_id)
    assert setup_board.state is ConfigEntryState.NOT_LOADED


async def test_firmware_without_fan2_fields(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
):
    new_keys = ("fan2", "fan_min", "fan_stall")
    old = {k: v for k, v in status(build="v0.3.2").items() if not k.startswith(new_keys)}
    aioclient_mock.get(f"{URL}/status.json", json=old)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.thinklab_esp32_fan_2_speed").state == "unknown"
    assert hass.states.get("binary_sensor.thinklab_esp32_fan_stalled").state == "unknown"
