"""Dataclasses used across the game."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field, replace
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

    @classmethod
    def from_serialisable(cls, payload: dict) -> "TestResult":
        """Reconstruct a test result saved via ``to_serialisable``."""

        def _as_int(value: object, default: int = 0) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _as_float(value: object, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        tables_raw = payload.get("tables", [])
        tables: List[int] = []
        if isinstance(tables_raw, list):
            for item in tables_raw:
                try:
                    tables.append(int(item))
                except (TypeError, ValueError):
                    continue

        timestamp_value = payload.get("timestamp")
        if isinstance(timestamp_value, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_value)
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        raw_table_stats = payload.get("table_stats", {})
        table_stats: Dict[int, Dict[str, float]] = {}
        if isinstance(raw_table_stats, dict):
            for key, stats in raw_table_stats.items():
                try:
                    table_key = int(key)
                except (TypeError, ValueError):
                    continue
                if not isinstance(stats, dict):
                    continue
                table_stats[table_key] = {
                    "questions": _as_float(stats.get("questions"), 0.0),
                    "correct": _as_float(stats.get("correct"), 0.0),
                    "incorrect": _as_float(stats.get("incorrect"), 0.0),
                    "total_time": _as_float(stats.get("total_time"), 0.0),
                }

        elapsed_value = payload.get("elapsed_seconds", payload.get("elapsed", 0.0))

        return cls(
            profile_id=str(payload.get("profile_id", "")),
            profile_name=str(payload.get("profile_name", "")),
            tables=tables,
            question_count=_as_int(payload.get("question_count"), 0),
            answered=_as_int(payload.get("answered"), 0),
            correct=_as_int(payload.get("correct"), 0),
            incorrect=_as_int(payload.get("incorrect"), 0),
            time_limit_seconds=_as_int(payload.get("time_limit_seconds"), 0),
            elapsed_seconds=_as_float(elapsed_value, 0.0),
            timestamp=timestamp,
            table_stats=table_stats,
        )


@dataclass
class GameSettings:
    music_enabled: bool = True
    effects_enabled: bool = True
    default_practice_tables: List[int] = field(default_factory=lambda: list(range(1, 11)))
    default_test_tables: List[int] = field(default_factory=lambda: list(range(1, 11)))
    default_test_speed: str = "Schildpad"
    default_test_questions: int = 50
    feedback_style: str = "warm"
    language: str = "nl"
    large_text: bool = False

    def to_dict(self) -> dict:
        return {
            "music_enabled": self.music_enabled,
            "effects_enabled": self.effects_enabled,
            "default_practice_tables": list(self.default_practice_tables),
            "default_test_tables": list(self.default_test_tables),
            "default_test_speed": self.default_test_speed,
            "default_test_questions": self.default_test_questions,
            "feedback_style": self.feedback_style,
            "language": self.language,
            "large_text": self.large_text,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "GameSettings":
        if not isinstance(payload, dict):
            return cls()

        def as_bool(value: object, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            return default

        def as_int(value: object, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def as_list(value: object) -> List[int]:
            result: List[int] = []
            if isinstance(value, list):
                for item in value:
                    try:
                        result.append(int(item))
                    except (TypeError, ValueError):
                        continue
            return result or list(range(1, 11))

        return cls(
            music_enabled=as_bool(payload.get("music_enabled"), True),
            effects_enabled=as_bool(payload.get("effects_enabled"), True),
            default_practice_tables=as_list(payload.get("default_practice_tables")),
            default_test_tables=as_list(payload.get("default_test_tables")),
            default_test_speed=str(payload.get("default_test_speed", "Schildpad")),
            default_test_questions=as_int(payload.get("default_test_questions"), 50),
            feedback_style=str(payload.get("feedback_style", "warm")) or "warm",
            language=str(payload.get("language", "nl")) or "nl",
            large_text=as_bool(payload.get("large_text"), False),
        )

    def clone(self) -> "GameSettings":
        return replace(self)
