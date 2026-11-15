"""Config flow: by hand, discovered, re-auth, reconfigure, options."""

from __future__ import annotations

from ipaddress import ip_address

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thinklab_display.const import CONF_SCAN_INTERVAL, DOMAIN

from .conftest import HOST, LOGIN, MAC, URL, mock_board, status

ZEROCONF = ZeroconfServiceInfo(
    ip_address=ip_address(HOST),
    ip_addresses=[ip_address(HOST)],
    hostname="ThinkLab-esp32.local.",
    name="ThinkLab-esp32._arduino._tcp.local.",
    port=3232,
    type="_arduino._tcp.local.",
    properties={},
)


async def test_user_creates_entry(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_board(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST} | LOGIN
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ThinkLab-esp32"
    assert result["data"] == {CONF_HOST: HOST} | LOGIN
    assert result["result"].unique_id == MAC


@pytest.mark.parametrize(
    ("answer", "error"),
    [
        ({"status": 401}, "invalid_auth"),
        ({"exc": TimeoutError()}, "cannot_connect"),
        ({"text": "<html>"}, "not_a_board"),
        ({"json": status(build="v0.3.1")}, "firmware_too_old"),
        ({"json": {k: v for k, v in status().items() if k != "mac"}}, "firmware_too_old"),
    ],
)
async def test_user_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, answer: dict, error: str
):
    aioclient_mock.get(f"{URL}/status.json", **answer)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST} | LOGIN
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # and it recovers once the board answers
    mock_board(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST} | LOGIN
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_already_configured_updates_host(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry
):
    aioclient_mock.get("http://10.0.0.9/status.json", json=status())
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.9"} | LOGIN
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "10.0.0.9"


async def test_zeroconf(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_board(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=ZEROCONF
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"
    assert result["description_placeholders"] == {"name": "ThinkLab-esp32", "host": HOST}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST} | LOGIN


async def test_zeroconf_known_host_aborts(hass: HomeAssistant, entry: MockConfigEntry):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=ZEROCONF
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry
):
    mock_board(aioclient_mock)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "new"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new"


async def test_reconfigure_other_board_refused(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry
):
    aioclient_mock.get("http://10.0.0.9/status.json", json=status(mac="AA:BB:CC:DD:EE:99"))
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.9"} | LOGIN
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_board"
    assert entry.data[CONF_HOST] == HOST


async def test_reconfigure(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry
):
    aioclient_mock.get("http://10.0.0.9/status.json", json=status())
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.9"} | LOGIN
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "10.0.0.9"


async def test_options(hass: HomeAssistant, setup_board: MockConfigEntry):
    result = await hass.config_entries.options.async_init(setup_board.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 60}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert setup_board.runtime_data.update_interval.total_seconds() == 60
