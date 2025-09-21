"""Locale loading and translation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    keys = set(base) | set(override)
    for key in keys:
        if key in base and key in override:
            base_val = base[key]
            override_val = override[key]
            if isinstance(base_val, dict) and isinstance(override_val, dict):
                result[key] = _deep_merge(base_val, override_val)
            else:
                result[key] = override_val
        elif key in override:
            result[key] = override[key]
        else:
            result[key] = base[key]
    return result


class Translator:
    """Loads locale files and provides access to translated strings."""

    def __init__(self, base_path: Path, language: str, default_language: str = "nl") -> None:
        self.base_path = base_path
        self.default_language = default_language
        self.language = language
        self._data: Dict[str, Any] = {}
        self.set_language(language)

    def set_language(self, language: str) -> None:
        self.language = language
        default_data = self._load_file(self.default_language)
        if language == self.default_language:
            self._data = default_data
        else:
            selected_data = self._load_file(language)
            self._data = _deep_merge(default_data, selected_data)

    def gettext(self, key: str, **kwargs: Any) -> str:
        value = self._resolve(key)
        if isinstance(value, str):
            if kwargs:
                try:
                    return value.format(**kwargs)
                except (KeyError, ValueError):
                    return value
            return value
        return key

    def get_list(self, key: str) -> List[str]:
        value = self._resolve(key)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [value]
        return []

    # Aliases --------------------------------------------------------
    __call__ = gettext

    # Internal helpers ----------------------------------------------
    def _load_file(self, language: str) -> Dict[str, Any]:
        path = self.base_path / f"{language}.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _resolve(self, key: str) -> Any:
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return key
        return node


__all__ = ["Translator"]
