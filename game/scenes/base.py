"""Scene base class and utilities."""

from __future__ import annotations

from typing import Iterable, Sequence

import pygame

from .. import settings


class Scene:
    """Base class for all scenes."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self.show_back_button = False
        self._back_button_rect: pygame.Rect | None = None

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        """React to incoming events. Child classes override as needed."""

    def update(self, delta_time: float) -> None:
        """Update internal state. Child classes override as needed."""

    def render(self, surface: pygame.Surface) -> None:
        raise NotImplementedError

    # Utility helpers -------------------------------------------------
    @staticmethod
    def draw_vertical_gradient(surface: pygame.Surface, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> None:
        """Draw a simple vertical gradient as the background."""

        height = surface.get_height()
        width = surface.get_width()
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = tuple(
                int(top_color[i] + (bottom_color[i] - top_color[i]) * ratio)
                for i in range(3)
            )
            pygame.draw.line(surface, color, (0, y), (width, y))

    # Back button helpers ---------------------------------------------
    def render_back_button(self, surface: pygame.Surface) -> None:
        if not self.show_back_button:
            self._back_button_rect = None
            return

        margin = settings.SCREEN_MARGIN
        radius = 36
        diameter = radius * 2
        rect = pygame.Rect(margin, margin, diameter, diameter)
        pygame.draw.circle(surface, settings.COLOR_NAV_BG, rect.center, radius)
        pygame.draw.circle(surface, settings.COLOR_NAV_ICON, rect.center, radius, width=2)

        arrow_body = [
            (rect.centerx + 8, rect.centery - 14),
            (rect.centerx - 6, rect.centery),
            (rect.centerx + 8, rect.centery + 14),
        ]
        pygame.draw.polygon(surface, settings.COLOR_NAV_ICON, arrow_body)
        pygame.draw.line(surface, settings.COLOR_NAV_ICON, (rect.centerx + 4, rect.centery), (rect.centerx + 12, rect.centery), 6)

        self._back_button_rect = rect

    def handle_back_button_event(self, event: pygame.event.Event) -> bool:
        if not self.show_back_button or self._back_button_rect is None:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_button_rect.collidepoint(event.pos):
                self.play_back_sound()
                self.on_back()
                return True
        return False

    def on_back(self) -> None:
        """Override to implement back navigation."""

    def play_back_sound(self) -> None:
        if hasattr(self.app, "play_sound"):
            try:
                self.app.play_sound("back")
            except Exception:
                pass

    # Translation helpers --------------------------------------------
    def tr(self, key: str, default: str | None = None, **kwargs: object) -> str:
        translator = getattr(self.app, "translator", None)
        if translator is not None:
            translated = translator.gettext(key, **kwargs)
            if translated != key:
                return translated
        if default is not None:
            try:
                return default.format(**kwargs)
            except (KeyError, ValueError):
                return default
        if kwargs:
            try:
                return key.format(**kwargs)
            except (KeyError, ValueError):
                return key
        return key

    def tr_list(self, key: str, default: Sequence[str] | None = None) -> list[str]:
        translator = getattr(self.app, "translator", None)
        if translator is not None:
            values = translator.get_list(key)
            if values:
                if len(values) == 1 and values[0] == key:
                    values = []
                else:
                    return values
        if default is not None:
            return list(default)
        return []


__all__ = ["Scene"]
