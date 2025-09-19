"""Dataclasses used across the game."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Sequence


@dataclass(frozen=True)
class PlayerProfile:
    identifier: str
    display_name: str
    avatar_filename: str

    def resolve_avatar_path(self, assets_dir: Path) -> Path:
        return assets_dir / "images" / self.avatar_filename


@dataclass
class TestConfig:
    tables: List[int]
    question_count: int
    time_limit_seconds: int


@dataclass
class TestResult:
    profile_id: str
    profile_name: str
    tables: Sequence[int]
    question_count: int
    answered: int
    correct: int
    incorrect: int
    time_limit_seconds: int
    elapsed_seconds: float
    timestamp: datetime

    def to_serialisable(self) -> dict:
        data = asdict(self)
        data.update(
            {
                "tables": list(self.tables),
                "timestamp": self.timestamp.isoformat(),
            }
        )
        return data

    @property
    def accuracy(self) -> float:
        return (self.correct / self.answered) if self.answered else 0.0

    @property
    def remaining_seconds(self) -> float:
        return max(self.time_limit_seconds - self.elapsed_seconds, 0.0)
