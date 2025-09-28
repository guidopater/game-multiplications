"""Persistent storage for game-wide settings."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .models import GameSettings


def _is_web_runtime() -> bool:
    return sys.platform == "emscripten" or bool(os.environ.get("PYGBAG"))


class SettingsStore:
    """Load and persist settings such as audio toggles and defaults."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> GameSettings:
        if _is_web_runtime():
            try:
                # pygbag exposes browser localStorage via js module
                import js  # type: ignore

                raw = js.localStorage.getItem("settings")
                if raw is None:
                    return GameSettings()
                payload = json.loads(str(raw))
                return GameSettings.from_dict(payload)
            except Exception:
                return GameSettings()
        else:
            if not self.path.exists():
                return GameSettings()
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return GameSettings()
            return GameSettings.from_dict(payload)

    def save(self, settings: GameSettings) -> None:
        if _is_web_runtime():
            try:
                import js  # type: ignore

                js.localStorage.setItem("settings", json.dumps(settings.to_dict()))
            except Exception:
                # Swallow errors in web environments to avoid crashes.
                pass
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")


__all__ = ["SettingsStore"]
