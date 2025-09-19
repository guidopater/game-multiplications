"""Persistence helpers for player progress."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .models import TestResult


class ScoreRepository:
    """Loads and saves per-profile test results."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: Dict[str, List[dict]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Start fresh if the file is corrupt.
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def record_test(self, result: TestResult) -> None:
        profile_results = self._data.setdefault(result.profile_id, [])
        profile_results.append(result.to_serialisable())
        self.save()

    def get_test_results(self, profile_id: str) -> List[dict]:
        return list(self._data.get(profile_id, []))
