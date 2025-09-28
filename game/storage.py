"""Persistence helpers for player progress."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

from .models import TestResult


def _is_web_runtime() -> bool:
    return sys.platform == "emscripten" or bool(os.environ.get("PYGBAG"))


class ScoreRepository:
    """Loads and saves per-profile test results."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: Dict[str, List[dict]] = {}
        self._load()

    def _load(self) -> None:
        if _is_web_runtime():
            try:
                import js  # type: ignore

                raw = js.localStorage.getItem("scores")
                if raw is None:
                    self._data = {}
                else:
                    self._data = json.loads(str(raw))
            except Exception:
                self._data = {}
        else:
            if self.path.exists():
                try:
                    self._data = json.loads(self.path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    # Start fresh if the file is corrupt.
                    self._data = {}
            else:
                self._data = {}

    def save(self) -> None:
        if _is_web_runtime():
            try:
                import js  # type: ignore

                js.localStorage.setItem("scores", json.dumps(self._data))
            except Exception:
                pass
        else:
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def record_test(self, result: TestResult) -> None:
        profile_results = self._data.setdefault(result.profile_id, [])
        profile_results.append(result.to_serialisable())
        self.save()

    def get_test_results(self, profile_id: str) -> List[dict]:
        return list(self._data.get(profile_id, []))

    def all_scores(self) -> Dict[str, List[dict]]:
        return json.loads(json.dumps(self._data))

    def clear_profile(self, profile_id: str) -> None:
        if profile_id in self._data:
            del self._data[profile_id]
            self.save()

    def clear_all(self) -> None:
        self._data = {}
        self.save()
