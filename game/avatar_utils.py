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
    """Generate a vivid two-tone gradient from a single colour."""

    hero = _ensure_brightness(color)
    partner = _rotate_hue(hero, 70)
    return _build_gradient(hero, partner)


def gradient_from_avatar(path: Path, fallback: Gradient) -> Gradient:
    """Derive a lively gradient from the avatar artwork."""

    surface = load_avatar_surface(path, size=None)
    if surface is None:
        return fallback

    palette = _sample_palette(surface, sample_size=16)
    if not palette:
        return fallback

    hero = _ensure_brightness(palette[0])
    partner = _find_playful_partner(palette, hero)
    return _build_gradient(hero, partner)


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

    pixels.sort(key=lambda entry: (entry[0], entry[1], entry[2]), reverse=True)
    colours = [entry[4] for entry in pixels]
    return colours


def _find_playful_partner(palette: Iterable[Color], hero: Color) -> Color:
    hero_h, hero_s, hero_v = _rgb_to_hsv(*hero)
    sectors = [
        (0.0, 1/3),
        (1/3, 2/3),
        (2/3, 1.0),
    ]
    hero_sector = next((i for i, (start, end) in enumerate(sectors) if start <= hero_h < end), 0)

    candidate: Color | None = None
    best_score = -1.0
    for colour in palette:
        if colour == hero:
            continue
        h, s, v = _rgb_to_hsv(*colour)
        if v < 0.45 or s < 0.4:
            continue
        sector = next((i for i, (start, end) in enumerate(sectors) if start <= h < end), 0)
        if sector == hero_sector:
            continue
        hue_diff = min(abs(h - hero_h), 1.0 - abs(h - hero_h))
        score = s * 0.6 + v * 0.3 + hue_diff * 0.4
        if score > best_score:
            best_score = score
            candidate = colour

    if candidate is None:
        candidate = _rotate_hue(hero, 90)
    return _ensure_brightness(candidate, min_val=0.75)


def _rotate_hue(color: Color, degrees: float) -> Color:
    h, s, v = _rgb_to_hsv(*color)
    h = (h + degrees / 360.0) % 1.0
    r, g, b = _hsv_to_rgb(h, s, v)
    return int(r), int(g), int(b)


def _rgb_to_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    color = pygame.Color(r, g, b)
    h, s, v, _ = color.hsva
    return h / 360.0, s / 100.0, v / 100.0


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    color = pygame.color.Color(0)
    color.hsva = (h * 360.0, s * 100.0, v * 100.0, 100.0)
    return color.r, color.g, color.b


def _adjust_color(color: Color, *, sat_mul: float = 1.0, val_mul: float = 1.0, val_add: float = 0.0) -> Color:
    h, s, v = _rgb_to_hsv(*color)
    s = max(0.0, min(1.0, s * sat_mul))
    v = max(0.0, min(1.0, v * val_mul + val_add))
    r, g, b = _hsv_to_rgb(h, s, v)
    return int(r), int(g), int(b)


def _ensure_brightness(color: Color, *, min_val: float = 0.75) -> Color:
    h, s, v = _rgb_to_hsv(*color)
    v = max(v, min_val)
    s = max(s, 0.65)
    r, g, b = _hsv_to_rgb(h, s, v)
    return int(r), int(g), int(b)


def _build_gradient(hero: Color, partner: Color) -> Gradient:
    top = _adjust_color(hero, sat_mul=1.45, val_mul=1.1, val_add=0.18)
    top = _blend(top, (255, 255, 255), 0.2)

    mid = _blend(hero, partner, 0.4)
    mid = _adjust_color(mid, sat_mul=1.2, val_mul=1.0, val_add=0.05)

    bottom = _adjust_color(partner, sat_mul=1.4, val_mul=1.0, val_add=0.1)
    bottom = _blend(bottom, mid, 0.35)
    bottom = _blend(bottom, (255, 255, 255), 0.05)

    return top, bottom


__all__ = [
    "load_avatar_surface",
    "apply_round_corners",
    "gradient_from_color",
    "gradient_from_avatar",
]
