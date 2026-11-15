"""Config flow: address + web login, discovery over mDNS, re-auth, reconfigure, options."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
import voluptuous as vol

from .api import ThinkLabApiError, ThinkLabAuthError, ThinkLabClient, ThinkLabConnectionError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_FIRMWARE,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_USERNAME = "admin"
PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _login_schema(username: str = DEFAULT_USERNAME) -> dict:
    return {
        vol.Required(CONF_USERNAME, default=username): str,
        vol.Required(CONF_PASSWORD): PASSWORD,
    }


class ThinkLabConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a board."""

    VERSION = 1

    def __init__(self) -> None:
        """Nothing discovered yet."""
        self._host: str | None = None
        self._name: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> ThinkLabOptionsFlow:
        """Options: poll interval."""
        return ThinkLabOptionsFlow()

    async def _probe(self, host: str, username: str, password: str) -> tuple[dict, dict[str, str]]:
        """Read status.json once; return it and any form errors."""
        client = ThinkLabClient(async_get_clientsession(self.hass), host, username, password)
        try:
            data = await client.status()
        except ThinkLabAuthError:
            return {}, {"base": "invalid_auth"}
        except ThinkLabConnectionError:
            return {}, {"base": "cannot_connect"}
        except ThinkLabApiError:
            return {}, {"base": "not_a_board"}
        except Exception:
            _LOGGER.exception("Unexpected error talking to %s", host)
            return {}, {"base": "unknown"}
        build = str(data.get("build", "0")).removeprefix("v")
        if "mac" not in data or AwesomeVersion(build) < AwesomeVersion(MIN_FIRMWARE):
            return data, {"base": "firmware_too_old"}
        return data, {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Address and login typed in by hand."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._probe(
                user_input[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                await self.async_set_unique_id(format_mac(data["mac"]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(
                    title=data.get("hostname") or "ThinkLab display", data=user_input
                )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=(user_input or {}).get(CONF_HOST, self._host or "")
                ): str
            }
            | _login_schema((user_input or {}).get(CONF_USERNAME, DEFAULT_USERNAME))
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Found by its mDNS announcement (the board announces itself for OTA)."""
        host = str(discovery_info.ip_address)
        self._async_abort_entries_match({CONF_HOST: host})
        self._host = host
        self._name = discovery_info.name.split(".", 1)[0]
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the login of the discovered board."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._probe(
                self._host, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                await self.async_set_unique_id(format_mac(data["mac"]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
                return self.async_create_entry(
                    title=data.get("hostname") or self._name or "ThinkLab display",
                    data={CONF_HOST: self._host} | user_input,
                )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(_login_schema()),
            description_placeholders={"name": self._name or "", "host": self._host or ""},
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start re-auth: the board refused the stored login."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new login."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._probe(
                entry.data[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                await self.async_set_unique_id(format_mac(data["mac"]))
                self._abort_if_unique_id_mismatch(reason="wrong_board")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(_login_schema(entry.data[CONF_USERNAME])),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change address or login."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = await self._probe(
                user_input[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                await self.async_set_unique_id(format_mac(data["mac"]))
                self._abort_if_unique_id_mismatch(reason="wrong_board")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        schema = vol.Schema(
            {vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str}
            | _login_schema(entry.data[CONF_USERNAME])
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


class ThinkLabOptionsFlow(OptionsFlowWithReload):
    """How often to poll."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """One field."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=5,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
