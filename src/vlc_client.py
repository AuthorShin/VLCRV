"""Small client for VLC's built-in HTTP (Lua) interface.

VLC exposes ``/requests/status.xml`` on the machine that plays the video.
Commands are passed as query parameters, e.g.::

    GET http://Your-PC:8080/requests/status.xml?command=pl_pause
    GET http://Your-PC:8080/requests/status.xml?command=seek&val=%2B10s

Authentication is HTTP Basic with an empty username and the password set in
VLC's Lua HTTP preferences.
"""

import logging
import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl

import requests

from src import settings

log = logging.getLogger(__name__)


def to_params(raw: str) -> dict:
    """Convert a configured command string into VLC query parameters.

    Accepted formats::

        "pl_pause"                    -> command=pl_pause
        "key|vol-mute"                -> command=key&val=vol-mute
        "seek|+10s"                   -> command=seek&val=+10s
        "command=seek&val=+10s"       -> legacy query-string form
    """
    raw = (raw or "").strip()
    if not raw:
        return {}

    if raw.startswith("command="):
        # In VLC values '+' is literal (e.g. "+10s"), not a URL-encoded space.
        return dict(parse_qsl(raw.replace("+", "%2B"), keep_blank_values=True))

    command, _, value = raw.partition("|")
    params = {"command": command.strip()}
    if value.strip():
        params["val"] = value.strip()
    return params


class VLCClient:
    def __init__(self, host=None, port=None, password=None, timeout=None):
        self.host = host or settings.VLC_HOST
        self.port = port or settings.VLC_HTTP_PORT
        self.password = (
            settings.VLC_HTTP_PASSWORD if password is None else password
        )
        self.timeout = timeout or settings.VLC_TIMEOUT
        self.base_url = f"http://{self.host}:{self.port}"
        self.session = requests.Session()
        # VLC's HTTP interface uses an empty username and the Lua HTTP password.
        self.session.auth = ("", self.password)

    def _get(self, path: str, params: dict | None = None):
        return self.session.get(
            f"{self.base_url}{path}",
            params=params or {},
            timeout=self.timeout,
        )

    def send(self, raw_command: str) -> tuple[bool, str | None]:
        """Send one configured command. Returns (success, error_message)."""
        params = to_params(raw_command)
        if not params.get("command"):
            return False, "No command configured for this button"

        try:
            response = self._get("/requests/status.xml", params)
        except requests.Timeout:
            message = (
                f"Timed out reaching VLC at {self.base_url}. On the VLC PC: "
                "check the Web interface is enabled, 'HTTP server address' is "
                f"empty/0.0.0.0, and the firewall allows TCP {self.port}."
            )
            log.warning(message)
            return False, message
        except requests.ConnectionRefused:
            message = (
                f"Connection refused by {self.base_url}. Is VLC running with "
                "its Web interface enabled?"
            )
            log.warning(message)
            return False, message
        except requests.RequestException as exc:
            log.warning("Cannot reach VLC at %s: %s", self.base_url, exc)
            return False, f"Cannot reach VLC at {self.base_url} ({type(exc).__name__})"

        if response.status_code == 401:
            return False, "VLC rejected the password (check VLC_HTTP_PASSWORD)"
        if not response.ok:
            return False, f"VLC returned HTTP {response.status_code}"
        return True, None

    def status(self) -> dict:
        """Return a small, human-readable snapshot of VLC's state."""
        try:
            response = self._get("/requests/status.xml")
        except requests.RequestException as exc:
            return {"reachable": False, "error": str(exc)}

        if response.status_code == 401:
            return {"reachable": False, "error": "Invalid VLC_HTTP_PASSWORD"}
        if not response.ok:
            return {"reachable": False, "error": f"HTTP {response.status_code}"}

        try:
            root = ET.fromstring(response.content)

            def field(tag: str, default: str = "") -> str:
                node = root.find(tag)
                return node.text if node is not None and node.text is not None else default

            return {
                "reachable": True,
                "state": field("state", "unknown"),
                "volume": field("volume"),
                "time": field("time"),
                "length": field("length"),
                "fullscreen": field("fullscreen"),
            }
        except ET.ParseError as exc:
            return {"reachable": True, "error": f"Invalid XML from VLC: {exc}"}
