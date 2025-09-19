"""Configuration scene for the timed test mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import pygame

from .. import settings
from ..models import TestConfig
from .base import Scene


@dataclass(frozen=True)
class SpeedOption:
    label: str
    animal: str
    minutes: int
    description: str


class TestSetupScene(Scene):
    """Lets the player pick tables, speed, and question count."""

    TABLE_VALUES = list(range(1, 11))
    SPEED_OPTIONS: Sequence[SpeedOption] = (
        SpeedOption("Slak", "🐌", 10, "Lekker rustig"),
        SpeedOption("Schildpad", "🐢", 8, "Rustig racen"),
        SpeedOption("Haas", "🐇", 7, "Supersnel"),
        SpeedOption("Cheeta", "🐆", 5, "Ultieme uitdaging"),
    )
    QUESTION_CHOICES = (30, 50, 100)

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.title_font = settings.load_title_font(54)
        self.section_font = settings.load_font(32)
        self.option_font = settings.load_font(28)
        self.button_font = settings.load_font(30)
        self.helper_font = settings.load_font(22)

        self.selected_tables: set[int] = set(self.TABLE_VALUES)
        self.selected_speed_index = 1  # Start met schildpad
        self.selected_question_index = 1  # 50 vragen standaard

        self.table_rects: List[Tuple[pygame.Rect, int]] = []
        self.speed_rects: List[Tuple[pygame.Rect, int]] = []
        self.question_rects: List[Tuple[pygame.Rect, int]] = []
        self.start_rect: pygame.Rect | None = None

        self.feedback_message = ""
        self.feedback_timer = 0.0
        self.show_back_button = True

    # Event handling -------------------------------------------------
    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if self.handle_back_button_event(event):
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    from .main_menu import MainMenuScene

                    self.app.change_scene(MainMenuScene)
                    return
                if event.key == pygame.K_RETURN:
                    self._start_test()
                    return
                if event.key == pygame.K_a:
                    self.selected_tables = set(self.TABLE_VALUES)
                if event.key == pygame.K_c:
                    self.selected_tables.clear()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.start_rect and self.start_rect.collidepoint(event.pos):
                    self._start_test()
                    return
                for rect, value in self.table_rects:
                    if rect.collidepoint(event.pos):
                        if value in self.selected_tables:
                            self.selected_tables.remove(value)
                        else:
                            self.selected_tables.add(value)
                        break
                for rect, index in self.speed_rects:
                    if rect.collidepoint(event.pos):
                        self.selected_speed_index = index
                        break
                for rect, index in self.question_rects:
                    if rect.collidepoint(event.pos):
                        self.selected_question_index = index
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
        self._draw_speed(surface)
        self._draw_questions(surface)
        self._draw_start_button(surface)
        self._draw_feedback(surface)
        self.render_back_button(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        title = self.title_font.render("Testmodus", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(margin, margin - 30)))
        subtitle = self.helper_font.render("Kies jouw uitdaging en druk op Start!", True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, subtitle.get_rect(topleft=(margin + 4, margin + 24)))

    def _draw_tables(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header = self.section_font.render("Voor welke tafels wil je gaan?", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(margin, margin + 70)))

        cols = 5
        button_size = (120, 60)
        spacing = 12
        start_x = margin
        start_y = margin + 120
        self.table_rects = []

        for idx, value in enumerate(self.TABLE_VALUES):
            col = idx % cols
            row = idx // cols
            x = start_x + col * (button_size[0] + spacing)
            y = start_y + row * (button_size[1] + spacing)
            rect = pygame.Rect(x, y, *button_size)
            is_selected = value in self.selected_tables
            colour = settings.COLOR_SELECTION if is_selected else settings.COLOR_CARD_INACTIVE
            pygame.draw.rect(surface, colour, rect, border_radius=14)
            text_color = settings.COLOR_TEXT_PRIMARY if is_selected else settings.COLOR_TEXT_DIM
            text = self.option_font.render(f"Tafel {value}", True, text_color)
            surface.blit(text, text.get_rect(center=rect.center))
            if is_selected:
                pygame.draw.rect(surface, settings.COLOR_ACCENT, rect, width=3, border_radius=14)
            else:
                self._apply_inactive_style(surface, rect, border_radius=14)
            self.table_rects.append((rect, value))

        hint = self.helper_font.render("Tip: druk op 'A' voor alles, 'C' om te wissen", True, settings.COLOR_TEXT_DIM)
        surface.blit(hint, hint.get_rect(topleft=(margin, start_y + 2 * (button_size[1] + spacing) + 14)))

    def _draw_speed(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header = self.section_font.render("Hoe snel ga je?", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(margin, margin + 260)))
        self.speed_rects = []

        base_x = margin
        base_y = margin + 310
        card_width = 200
        card_height = 100
        spacing = 16

        for index, option in enumerate(self.SPEED_OPTIONS):
            x = base_x + index * (card_width + spacing)
            rect = pygame.Rect(x, base_y, card_width, card_height)
            is_selected = index == self.selected_speed_index
            colour = settings.COLOR_SELECTION if is_selected else (70, 96, 144)
            pygame.draw.rect(surface, colour, rect, border_radius=18)
            text_color = settings.COLOR_TEXT_PRIMARY if is_selected else settings.COLOR_TEXT_DIM
            text = self.option_font.render(f"{option.animal} {option.label}", True, text_color)
            surface.blit(text, text.get_rect(midtop=(rect.centerx, rect.top + 14)))

            minutes_color = settings.COLOR_TEXT_PRIMARY if is_selected else settings.COLOR_TEXT_DIM
            minutes_text = self.helper_font.render(f"{option.minutes} minuten", True, minutes_color)
            surface.blit(minutes_text, minutes_text.get_rect(midtop=(rect.centerx, rect.top + 48)))

            description_color = settings.COLOR_TEXT_DIM if is_selected else (120, 130, 150)
            description = self.helper_font.render(option.description, True, description_color)
            surface.blit(description, description.get_rect(midtop=(rect.centerx, rect.top + 72)))

            if is_selected:
                pygame.draw.rect(surface, settings.COLOR_ACCENT, rect, width=3, border_radius=18)
            self.speed_rects.append((rect, index))

            if not is_selected:
                self._apply_inactive_style(surface, rect, border_radius=18)

    def _draw_questions(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header = self.section_font.render("Hoeveel sommen wil je doen?", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(surface.get_width() - margin - 260, margin + 70)))
        self.question_rects = []

        width = 220
        height = 72
        spacing = 18
        base_x = surface.get_width() - settings.SCREEN_MARGIN - width
        base_y = settings.SCREEN_MARGIN + 120

        for index, amount in enumerate(self.QUESTION_CHOICES):
            rect = pygame.Rect(base_x, base_y + index * (height + spacing), width, height)
            is_selected = index == self.selected_question_index
            colour = settings.COLOR_SELECTION if is_selected else settings.COLOR_CARD_INACTIVE
            pygame.draw.rect(surface, colour, rect, border_radius=18)
            text_color = settings.COLOR_TEXT_PRIMARY if is_selected else settings.COLOR_TEXT_DIM
            text = self.option_font.render(f"{amount} sommen", True, text_color)
            surface.blit(text, text.get_rect(center=rect.center))
            if is_selected:
                pygame.draw.rect(surface, settings.COLOR_ACCENT, rect, width=3, border_radius=18)
            self.question_rects.append((rect, index))

            if not is_selected:
                self._apply_inactive_style(surface, rect, border_radius=18)

    def _draw_start_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        rect = pygame.Rect(surface.get_width() - margin - 220, surface.get_height() - margin - 72, 220, 72)
        colour = settings.COLOR_ACCENT
        pygame.draw.rect(surface, colour, rect, border_radius=24)
        text = self.button_font.render("Start!", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=rect.center))
        self.start_rect = rect

    def _draw_feedback(self, surface: pygame.Surface) -> None:
        if not self.feedback_message:
            return
        alpha = 255 if self.feedback_timer > 1 else int(255 * self.feedback_timer)
        text_surface = self.helper_font.render(self.feedback_message, True, settings.COLOR_ACCENT_LIGHT)
        text_surface.set_alpha(alpha)
        rect = text_surface.get_rect(center=(surface.get_width() // 2, surface.get_height() - 40))
        surface.blit(text_surface, rect)

    def _start_test(self) -> None:
        if not self.selected_tables:
            self.feedback_message = "Kies minstens \u00e9\u00e9n tafel."
            self.feedback_timer = 2.5
            return

        speed = self.SPEED_OPTIONS[self.selected_speed_index]
        question_count = self.QUESTION_CHOICES[self.selected_question_index]
        config = TestConfig(
            tables=sorted(self.selected_tables),
            question_count=question_count,
            time_limit_seconds=speed.minutes * 60,
        )
        from .test_session import TestSessionScene

        self.app.change_scene(TestSessionScene, config=config, speed_label=speed.label)

    @staticmethod
    def _apply_inactive_style(surface: pygame.Surface, rect: pygame.Rect, *, border_radius: int) -> None:
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(overlay, settings.COLOR_INACTIVE_OVERLAY, overlay.get_rect(), border_radius=border_radius)
        surface.blit(overlay, rect.topleft)

    def on_back(self) -> None:
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)
