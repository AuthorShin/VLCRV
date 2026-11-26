"""Configuration for the VLC remote control web app.

Every value can be overridden with an environment variable so the same image
can be deployed without a rebuild. The defaults match the intended setup:
this app runs in Docker on a VM and controls VLC on the PC named ``Your-PC``.
"""

import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


# --- Web server -----------------------------------------------------------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = _env_int("PORT", 8004)
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

# Optional override for the URL printed in the logs and encoded in the QR code.
# Useful behind a reverse proxy or when the VM is reached through a DNS name.
PUBLIC_URL = os.getenv("PUBLIC_URL", "").strip()

# --- VLC HTTP interface (on the PC that is actually playing the video) ----
VLC_HOST = os.getenv("VLC_HOST", "Your-PC")
VLC_HTTP_PORT = _env_int("VLC_HTTP_PORT", 8080)
VLC_HTTP_PASSWORD = os.getenv("VLC_HTTP_PASSWORD", "")
VLC_TIMEOUT = _env_float("VLC_TIMEOUT", "3")  # seconds

# --- Persistent configuration ---------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.getenv("CONFIG_PATH", os.path.join(_BASE_DIR, "data", "db.json"))

# Each value is a VLC HTTP command sent to /requests/status.xml.
# Format: "command" or "command|val" (see src/vlc_client.py).
DEFAULT_SHORTCUTS = {
    "play_pause": "pl_pause",
    "fullscreen": "key|toggle-fullscreen",
    "mute": "key|vol-mute",
    "volume_up": "volume|+10",
    "volume_down": "volume|-10",
    "move_forward": "seek|+10s",
    "move_back": "seek|-10s",
    "quit": "key|quit",
    # VLC must already be running on Your-PC; this optional command is sent
    # once at startup (e.g. "pl_play"). Leave empty to do nothing.
    "open_vlc": "",
}
