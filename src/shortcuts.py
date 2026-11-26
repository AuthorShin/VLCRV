"""Persistence for the configurable VLC commands."""

import json
import logging
import os
from threading import Lock

from src.settings import DEFAULT_SHORTCUTS

log = logging.getLogger(__name__)


class Shortcuts:
    def __init__(self, source: str):
        self.source = source
        self._lock = Lock()
        self.persistent = True
        self.data = self._load()

    def _load(self) -> dict:
        data = {}
        try:
            with open(self.source, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            pass

        # Fill in anything missing (new keys after an upgrade, corrupt file...).
        for key, value in DEFAULT_SHORTCUTS.items():
            data.setdefault(key, value)
        self._save(data)
        return data

    def _save(self, data: dict) -> None:
        """Write atomically; fall back to in-memory config if storage is read-only."""
        tmp = None
        try:
            parent = os.path.dirname(self.source) or "."
            os.makedirs(parent, exist_ok=True)
            tmp = f"{self.source}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.source)
            self.persistent = True
        except OSError as exc:
            # This happens if the mounted volume is owned by root while the
            # distroless container runs as UID 65532. Never crash the app for it.
            self.persistent = False
            log.warning(
                "Config path %s is not writable (%s). Running with in-memory "
                "commands only. Fix the volume ownership with: "
                "docker run --rm -v <volume>:/data alpine:3 chown -R 65532:65532 /data",
                self.source,
                exc,
            )
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def get_all(self) -> dict:
        with self._lock:
            return dict(self.data)

    def get(self, key: str):
        return self.get_all().get(key)

    def update(self, data: dict) -> None:
        with self._lock:
            merged = dict(self.data)
            merged.update({k: str(v) for k, v in data.items()})
            self._save(merged)
            self.data = merged

    def reset(self) -> None:
        self.update(DEFAULT_SHORTCUTS)
