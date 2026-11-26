"""Smoke test: exercise the web app against a fake VLC HTTP interface.

No real VLC is required. Run from the repo root with:
    python tests/smoke_test.py
"""

import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["VLC_HOST"] = "127.0.0.1"
os.environ["VLC_HTTP_PORT"] = "18080"
os.environ["VLC_HTTP_PASSWORD"] = "secret"
os.environ["CONFIG_PATH"] = os.path.join(ROOT, "data", "db.json")

requests_seen = []

STATUS_XML = (
    b'<?xml version="1.0"?><root><state>playing</state><volume>128</volume>'
    b"<time>42</time><length>120</length><fullscreen>0</fullscreen></root>"
)


class FakeVLC(BaseHTTPRequestHandler):
    def do_GET(self):
        requests_seen.append((self.path, self.headers.get("Authorization")))
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(STATUS_XML)))
        self.end_headers()
        self.wfile.write(STATUS_XML)

    def log_message(self, *args):
        pass


def main() -> None:
    server = HTTPServer(("127.0.0.1", 18080), FakeVLC)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        from fastapi.testclient import TestClient

        from src.app import app
        from src.shortcuts import Shortcuts
        from src.vlc_client import to_params

        # A read-only config path must not crash startup (root-owned volume).
        fallback = Shortcuts("/proc/forbidden/db.json")
        assert fallback.get("play_pause") == "pl_pause"
        assert fallback.persistent is False

        assert to_params("seek|+10s") == {"command": "seek", "val": "+10s"}
        assert to_params("pl_pause") == {"command": "pl_pause"}

        with TestClient(app) as client:
            home = client.get("/")
            assert home.status_code == 200
            assert "/static/style.css" in home.text
            assert 'name="color-scheme"' in home.text
            assert 'id="icon-play"' in home.text
            assert 'id="icon-pause"' in home.text
            assert "refreshStatus" in home.text
            assert "cdn.tailwindcss.com" not in home.text
            css = client.get("/static/style.css")
            assert css.status_code == 200
            assert ".hidden { display: none; }" in css.text
            assert client.get("/help").status_code == 200
            assert client.get("/favicon.ico").status_code == 204
            config = client.get("/config")
            assert config.status_code == 200
            assert "cdn.tailwindcss.com" not in config.text
            assert "fonts.googleapis.com" not in config.text
            assert "vlchelp.com" not in config.text
            assert client.get("/health").json()["status"] == "ok"
            assert client.get("/action/unknown").status_code == 404

            for button in (
                "play_pause",
                "volume_up",
                "volume_down",
                "move_forward",
                "move_back",
                "mute",
                "fullscreen",
                "quit",
            ):
                response = client.get(f"/action/{button}")
                assert response.status_code == 200, (button, response.text)

            assert client.get("/status").json()["state"] == "playing"

        paths = [path for path, _ in requests_seen]
        assert any("command=seek&val=%2B10s" in p for p in paths), paths
        assert any("command=key&val=vol-mute" in p for p in paths), paths
        assert any(auth == "Basic OnNlY3JldA==" for _, auth in requests_seen)
        print(f"smoke test passed ({len(paths)} VLC requests verified)")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
