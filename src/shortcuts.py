"""Persistence for the configurable VLC commands."""

import json
import os
from threading import Lock

from src.settings import DEFAULT_SHORTCUTS


class Shortcuts:
    def __init__(self, source: str):
        self.source = source
        self._lock = Lock()
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
        parent = os.path.dirname(self.source) or "."
        os.makedirs(parent, exist_ok=True)
        tmp = f"{self.source}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.source)

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
