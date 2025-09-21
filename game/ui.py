"""UI drawing helpers for glossy buttons."""

from __future__ import annotations

from typing import Callable, Dict, Optional

import pygame

Palette = Dict[str, tuple[int, int, int]]


def _blend(color_a: tuple[int, int, int], color_b: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    factor = max(0.0, min(1.0, factor))
    return tuple(int(color_a[i] + (color_b[i] - color_a[i]) * factor) for i in range(3))


def _darken(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return _blend(color, (0, 0, 0), amount)


_STATE_OFFSETS = {
    "rest": {"base": 12, "face": -6},
    "hover": {"base": 8, "face": -3},
    "pressed": {"base": 4, "face": 2},
}


def draw_glossy_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    palette: Palette,
    *,
    selected: bool = False,
    hover: bool = False,
    corner_radius: int | None = None,
) -> pygame.Rect:
    """Render a candy-like button with a soft depth effect and return the face rect."""

    state = "pressed" if selected else "hover" if hover else "rest"
    offsets = _STATE_OFFSETS[state]

    radius = corner_radius if corner_radius is not None else rect.height // 2
    radius = max(8, min(radius, rect.width // 2))

    base_rect = rect.inflate(-16, -8)
    base_rect = base_rect.move(0, offsets["base"])
    base_surface = pygame.Surface(base_rect.size, pygame.SRCALPHA)
    for y in range(base_surface.get_height()):
        ratio = y / max(base_surface.get_height() - 1, 1)
        color = _blend(palette["shadow"], _darken(palette["shadow"], 0.35), ratio)
        pygame.draw.line(base_surface, color, (0, y), (base_surface.get_width(), y))
    base_mask = pygame.Surface(base_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(base_mask, (255, 255, 255, 255), base_mask.get_rect(), border_radius=radius)
    base_surface.blit(base_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(base_surface, base_rect.topleft)

    face_rect = rect.inflate(-12, -12)
    face_rect = face_rect.move(0, offsets["face"])
    face_surface = pygame.Surface(face_rect.size, pygame.SRCALPHA)
    for y in range(face_surface.get_height()):
        ratio = y / max(face_surface.get_height() - 1, 1)
        color = _blend(palette["top"], palette["bottom"], ratio)
        pygame.draw.line(face_surface, color, (0, y), (face_surface.get_width(), y))

    mask = pygame.Surface(face_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    face_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    surface.blit(face_surface, face_rect.topleft)
    pygame.draw.rect(surface, palette["border"], face_rect, width=4, border_radius=radius)

    return face_rect


__all__ = ["draw_glossy_button"]


class Button:
    """Interactive button built on top of the glossy button helper."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        palette: Palette,
        *,
        text_color: tuple[int, int, int] = (255, 255, 255),
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self.rect = rect
        self.label = label
        self.font = font
        self.palette = palette
        self.text_color = text_color
        self._callback = callback

    def set_rect(self, rect: pygame.Rect) -> None:
        self.rect = rect

    def render(
        self,
        surface: pygame.Surface,
        *,
        hover: bool = False,
        selected: bool = False,
    ) -> pygame.Rect:
        face_rect = draw_glossy_button(
            surface,
            self.rect,
            self.palette,
            selected=selected,
            hover=hover,
        )
        text_surface = self.font.render(self.label, True, self.text_color)
        surface.blit(text_surface, text_surface.get_rect(center=face_rect.center))
        return face_rect

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.trigger()
                return True
        return False

    def trigger(self) -> None:
        if self._callback:
            self._callback()


__all__ = ["draw_glossy_button", "Button"]
