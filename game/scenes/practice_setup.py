"""Setup screen for practice mode."""

from __future__ import annotations

import pygame

from .. import settings
from ..models import PracticeConfig
from .base import Scene
from ..ui import draw_glossy_button


class PracticeSetupScene(Scene):
    """Lets the player choose which tables to practice."""

    TABLE_VALUES = list(range(1, 11))

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.title_font = settings.load_title_font(54)
        self.section_font = settings.load_title_font(36)
        self.option_font = settings.load_font(28)
        self.helper_font = settings.load_font(22)

        self.selected_tables: set[int] = set(self.TABLE_VALUES)
        self.table_rects: list[tuple[pygame.Rect, int]] = []
        self.start_rect: pygame.Rect | None = None

        self.feedback_message = ""
        self.feedback_timer = 0.0

        self.table_palette_active = {
            "top": (116, 227, 128),
            "bottom": (63, 186, 94),
            "border": (36, 140, 67),
            "shadow": (45, 122, 59),
        }
        self.table_palette_inactive = {
            "top": (242, 236, 228),
            "bottom": (209, 197, 184),
            "border": (168, 156, 145),
            "shadow": (150, 140, 130),
        }
        self.start_palette = {
            "top": (255, 215, 90),
            "bottom": (247, 176, 49),
            "border": (191, 128, 38),
            "shadow": (160, 109, 34),
        }

    # Event handling -------------------------------------------------
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    from .main_menu import MainMenuScene

                    self.app.change_scene(MainMenuScene)
                    return
                if event.key == pygame.K_RETURN:
                    self._start_practice()
                    return
                if event.key == pygame.K_a:
                    self.selected_tables = set(self.TABLE_VALUES)
                if event.key == pygame.K_c:
                    self.selected_tables.clear()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.start_rect and self.start_rect.collidepoint(event.pos):
                    self._start_practice()
                    return
                for rect, value in self.table_rects:
                    if rect.collidepoint(event.pos):
                        if value in self.selected_tables:
                            self.selected_tables.remove(value)
                        else:
                            self.selected_tables.add(value)
                        break

    # Update ---------------------------------------------------------
    def update(self, delta_time: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer = max(self.feedback_timer - delta_time, 0)
            if self.feedback_timer == 0:
                self.feedback_message = ""

    # Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._draw_title(surface)
        self._draw_tables(surface)
        self._draw_feedback(surface)
        self._draw_start_button(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        title = self.title_font.render("Oefenmodus", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(margin, margin - 30)))
        subtitle = self.helper_font.render("Kies de tafels waarop je wilt oefenen.", True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, subtitle.get_rect(topleft=(margin + 4, margin + 24)))

    def _draw_tables(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header = self.section_font.render("Voor welke tafels wil je gaan?", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(margin, margin + 70)))

        cols = 5
        button_size = (150, 64)
        spacing = 16
        start_x = margin
        start_y = margin + 120
        self.table_rects = []
        mouse_pos = pygame.mouse.get_pos()

        for idx, value in enumerate(self.TABLE_VALUES):
            col = idx % cols
            row = idx // cols
            rect = pygame.Rect(
                start_x + col * (button_size[0] + spacing),
                start_y + row * (button_size[1] + spacing),
                *button_size,
            )
            is_selected = value in self.selected_tables
            palette = self.table_palette_active if is_selected else self.table_palette_inactive
            face_rect = draw_glossy_button(
                surface,
                rect,
                palette,
                selected=is_selected,
                hover=rect.collidepoint(mouse_pos),
                corner_radius=32,
            )
            label = self.option_font.render(f"Tafel {value}", True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(label, label.get_rect(center=face_rect.center))
            self.table_rects.append((rect, value))

        hint = self.helper_font.render("Tip: druk op 'A' voor alles, 'C' om te wissen", True, settings.COLOR_TEXT_DIM)
        surface.blit(hint, hint.get_rect(topleft=(margin, start_y + 3 * (button_size[1] + spacing) + 12)))

    def _draw_feedback(self, surface: pygame.Surface) -> None:
        if not self.feedback_message:
            return
        alpha = 255 if self.feedback_timer > 1 else int(255 * self.feedback_timer)
        text_surface = self.helper_font.render(self.feedback_message, True, settings.COLOR_ACCENT_LIGHT)
        text_surface.set_alpha(alpha)
        rect = text_surface.get_rect(center=(surface.get_width() // 2, surface.get_height() - 60))
        surface.blit(text_surface, rect)

    def _draw_start_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        width = 260
        height = 86
        rect = pygame.Rect(surface.get_width() - margin - width, surface.get_height() - margin - height, width, height)
        face_rect = draw_glossy_button(
            surface,
            rect,
            self.start_palette,
            selected=False,
            hover=rect.collidepoint(pygame.mouse.get_pos()),
            corner_radius=32,
        )
        text = self.option_font.render("Start oefenen", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=face_rect.center))
        self.start_rect = rect

    def _start_practice(self) -> None:
        if not self.selected_tables:
            self.feedback_message = "Kies minstens één tafel."
            self.feedback_timer = 2.5
            return

        config = PracticeConfig(tables=sorted(self.selected_tables))
        from .practice_session import PracticeSessionScene

        self.app.change_scene(PracticeSessionScene, config=config)
