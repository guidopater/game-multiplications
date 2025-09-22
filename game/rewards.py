"""Shared helpers for coin reward calculations."""

from __future__ import annotations

from typing import Iterable

INCORRECT_PENALTY: int = 2
_TIME_BONUS_SCALE: int = 8
_SPEED_BONUS: dict[str, int] = {
    "Slak": 0,
    "Schildpad": 2,
    "Haas": 4,
    "Cheeta": 6,
}


def per_question_reward(table: int) -> int:
    """Return the coin reward for a correct answer on a given table."""

    return 2 + table // 4


def incorrect_penalty() -> int:
    """Return the penalty applied when a question is answered incorrectly."""

    return INCORRECT_PENALTY


def time_bonus_from_ratio(ratio: float) -> int:
    """Return the time bonus for the fraction of time left (0.0–1.0)."""

    ratio = max(0.0, min(1.0, ratio))
    return int(round(ratio * _TIME_BONUS_SCALE))


def max_time_bonus() -> int:
    """Return the maximum achievable time bonus."""

    return _TIME_BONUS_SCALE


def speed_bonus(label: str) -> int:
    """Return the static bonus associated with the chosen speed preset."""

    return _SPEED_BONUS.get(label, 0)


def estimate_max_reward(tables: Iterable[int], question_count: int, speed_label: str) -> int:
    """Estimate the maximum coins a player could earn with perfect play."""

    table_list = list(tables)
    if not table_list or question_count <= 0:
        return 0

    average_reward = sum(per_question_reward(table) for table in table_list) / len(table_list)
    total = int(round(average_reward * question_count))
    total += max(0, max_time_bonus() + speed_bonus(speed_label))
    return total


__all__ = [
    "INCORRECT_PENALTY",
    "per_question_reward",
    "incorrect_penalty",
    "time_bonus_from_ratio",
    "max_time_bonus",
    "speed_bonus",
    "estimate_max_reward",
]
