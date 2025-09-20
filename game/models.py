"""Dataclasses used across the game."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence


@dataclass
class PlayerProfile:
    identifier: str
    display_name: str
    avatar_filename: str
    coins: int = 0

    def resolve_avatar_path(self, assets_dir: Path) -> Path:
        return assets_dir / "images" / self.avatar_filename

    def to_dict(self) -> dict:
        return {
            "id": self.identifier,
            "display_name": self.display_name,
            "avatar": self.avatar_filename,
            "coins": self.coins,
        }


@dataclass
class TestConfig:
    tables: List[int]
    question_count: int
    time_limit_seconds: int


@dataclass
class PracticeConfig:
    tables: List[int]


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
    table_stats: Dict[int, Dict[str, float]]

    def to_serialisable(self) -> dict:
        data = asdict(self)
        data.update(
            {
                "tables": list(self.tables),
                "timestamp": self.timestamp.isoformat(),
                "table_stats": {
                    str(key): value for key, value in self.table_stats.items()
                },
            }
        )
        return data

    @property
    def accuracy(self) -> float:
        return (self.correct / self.answered) if self.answered else 0.0

    @property
    def remaining_seconds(self) -> float:
        return max(self.time_limit_seconds - self.elapsed_seconds, 0.0)

    def slowest_tables(self) -> List[int]:
        averages = [
            (table, stats.get("total_time", 0.0) / max(stats.get("questions", 1), 1))
            for table, stats in self.table_stats.items()
            if stats.get("questions", 0)
        ]
        averages.sort(key=lambda item: item[1], reverse=True)
        return [table for table, _ in averages[:2]]

    def tricky_tables(self) -> List[int]:
        stats = [
            (table, value.get("incorrect", 0))
            for table, value in self.table_stats.items()
        ]
        stats.sort(key=lambda item: item[1], reverse=True)
        return [table for table, incorrect in stats if incorrect > 0]
