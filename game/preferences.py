"""Persistent storage for game-wide settings."""

from __future__ import annotations

import json
from pathlib import Path

from .models import GameSettings


class SettingsStore:
    """Load and persist settings such as audio toggles and defaults."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> GameSettings:
        if not self.path.exists():
            return GameSettings()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return GameSettings()
        return GameSettings.from_dict(payload)

    def save(self, settings: GameSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")


__all__ = ["SettingsStore"]

