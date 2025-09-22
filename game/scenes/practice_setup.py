"""Setup screen for practice mode."""

from __future__ import annotations

import pygame

from .. import settings
from ..models import PracticeConfig
from .base import Scene
from ..ui import Button, draw_glossy_button


class PracticeSetupScene(Scene):
    """Lets the player choose which tables to practice."""

    TABLE_VALUES = list(range(1, 11))

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.title_font = settings.load_title_font(54)
        self.section_font = settings.load_title_font(36)
        self.option_font = settings.load_font(28)
        self.helper_font = settings.load_font(22)

        defaults = [value for value in getattr(self.app.settings, "default_practice_tables", self.TABLE_VALUES) if value in self.TABLE_VALUES]
        self.selected_tables: set[int] = set(defaults or self.TABLE_VALUES)
        self.table_rects: list[tuple[pygame.Rect, int]] = []

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
        self.start_button = Button(
            pygame.Rect(0, 0, 260, 86),
            self.tr("practice_setup.actions.start", default="Start oefenen"),
            self.option_font,
            self.start_palette,
            text_color=settings.COLOR_TEXT_PRIMARY,
            callback=self._start_practice,
        )
        self.back_palette = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }
        self.back_button_rect: pygame.Rect | None = None

    # Event handling -------------------------------------------------
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if self.handle_back_button_event(event):
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                    self._handle_back_action()
                    return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._handle_back_action()
                    return
                if event.key == pygame.K_RETURN:
                    self._start_practice()
                    return
                if event.key == pygame.K_a:
                    self.selected_tables = set(self.TABLE_VALUES)
                if event.key == pygame.K_w:
                    self.selected_tables.clear()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                    self.on_back()
                    return
                if self.start_button.handle_event(event):
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
        self._draw_back_button(surface)
        self._draw_title(surface)
        self._draw_tables(surface)
        self._draw_feedback(surface)
        self._draw_start_button(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        offset = (self.back_button_rect.right + 40) if self.back_button_rect else (margin + 100)
        title_text = self.tr("practice_setup.title", default="Oefenmodus")
        title = self.title_font.render(title_text, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(offset, margin - 30)))
        subtitle_text = self.tr(
            "practice_setup.subtitle",
            default="Kies de tafels waarop je wilt oefenen.",
        )
        subtitle = self.helper_font.render(subtitle_text, True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, subtitle.get_rect(topleft=(offset + 4, margin + 24)))

    def _draw_tables(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header_text = self.tr(
            "common.tables.header",
            default="Voor welke tafels wil je gaan?",
        )
        header = self.section_font.render(header_text, True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(margin, margin + 100)))

        cols = 5
        button_size = (150, 64)
        spacing = 16
        start_x = margin
        start_y = margin + 160
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
            label_text = self.tr(
                "common.tables.label",
                default="Tafel {number}",
                number=value,
            )
            label = self.option_font.render(label_text, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(label, label.get_rect(center=face_rect.center))
            self.table_rects.append((rect, value))

        rows = (len(self.TABLE_VALUES) + cols - 1) // cols
        grid_bottom = start_y + rows * (button_size[1] + spacing) - spacing

        hint_text = self.tr(
            "common.tables.hint_select",
            default="Tip: druk op 'A' voor alles, 'W' om te wissen",
        )
        hint = self.helper_font.render(hint_text, True, settings.COLOR_TEXT_DIM)
        hint_rect = hint.get_rect(topleft=(margin, grid_bottom + 20))
        surface.blit(hint, hint_rect)

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
        self.start_button.set_rect(rect)
        self.start_button.label = self.tr("practice_setup.actions.start", default="Start oefenen")
        self.start_button.render(surface, hover=rect.collidepoint(pygame.mouse.get_pos()))

    def _start_practice(self) -> None:
        if not self.selected_tables:
            self.feedback_message = self.tr(
                "common.feedback.choose_table",
                default="Kies minstens één tafel.",
            )
            self.feedback_timer = 2.5
            return

        config = PracticeConfig(tables=sorted(self.selected_tables))
        from .practice_session import PracticeSessionScene

        self.app.change_scene(PracticeSessionScene, config=config)

    def _handle_back_action(self) -> None:
        self.on_back()

    def on_back(self) -> None:
        self.play_back_sound()
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)

    def _draw_back_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        back_label = self.tr("common.back", default="Terug")
        text = self.helper_font.render(back_label, True, settings.COLOR_TEXT_PRIMARY)
        padding_x = 32
        padding_y = 18
        width = text.get_width() + padding_x * 2
        height = text.get_height() + padding_y * 2
        rect = pygame.Rect(margin, margin + 6, width, height)
        face_rect = draw_glossy_button(
            surface,
            rect,
            self.back_palette,
            selected=False,
            hover=rect.collidepoint(pygame.mouse.get_pos()),
            corner_radius=28,
        )
        surface.blit(text, text.get_rect(center=face_rect.center))
        self.back_button_rect = rect
