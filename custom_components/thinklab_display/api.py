"""Small client for the board's web API (HTTP basic auth)."""

from __future__ import annotations

import base64
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=10)


class ThinkLabError(Exception):
    """Base error."""


class ThinkLabConnectionError(ThinkLabError):
    """The board can't be reached."""


class ThinkLabAuthError(ThinkLabError):
    """Wrong user name or password."""


class ThinkLabApiError(ThinkLabError):
    """The board answered, but not as expected."""


def base_url(host: str) -> str:
    """Turn what the user typed into http://host[:port]."""
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return host


class ThinkLabClient:
    """Talks to one board."""

    def __init__(self, session: aiohttp.ClientSession, host: str, username: str, password: str):
        """Keep the session, address and login."""
        self._session = session
        self._base = base_url(host)
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._headers = {"Authorization": f"Basic {token}"}

    async def _request(self, method: str, path: str) -> Any:
        try:
            async with self._session.request(
                method, f"{self._base}{path}", headers=self._headers, timeout=TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise ThinkLabAuthError("login refused")
                if resp.status >= 400:
                    raise ThinkLabApiError(f"{method} {path} -> HTTP {resp.status}")
                if method == "GET":
                    try:
                        return await resp.json(content_type=None)
                    except ValueError as err:
                        raise ThinkLabApiError(f"{path}: not JSON") from err
                return None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ThinkLabConnectionError(str(err) or type(err).__name__) from err

    async def status(self) -> dict[str, Any]:
        """Read /status.json."""
        data = await self._request("GET", "/status.json")
        if not isinstance(data, dict):
            raise ThinkLabApiError("status.json is not an object")
        return data

    async def set_fan_manual(self, percent: int) -> None:
        """Manual fan duty 0..100 (the board ends it after an hour or at 50 °C)."""
        await self._request("POST", f"/api/fan/manual/{int(percent)}")

    async def set_fan_auto(self) -> None:
        """Back to the temperature curve."""
        await self._request("POST", "/api/fan/auto")

    async def reboot(self) -> None:
        """Restart the board."""
        await self._request("POST", "/api/esp/reboot")

    async def next_page(self) -> None:
        """Show the next e-paper page."""
        await self._request("POST", "/api/ui/page/next")

    async def refresh_page(self) -> None:
        """Redraw the current e-paper page."""
        await self._request("POST", "/api/ui/page/update")
