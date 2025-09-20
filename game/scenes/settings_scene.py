"""Settings scene for audio, defaults, language, and profile management."""

from __future__ import annotations

import datetime
import json
import random
import string
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import pygame

from .. import settings
from ..ui import draw_glossy_button
from .base import Scene


class SettingsScene(Scene):
    """Interactive settings dashboard for the multiplication game."""

    LANGUAGE_OPTIONS: Sequence[Tuple[str, str]] = (
        ("nl", "Nederlands"),
        ("en", "English"),
    )

    FEEDBACK_OPTIONS: Sequence[Tuple[str, str]] = (
        ("warm", "Warme hints"),
        ("compact", "Korte hints"),
    )

    SPEED_LABELS: Sequence[str] = ("Slak", "Schildpad", "Haas", "Cheeta")
    QUESTION_CHOICES: Sequence[int] = (30, 50, 100)
    TABLE_COLS: int = 5
    TABLE_BUTTON_SIZE: Tuple[int, int] = (60, 48)

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.title_font = settings.load_title_font(52)
        self.section_font = settings.load_title_font(32)
        self.option_font = settings.load_font(26)
        self.helper_font = settings.load_font(22)
        self.value_font = settings.load_font(24)
        self.button_font = settings.load_font(28)

        self.settings = app.settings.clone()
        self.feedback_message = ""
        self.feedback_timer = 0.0
        self.has_unsaved_changes = False

        self.music_toggle_rect: pygame.Rect | None = None
        self.effects_toggle_rect: pygame.Rect | None = None
        self.large_text_toggle_rect: pygame.Rect | None = None
        self.feedback_option_rects: Dict[str, pygame.Rect] = {}
        self.language_rects: Dict[str, pygame.Rect] = {}
        self.practice_table_rects: List[Tuple[pygame.Rect, int]] = []
        self.test_table_rects: List[Tuple[pygame.Rect, int]] = []
        self.speed_rects: Dict[str, pygame.Rect] = {}
        self.question_rects: Dict[int, pygame.Rect] = {}
        self.profile_button_rects: Dict[str, pygame.Rect] = {}
        self.data_button_rects: Dict[str, pygame.Rect] = {}

        self.name_input_active = False
        self.name_buffer = self.app.active_profile.display_name
        self.name_input_rect: pygame.Rect | None = None

        self.buy_rect: pygame.Rect | None = None
        self.save_rect: pygame.Rect | None = None
        self.back_top_rect: pygame.Rect | None = None
        self.footer_back_rect: pygame.Rect | None = None

        self.scroll_offset = 0.0
        self.max_scroll = 0.0
        self.content_height = 0.0
        self.pointer_content_pos: Tuple[float, float] = (0.0, 0.0)
        self.card_inner_margin = 28
        self.section_spacing = 24
        self.grid_spacing = 14

    # Event handling -------------------------------------------------
    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._handle_mouse_click(event.pos):
                    continue
            elif event.type == pygame.MOUSEWHEEL:
                self._adjust_scroll(-event.y * 60)
                continue
            if event.type == pygame.KEYDOWN:
                if self.name_input_active:
                    self._handle_name_input(event)
                    continue
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._handle_back()
                    return
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._save_settings()
                    continue
                if event.key == pygame.K_UP:
                    self._adjust_scroll(-40)
                    continue
                if event.key == pygame.K_DOWN:
                    self._adjust_scroll(40)
                    continue
                if event.key == pygame.K_PAGEUP:
                    self._adjust_scroll(-200)
                    continue
                if event.key == pygame.K_PAGEDOWN:
                    self._adjust_scroll(200)
                    continue

    def _handle_mouse_click(self, position: Tuple[int, int]) -> bool:
        content_pos = (position[0], position[1] + self.scroll_offset)

        if self.back_top_rect and self.back_top_rect.collidepoint(content_pos):
            self._handle_back()
            return True
        if self.save_rect and self.save_rect.collidepoint(content_pos):
            self._save_settings()
            return True
        if self.buy_rect and self.buy_rect.collidepoint(content_pos):
            self._show_support_message()
            return True
        if self.footer_back_rect and self.footer_back_rect.collidepoint(content_pos):
            self._handle_back()
            return True

        if self.music_toggle_rect and self.music_toggle_rect.collidepoint(content_pos):
            self.settings.music_enabled = not self.settings.music_enabled
            self.has_unsaved_changes = True
            self._apply_music_volume()
            return True
        if self.effects_toggle_rect and self.effects_toggle_rect.collidepoint(content_pos):
            self.settings.effects_enabled = not self.settings.effects_enabled
            self.has_unsaved_changes = True
            return True
        if self.large_text_toggle_rect and self.large_text_toggle_rect.collidepoint(content_pos):
            self.settings.large_text = not self.settings.large_text
            self.has_unsaved_changes = True
            return True

        for key, rect in self.feedback_option_rects.items():
            if rect.collidepoint(content_pos):
                self.settings.feedback_style = key
                self.has_unsaved_changes = True
                return True

        for code, rect in self.language_rects.items():
            if rect.collidepoint(content_pos):
                self.settings.language = code
                self.has_unsaved_changes = True
                return True

        self._handle_grid_click(content_pos, self.practice_table_rects, self.settings.default_practice_tables)
        self._handle_grid_click(content_pos, self.test_table_rects, self.settings.default_test_tables)

        for label, rect in self.speed_rects.items():
            if rect.collidepoint(content_pos):
                self.settings.default_test_speed = label
                self.has_unsaved_changes = True
                return True

        for quantity, rect in self.question_rects.items():
            if rect.collidepoint(content_pos):
                self.settings.default_test_questions = quantity
                self.has_unsaved_changes = True
                return True

        if self.name_input_rect and self.name_input_rect.collidepoint(content_pos):
            self.name_input_active = True
            return True

        for identifier, rect in self.profile_button_rects.items():
            if rect.collidepoint(content_pos):
                self._handle_profile_action(identifier)
                return True

        for identifier, rect in self.data_button_rects.items():
            if rect.collidepoint(content_pos):
                self._handle_data_action(identifier)
                return True

        self.name_input_active = False
        return False

    def _handle_name_input(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_RETURN:
            self._apply_name_change()
            self.name_input_active = False
            return
        if event.key == pygame.K_ESCAPE:
            self.name_input_active = False
            self.name_buffer = self.app.active_profile.display_name
            return
        if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
            self.name_buffer = self.name_buffer[:-1]
            return
        if event.unicode and len(self.name_buffer) < 16:
            if event.unicode.isprintable():
                self.name_buffer += event.unicode

    # Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.pointer_content_pos = (mouse_x, mouse_y + self.scroll_offset)

        content_surface_height = surface.get_height() + 1200
        content_surface = pygame.Surface((surface.get_width(), content_surface_height), pygame.SRCALPHA)

        content_bottom = self._render_content(content_surface)
        self.content_height = content_bottom
        self.max_scroll = max(0.0, self.content_height - surface.get_height())
        self.scroll_offset = max(0.0, min(self.scroll_offset, self.max_scroll))
        self.pointer_content_pos = (mouse_x, mouse_y + self.scroll_offset)

        surface.blit(content_surface, (0, -int(self.scroll_offset)))

    # Drawing helpers ------------------------------------------------
    def _render_content(self, surface: pygame.Surface) -> int:
        self._draw_back_button(surface)
        self._draw_header(surface)
        y = settings.SCREEN_MARGIN + 120
        spacer = self.section_spacing
        y = self._draw_audio_card(surface, y) + spacer
        y = self._draw_defaults_card(surface, y) + spacer
        y = self._draw_feedback_language_card(surface, y) + spacer
        y = self._draw_profile_card(surface, y) + spacer
        y = self._draw_data_card(surface, y) + spacer
        y = self._draw_support_card(surface, y) + spacer
        y = self._draw_footer_buttons(surface, y)
        self._draw_feedback(surface)
        return y + settings.SCREEN_MARGIN

    def _draw_header(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        back_right = (self.back_top_rect.right + 24) if self.back_top_rect else margin
        title = self.title_font.render("Instellingen", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(back_right, margin - 20)))
        subtitle = self.helper_font.render("Pas het spel aan op jouw gezin.", True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, subtitle.get_rect(topleft=(back_right + 6, margin + 24)))

    def _draw_card(self, surface: pygame.Surface, top: int, height: int) -> pygame.Rect:
        margin = settings.SCREEN_MARGIN
        rect = pygame.Rect(margin, top, surface.get_width() - margin * 2, height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, rect, border_radius=32)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, rect, width=3, border_radius=32)
        return rect

    def _draw_back_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        rect = pygame.Rect(margin, margin - 8, 140, 44)
        palette = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }
        draw_glossy_button(
            surface,
            rect,
            palette,
            selected=False,
            hover=rect.collidepoint(pygame.mouse.get_pos()),
            corner_radius=24,
        )
        label = self.button_font.render("Terug", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(label, label.get_rect(center=rect.center))
        self.back_top_rect = rect

    def _draw_audio_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        toggle_height = 48
        total_height = int(inner * 2 + heading_h + self.section_spacing + toggle_height)
        card = self._draw_card(surface, top, total_height)
        heading = self.section_font.render("Geluid", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        toggle_y = card.top + inner + heading_h + self.section_spacing
        self.music_toggle_rect = self._draw_toggle(
            surface,
            card.left + inner,
            toggle_y,
            "Muziek",
            self.settings.music_enabled,
        )
        self.effects_toggle_rect = self._draw_toggle(
            surface,
            self.music_toggle_rect.right + self.section_spacing,
            toggle_y,
            "Effecten",
            self.settings.effects_enabled,
        )
        return card.bottom

    def _draw_defaults_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        label_h = self.option_font.get_height()
        button_width, button_height = self.TABLE_BUTTON_SIZE
        grid_width = self.TABLE_COLS * button_width + (self.TABLE_COLS - 1) * self.grid_spacing
        grid_height = button_height * 2 + self.grid_spacing

        left_height = (
            heading_h
            + self.section_spacing
            + label_h
            + self.grid_spacing
            + grid_height
            + self.section_spacing
            + label_h
            + self.grid_spacing
            + grid_height
        )
        column_buttons_height = label_h + self.grid_spacing + len(self.SPEED_LABELS) * 52
        questions_buttons_height = label_h + self.grid_spacing + len(self.QUESTION_CHOICES) * 52
        right_height = heading_h + self.section_spacing + max(column_buttons_height, questions_buttons_height)

        total_height = int(inner * 2 + max(left_height, right_height))
        card = self._draw_card(surface, top, total_height)

        heading = self.section_font.render("Standaard instellingen", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        column_top = card.top + inner + heading_h + self.section_spacing
        practice_title = self.option_font.render("Oefenen tafels", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(practice_title, practice_title.get_rect(topleft=(card.left + inner, column_top)))
        practice_grid_top = practice_title.get_rect().bottom + self.grid_spacing
        self.practice_table_rects = self._draw_table_grid(
            surface,
            origin=(card.left + inner, practice_grid_top),
            selected=self.settings.default_practice_tables,
        )

        test_title_top = practice_grid_top + grid_height + self.section_spacing
        test_title = self.option_font.render("Test tafels", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(test_title, test_title.get_rect(topleft=(card.left + inner, test_title_top)))
        test_grid_top = test_title.get_rect().bottom + self.grid_spacing
        self.test_table_rects = self._draw_table_grid(
            surface,
            origin=(card.left + inner, test_grid_top),
            selected=self.settings.default_test_tables,
        )

        self.speed_rects = {}
        right_column_x = card.left + inner + grid_width + self.section_spacing * 3
        speed_title = self.option_font.render("Snelheid", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(speed_title, speed_title.get_rect(topleft=(right_column_x, column_top)))
        speed_button_top = speed_title.get_rect().bottom + self.grid_spacing
        for index, label in enumerate(self.SPEED_LABELS):
            rect = pygame.Rect(right_column_x, speed_button_top + index * 52, 170, 44)
            selected = self.settings.default_test_speed == label
            self.speed_rects[label] = self._draw_small_button(surface, rect, label, selected)

        questions_title = self.option_font.render("Aantal vragen", True, settings.COLOR_TEXT_PRIMARY)
        questions_x = right_column_x + 200
        surface.blit(questions_title, questions_title.get_rect(topleft=(questions_x, column_top)))
        questions_button_top = questions_title.get_rect().bottom + self.grid_spacing
        self.question_rects = {}
        for index, quantity in enumerate(self.QUESTION_CHOICES):
            rect = pygame.Rect(questions_x, questions_button_top + index * 52, 170, 44)
            selected = self.settings.default_test_questions == quantity
            self.question_rects[quantity] = self._draw_small_button(surface, rect, str(quantity), selected)

        return card.bottom

    def _draw_feedback_language_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        label_h = self.option_font.get_height()
        feedback_row_height = 50
        language_row_height = label_h + self.grid_spacing + 44
        large_text_row_height = label_h + self.grid_spacing + 44
        total_height = int(
            inner * 2
            + heading_h
            + self.section_spacing
            + feedback_row_height
            + self.section_spacing
            + language_row_height
            + self.section_spacing
            + large_text_row_height
        )
        card = self._draw_card(surface, top, total_height)
        heading = self.section_font.render("Feedback & taal", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        self.feedback_option_rects = {}
        feedback_top = card.top + inner + heading_h + self.section_spacing
        x = card.left + inner
        for option, label in self.FEEDBACK_OPTIONS:
            rect = pygame.Rect(x, feedback_top, 200, 50)
            selected = self.settings.feedback_style == option
            self.feedback_option_rects[option] = self._draw_small_button(surface, rect, label, selected)
            x += rect.width + self.section_spacing

        language_title = self.option_font.render("Taal", True, settings.COLOR_TEXT_PRIMARY)
        language_top = feedback_top + feedback_row_height + self.section_spacing
        surface.blit(language_title, language_title.get_rect(topleft=(card.left + inner, language_top)))
        self.language_rects = {}
        lx = card.left + inner + language_title.get_width() + self.section_spacing
        for code, label in self.LANGUAGE_OPTIONS:
            rect = pygame.Rect(lx, language_top - 4, 180, 44)
            selected = self.settings.language == code
            self.language_rects[code] = self._draw_small_button(surface, rect, label, selected)
            lx += rect.width + self.section_spacing

        large_text_title = self.option_font.render("Grote tekst", True, settings.COLOR_TEXT_PRIMARY)
        large_text_top = language_top + label_h + self.section_spacing
        surface.blit(large_text_title, large_text_title.get_rect(topleft=(card.left + inner, large_text_top)))
        self.large_text_toggle_rect = self._draw_toggle(
            surface,
            card.left + inner + large_text_title.get_width() + self.section_spacing,
            large_text_top - 4,
            "Aan",
            self.settings.large_text,
        )

        return card.bottom

    def _draw_profile_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        label_h = self.option_font.get_height()
        total_height = int(
            inner * 2
            + heading_h
            + self.section_spacing
            + label_h
            + self.grid_spacing
            + 52
            + self.section_spacing
            + 52 * 2
            + self.grid_spacing
        )
        card = self._draw_card(surface, top, total_height)
        heading = self.section_font.render("Profielen", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        name_label = self.option_font.render("Naam actief profiel", True, settings.COLOR_TEXT_PRIMARY)
        name_top = card.top + inner + heading.get_height() + self.section_spacing
        surface.blit(name_label, name_label.get_rect(topleft=(card.left + inner, name_top)))

        input_rect = pygame.Rect(card.left + inner, name_top + name_label.get_height() + self.grid_spacing, 360, 52)
        color = settings.COLOR_SELECTION if self.name_input_active else settings.COLOR_CARD_INACTIVE
        pygame.draw.rect(surface, color, input_rect, border_radius=18)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, input_rect, width=2, border_radius=18)
        text_surface = self.value_font.render(self.name_buffer or " ", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text_surface, text_surface.get_rect(midleft=(input_rect.left + 18, input_rect.centery)))
        if self.name_input_active:
            cursor_x = input_rect.left + 18 + text_surface.get_width() + 4
            pygame.draw.line(surface, settings.COLOR_TEXT_PRIMARY, (cursor_x, input_rect.top + 10), (cursor_x, input_rect.bottom - 10), 2)
        self.name_input_rect = input_rect

        self.profile_button_rects = {}
        palette = {
            "top": (255, 170, 59),
            "bottom": (244, 110, 34),
            "border": (172, 78, 23),
            "shadow": (138, 62, 19),
        }
        button_row_top = input_rect.bottom + self.section_spacing
        specs = [
            ("save_name", card.left + inner, button_row_top, "Bewaar naam"),
            ("new_profile", card.left + inner + 220, button_row_top, "Nieuw profiel"),
            ("reset_coins", card.left + inner, button_row_top + 64, "Reset munten"),
            ("delete_profile", card.left + inner + 220, button_row_top + 64, "Verwijder profiel"),
        ]
        for key, x, y, label in specs:
            rect = pygame.Rect(x, y, 200, 52)
            self.profile_button_rects[key] = rect
            draw_glossy_button(
                surface,
                rect,
                palette,
                selected=False,
                hover=self._is_hover(rect),
                corner_radius=24,
            )
            text = self.button_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(center=rect.center))
        return card.bottom

    def _draw_data_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        total_height = int(inner * 2 + heading_h + self.section_spacing + 56 + self.grid_spacing + self.helper_font.get_height() + 6)
        card = self._draw_card(surface, top, total_height)
        heading = self.section_font.render("Data & privacy", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        self.data_button_rects = self._data_buttons(card, inner)
        palettes = {
            "export_scores": {
                "top": (84, 188, 255),
                "bottom": (31, 117, 232),
                "border": (27, 86, 182),
                "shadow": (21, 73, 152),
            },
            "reset_scores": {
                "top": (244, 110, 34),
                "bottom": (214, 78, 20),
                "border": (172, 58, 18),
                "shadow": (138, 44, 18),
            },
            "reset_all": {
                "top": (255, 131, 131),
                "bottom": (220, 70, 70),
                "border": (168, 48, 48),
                "shadow": (140, 36, 36),
            },
        }
        labels = {
            "export_scores": "Exporteer scores",
            "reset_scores": "Reset scores actief profiel",
            "reset_all": "Complete reset",
        }
        for key, rect in self.data_button_rects.items():
            draw_glossy_button(
                surface,
                rect,
                palettes[key],
                selected=False,
                hover=self._is_hover(rect),
                corner_radius=24,
            )
            text = self.button_font.render(labels[key], True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(center=rect.center))

        info = self.helper_font.render("Let op: resets vragen geen bevestiging, gebruik ze bewust!", True, settings.COLOR_TEXT_DIM)
        info_top = self.data_button_rects["reset_all"].bottom + self.grid_spacing
        surface.blit(info, info.get_rect(topleft=(card.left + inner, info_top)))
        return card.bottom

    def _data_buttons(self, card: pygame.Rect, inner: int) -> Dict[str, pygame.Rect]:
        base_x = card.left + inner
        base_y = card.top + inner + self.section_font.get_height() + self.section_spacing
        return {
            "export_scores": pygame.Rect(base_x, base_y, 220, 56),
            "reset_scores": pygame.Rect(base_x + 240, base_y, 280, 56),
            "reset_all": pygame.Rect(base_x + 540, base_y, 240, 56),
        }

    def _draw_support_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        line_height = self.helper_font.get_height()
        total_height = int(inner * 2 + heading_h + self.section_spacing + 3 * (line_height + 6) + self.section_spacing + 56)
        card = self._draw_card(surface, top, total_height)
        heading = self.section_font.render("Dankjewel!", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        lines = [
            "Dit spel is gemaakt om kinderen spelenderwijs tafels te oefenen.",
            "Geen advertenties, geen tracking – gewoon vrolijk leren.",
            "Vind je het waardevol? Trakteer ons dan op een kop koffie!",
        ]
        y = card.top + inner + heading_h + self.grid_spacing
        for line in lines:
            text = self.helper_font.render(line, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(topleft=(card.left + inner, y)))
            y += self.helper_font.get_height() + 6

        self.buy_rect = pygame.Rect(card.right - inner - 200, card.bottom - inner - 56, 200, 56)
        draw_glossy_button(
            surface,
            self.buy_rect,
            {
                "top": (255, 215, 90),
                "bottom": (247, 176, 49),
                "border": (191, 128, 38),
                "shadow": (160, 109, 34),
            },
            selected=False,
            hover=self._is_hover(self.buy_rect),
            corner_radius=28,
        )
        label = self.button_font.render("Koop een koffie", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(label, label.get_rect(center=self.buy_rect.center))

        return card.bottom

    def _draw_footer_buttons(self, surface: pygame.Surface, top: int) -> int:
        margin = settings.SCREEN_MARGIN
        self.save_rect = pygame.Rect(surface.get_width() - margin - 240, top, 240, 60)
        self.footer_back_rect = pygame.Rect(surface.get_width() - margin - 500, top, 240, 60)

        draw_glossy_button(
            surface,
            self.save_rect,
            {
                "top": (116, 227, 128),
                "bottom": (63, 186, 94),
                "border": (36, 140, 67),
                "shadow": (45, 122, 59),
            },
            selected=False,
            hover=self._is_hover(self.save_rect),
            corner_radius=30,
        )
        save_label = "Opgeslagen" if not self.has_unsaved_changes else "Instellingen opslaan"
        save_text = self.button_font.render(save_label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(save_text, save_text.get_rect(center=self.save_rect.center))

        draw_glossy_button(
            surface,
            self.footer_back_rect,
            {
                "top": (216, 196, 255),
                "bottom": (176, 148, 227),
                "border": (126, 98, 192),
                "shadow": (102, 78, 152),
            },
            selected=False,
            hover=self._is_hover(self.footer_back_rect),
            corner_radius=30,
        )
        back_text = self.button_font.render("Terug", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(back_text, back_text.get_rect(center=self.footer_back_rect.center))

        return max(self.save_rect.bottom, self.footer_back_rect.bottom)

    def _draw_feedback(self, surface: pygame.Surface) -> None:
        if not self.feedback_message:
            return
        alpha = int(255 * min(self.feedback_timer / 3.0, 1.0)) if self.feedback_timer > 0 else 255
        text_surface = self.helper_font.render(self.feedback_message, True, settings.COLOR_TEXT_PRIMARY)
        text_surface.set_alpha(alpha)
        rect = text_surface.get_rect(center=(surface.get_width() // 2, settings.SCREEN_MARGIN))
        surface.blit(text_surface, rect)

    def _draw_toggle(self, surface: pygame.Surface, x: int, y: int, label: str, value: bool) -> pygame.Rect:
        rect = pygame.Rect(x, y, 180, 48)
        palette = {
            "top": (116, 227, 128) if value else (242, 236, 228),
            "bottom": (63, 186, 94) if value else (209, 197, 184),
            "border": (36, 140, 67) if value else (168, 156, 145),
            "shadow": (45, 122, 59) if value else (150, 140, 130),
        }
        draw_glossy_button(
            surface,
            rect,
            palette,
            selected=False,
            hover=self._is_hover(rect),
            corner_radius=24,
        )
        text = self.option_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=rect.center))
        return rect

    def _draw_small_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str, selected: bool) -> pygame.Rect:
        palette = {
            "top": (137, 214, 255) if selected else (242, 236, 228),
            "bottom": (73, 158, 236) if selected else (209, 197, 184),
            "border": (45, 118, 189) if selected else (168, 156, 145),
            "shadow": (41, 99, 156) if selected else (150, 140, 130),
        }
        draw_glossy_button(
            surface,
            rect,
            palette,
            selected=selected,
            hover=self._is_hover(rect),
            corner_radius=20,
        )
        text = self.helper_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=rect.center))
        return rect

    def _draw_table_grid(
        self,
        surface: pygame.Surface,
        *,
        origin: Tuple[int, int],
        selected: Sequence[int],
    ) -> List[Tuple[pygame.Rect, int]]:
        rects: List[Tuple[pygame.Rect, int]] = []
        cols = self.TABLE_COLS
        button_width, button_height = self.TABLE_BUTTON_SIZE
        spacing = 12
        base_x, base_y = origin
        selected_set = set(selected)
        for idx, value in enumerate(range(1, 11)):
            col = idx % cols
            row = idx // cols
            rect = pygame.Rect(
                base_x + col * (button_width + spacing),
                base_y + row * (button_height + spacing),
                button_width,
                button_height,
            )
            is_selected = value in selected_set
            palette = {
                "top": (116, 227, 128) if is_selected else (242, 236, 228),
                "bottom": (63, 186, 94) if is_selected else (209, 197, 184),
                "border": (36, 140, 67) if is_selected else (168, 156, 145),
                "shadow": (45, 122, 59) if is_selected else (150, 140, 130),
            }
            draw_glossy_button(
                surface,
                rect,
                palette,
                selected=is_selected,
                hover=self._is_hover(rect),
                corner_radius=18,
            )
            text = self.helper_font.render(str(value), True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(center=rect.center))
            rects.append((rect, value))
        return rects

    def _is_hover(self, rect: pygame.Rect) -> bool:
        return rect.collidepoint(self.pointer_content_pos)

    def _adjust_scroll(self, delta: float) -> None:
        if self.max_scroll <= 0:
            self.scroll_offset = 0.0
            return
        self.scroll_offset = max(0.0, min(self.scroll_offset + delta, self.max_scroll))

    def _handle_grid_click(self, position: Tuple[int, int], rects: List[Tuple[pygame.Rect, int]], values: List[int]) -> None:
        value_set = set(values)
        for rect, value in rects:
            if rect.collidepoint(position):
                if value in value_set:
                    value_set.remove(value)
                else:
                    value_set.add(value)
                if not value_set:
                    value_set.add(value)
                values[:] = sorted(value_set)
                self.has_unsaved_changes = True
                return

    def _handle_profile_action(self, action: str) -> None:
        if action == "save_name":
            self._apply_name_change()
            self.name_input_active = False
            return
        if action == "new_profile":
            self._create_profile()
            return
        if action == "reset_coins":
            self.app.active_profile.coins = 0
            self.app.save_profiles()
            self.feedback_message = "Munten teruggezet naar 0."
            self.feedback_timer = 3.0
            return
        if action == "delete_profile":
            if len(self.app.profiles) <= 1:
                self.feedback_message = "Je hebt minimaal één profiel nodig."
                self.feedback_timer = 3.0
                return
            profile = self.app.active_profile
            self.app.profiles = [p for p in self.app.profiles if p.identifier != profile.identifier]
            self.app.active_profile_index = 0
            self.app.active_profile = self.app.profiles[0]
            self.app.save_profiles()
            self.app.scores.clear_profile(profile.identifier)
            self.name_buffer = self.app.active_profile.display_name
            self.feedback_message = "Profiel verwijderd."
            self.feedback_timer = 3.0

    def _create_profile(self) -> None:
        identifier = self._generate_profile_id()
        display_name = f"Speler {len(self.app.profiles) + 1}"
        from ..models import PlayerProfile

        profile = PlayerProfile(identifier, display_name, "", coins=0)
        self.app.profiles.append(profile)
        self.app.active_profile_index = len(self.app.profiles) - 1
        self.app.active_profile = profile
        self.app.save_profiles()
        self.name_buffer = display_name
        self.feedback_message = "Nieuw profiel aangemaakt."
        self.feedback_timer = 3.0

    def _generate_profile_id(self) -> str:
        existing = {profile.identifier for profile in self.app.profiles}
        while True:
            candidate = "profile_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
            if candidate not in existing:
                return candidate

    def _handle_data_action(self, action: str) -> None:
        if action == "export_scores":
            self._export_scores()
        elif action == "reset_scores":
            self.app.scores.clear_profile(self.app.active_profile.identifier)
            self.feedback_message = "Scores van dit profiel gewist."
            self.feedback_timer = 3.0
        elif action == "reset_all":
            self.app.scores.clear_all()
            self.app.save_profiles()
            self.feedback_message = "Alle data gewist."
            self.feedback_timer = 3.0

    def _export_scores(self) -> None:
        export_dir: Path = self.app.data_dir
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = export_dir / f"scores_export_{timestamp}.json"
        export_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.app.scores.all_scores(), indent=2), encoding="utf-8")
        self.feedback_message = f"Scores opgeslagen naar {path.name}."
        self.feedback_timer = 3.0

    def _apply_name_change(self) -> None:
        new_name = self.name_buffer.strip()
        if not new_name:
            self.feedback_message = "Naam mag niet leeg zijn."
            self.feedback_timer = 3.0
            self.name_buffer = self.app.active_profile.display_name
            return
        self.app.active_profile.display_name = new_name
        self.app.save_profiles()
        self.feedback_message = "Naam opgeslagen."
        self.feedback_timer = 3.0

    def _handle_back(self) -> None:
        from .main_menu import MainMenuScene

        if self.has_unsaved_changes:
            self._save_settings()
        self.app.change_scene(MainMenuScene)

    def _save_settings(self) -> None:
        self.app.settings = self.settings.clone()
        self.app.save_settings()
        self.has_unsaved_changes = False
        self.feedback_message = "Instellingen opgeslagen."
        self.feedback_timer = 3.0

    def _show_support_message(self) -> None:
        self.feedback_message = "Bedankt! Koffielink volgt binnenkort."
        self.feedback_timer = 3.0

    def update(self, delta_time: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer = max(self.feedback_timer - delta_time, 0.0)

    def _apply_music_volume(self) -> None:
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(1.0 if self.settings.music_enabled else 0.0)


__all__ = ["SettingsScene"]
