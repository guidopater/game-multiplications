"""Helpers for avatar rendering and styling."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import pygame

Color = Tuple[int, int, int]
Gradient = Tuple[Color, Color]


def load_avatar_surface(path: Path, size: int | None = None, corner_radius: int | None = None) -> pygame.Surface | None:
    """Load an avatar image, optionally resizing and rounding the corners."""

    if not path.exists():
        return None
    try:
        surface = pygame.image.load(str(path)).convert_alpha()
    except pygame.error:
        return None

    if size is not None:
        surface = pygame.transform.smoothscale(surface, (size, size))

    if corner_radius and corner_radius > 0:
        surface = apply_round_corners(surface, corner_radius)

    return surface


def apply_round_corners(surface: pygame.Surface, radius: int) -> pygame.Surface:
    """Return a copy of ``surface`` with rounded corners using the given radius."""

    radius = max(0, radius)
    mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    rounded = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    rounded.blit(surface, (0, 0))
    rounded.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return rounded


def gradient_from_color(color: Color) -> Gradient:
    """Generate a warm gradient based on one colour."""

    top = _blend(color, (255, 255, 255), 0.45)
    bottom = _blend(color, _rotate_hue(color, 25), 0.25)
    bottom = _blend(bottom, (0, 0, 0), 0.25)
    return top, bottom


def gradient_from_avatar(path: Path, fallback: Gradient) -> Gradient:
    """Derive a lively gradient from the avatar artwork."""

    surface = load_avatar_surface(path, size=None)
    if surface is None:
        return fallback

    palette = _sample_palette(surface, sample_size=16)
    if not palette:
        return fallback

    accent = palette[0]
    secondary = _find_complementary_colour(palette, accent)

    top = _blend(accent, (255, 255, 255), 0.45)
    bottom_seed = _blend(secondary, accent, 0.25)
    bottom_seed = _blend(bottom_seed, _rotate_hue(accent, 30), 0.2)
    bottom = _blend(bottom_seed, (0, 0, 0), 0.25)

    return top, bottom


def _blend(color: Color, target: Color, factor: float) -> Color:
    factor = max(0.0, min(1.0, factor))
    blended = [
        int(max(0, min(255, round(component + (target[i] - component) * factor))))
        for i, component in enumerate(color)
    ]
    return blended[0], blended[1], blended[2]


def _sample_palette(surface: pygame.Surface, sample_size: int = 16) -> list[Color]:
    small = pygame.transform.smoothscale(surface, (sample_size, sample_size))
    pixels: list[tuple[float, float, float, float, Color]] = []
    for x in range(sample_size):
        for y in range(sample_size):
            r, g, b, a = small.get_at((x, y))
            if a < 64:
                continue
            h, s, v = _rgb_to_hsv(r, g, b)
            if s < 0.25 or v < 0.2:
                continue
            score = s * 0.7 + v * 0.3
            pixels.append((score, s, v, h, (int(r), int(g), int(b))))

    if not pixels:
        return []

    pixels.sort(key=lambda entry: entry[0], reverse=True)
    colours = [entry[4] for entry in pixels]
    return colours


def _find_complementary_colour(palette: Iterable[Color], accent: Color) -> Color:
    accent_h, accent_s, accent_v = _rgb_to_hsv(*accent)
    chosen: Color | None = None
    best_diff = 0.0
    for colour in palette:
        if colour == accent:
            continue
        h, s, v = _rgb_to_hsv(*colour)
        hue_diff = abs(h - accent_h)
        hue_diff = min(hue_diff, 1.0 - hue_diff)  # wrap around circle
        diff = hue_diff + abs(v - accent_v) * 0.25
        if diff > best_diff and hue_diff > 0.08:
            best_diff = diff
            chosen = colour

    if chosen is None:
        chosen = _rotate_hue(accent, 40)
    return chosen


def _rotate_hue(color: Color, degrees: float) -> Color:
    h, s, v = _rgb_to_hsv(*color)
    h = (h + degrees / 360.0) % 1.0
    r, g, b = _hsv_to_rgb(h, s, v)
    return int(r), int(g), int(b)


def _rgb_to_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    return tuple(value / 255.0 for value in pygame.color.Color(r, g, b).hsva[:3])  # type: ignore[return-value]


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    color = pygame.color.Color(0)
    color.hsva = (h * 360.0, s * 100.0, v * 100.0, 100.0)
    return color.r, color.g, color.b


__all__ = [
    "load_avatar_surface",
    "apply_round_corners",
    "gradient_from_color",
    "gradient_from_avatar",
]
