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
from ..avatar_utils import load_avatar_surface, apply_round_corners
from .base import Scene


class SettingsScene(Scene):
    """Interactive settings dashboard for the multiplication game."""

    LANGUAGE_OPTIONS: Sequence[str] = ("nl", "en")

    FEEDBACK_OPTIONS: Sequence[str] = ("warm", "compact")

    SPEED_LABELS: Sequence[str] = ("Slak", "Schildpad", "Haas", "Cheeta")
    QUESTION_CHOICES: Sequence[int] = (30, 50, 100)
    TABLE_COLS: int = 5
    TABLE_BUTTON_SIZE: Tuple[int, int] = (60, 48)
    BUTTON_HEIGHT: int = 52

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
        self.avatar_rects: List[Tuple[str, pygame.Rect]] = []
        self.avatar_surface_cache: Dict[str, pygame.Surface | None] = {}
        self.avatar_cell_size = 108
        self.avatar_thumbnail_size = 78
        self.avatar_columns = 5
        active_profile = self.app.active_profile
        avatar_default = self.app.default_avatar_filename()
        self.selected_avatar = (
            active_profile.avatar_filename if active_profile else avatar_default
        ) or avatar_default

        self.name_input_active = False
        self.name_buffer = active_profile.display_name if active_profile else ""
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

        for filename, rect in self.avatar_rects:
            if rect.collidepoint(content_pos):
                self._select_avatar(filename)
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
        header_bottom = self._draw_header(surface)
        y = header_bottom + self.section_spacing * 2
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

    def _draw_header(self, surface: pygame.Surface) -> int:
        margin = settings.SCREEN_MARGIN
        back_right = (self.back_top_rect.right + 24) if self.back_top_rect else margin
        title_text = self.tr("settings.title", default="Instellingen")
        title = self.title_font.render(title_text, True, settings.COLOR_TEXT_PRIMARY)
        title_rect = title.get_rect(topleft=(back_right, margin - 20))
        surface.blit(title, title_rect)
        subtitle_text = self.tr("settings.subtitle", default="Pas het spel aan op jouw gezin.")
        subtitle = self.helper_font.render(subtitle_text, True, settings.COLOR_TEXT_DIM)
        subtitle_rect = subtitle.get_rect(topleft=(back_right + 6, margin + 24))
        surface.blit(subtitle, subtitle_rect)

        return max(title_rect.bottom, subtitle_rect.bottom)

    def _draw_card(self, surface: pygame.Surface, top: int, height: int) -> pygame.Rect:
        margin = settings.SCREEN_MARGIN
        rect = pygame.Rect(margin, top, surface.get_width() - margin * 2, height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, rect, border_radius=32)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, rect, width=3, border_radius=32)
        return rect

    def _draw_back_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        label_text = self.tr("common.back", default="Terug")
        label = self.helper_font.render(label_text, True, settings.COLOR_TEXT_PRIMARY)
        padding_x = 32
        padding_y = 18
        width = label.get_width() + padding_x * 2
        height = label.get_height() + padding_y * 2
        rect = pygame.Rect(margin, margin + 6, width, height)
        palette = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }
        hover = rect.collidepoint(self.pointer_content_pos)
        face_rect = draw_glossy_button(
            surface,
            rect,
            palette,
            selected=False,
            hover=hover,
            corner_radius=28,
        )
        surface.blit(label, label.get_rect(center=face_rect.center))
        self.back_top_rect = rect

    def _draw_audio_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        toggle_height = 48
        total_height = int(inner * 2 + heading_h + self.section_spacing + toggle_height)
        card = self._draw_card(surface, top, total_height)
        heading_text = self.tr("settings.sections.audio", default="Geluid")
        heading = self.section_font.render(heading_text, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        toggle_y = card.top + inner + heading_h + self.section_spacing
        self.music_toggle_rect = self._draw_toggle(
            surface,
            card.left + inner,
            toggle_y,
            self.tr("settings.audio.music", default="Muziek"),
            self.settings.music_enabled,
        )
        self.effects_toggle_rect = self._draw_toggle(
            surface,
            self.music_toggle_rect.right + self.section_spacing,
            toggle_y,
            self.tr("settings.audio.effects", default="Effecten"),
            self.settings.effects_enabled,
        )
        return card.bottom

    def _draw_defaults_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        label_h = self.option_font.get_height()
        button_width, button_height = self.TABLE_BUTTON_SIZE
        rows = (10 + self.TABLE_COLS - 1) // self.TABLE_COLS
        grid_height = rows * button_height + (rows - 1) * self.grid_spacing
        grid_width = self.TABLE_COLS * button_width + (self.TABLE_COLS - 1) * self.grid_spacing

        button_gap = self.grid_spacing
        small_button_height = self.BUTTON_HEIGHT - 8
        speed_column_height = label_h + button_gap + len(self.SPEED_LABELS) * small_button_height + max(len(self.SPEED_LABELS) - 1, 0) * button_gap
        questions_column_height = label_h + button_gap + len(self.QUESTION_CHOICES) * small_button_height + max(len(self.QUESTION_CHOICES) - 1, 0) * button_gap

        left_body_height = (
            label_h
            + button_gap
            + grid_height
            + self.section_spacing
            + label_h
            + button_gap
            + grid_height
        )
        right_body_height = max(speed_column_height, questions_column_height)

        height_needed = heading_h + self.section_spacing + max(left_body_height, right_body_height)
        total_height = int(inner * 2 + height_needed)
        card = self._draw_card(surface, top, total_height)

        heading_text = self.tr("settings.sections.defaults", default="Standaard instellingen")
        heading = self.section_font.render(heading_text, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        content_top = card.top + inner + heading_h + self.section_spacing
        left_x = card.left + inner
        right_x = left_x + grid_width + self.section_spacing * 3

        # Practice tables -------------------------------------------------
        practice_title_surface = self.option_font.render(
            self.tr("settings.defaults.practice_tables", default="Oefenen tafels"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        practice_title_rect = practice_title_surface.get_rect(topleft=(left_x, content_top))
        surface.blit(practice_title_surface, practice_title_rect)
        practice_grid_top = practice_title_rect.bottom + button_gap
        self.practice_table_rects = self._draw_table_grid(
            surface,
            origin=(left_x, practice_grid_top),
            selected=self.settings.default_practice_tables,
        )

        # Test tables -----------------------------------------------------
        test_title_top = practice_grid_top + grid_height + self.section_spacing
        test_title_surface = self.option_font.render(
            self.tr("settings.defaults.test_tables", default="Test tafels"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        test_title_rect = test_title_surface.get_rect(topleft=(left_x, test_title_top))
        surface.blit(test_title_surface, test_title_rect)
        test_grid_top = test_title_rect.bottom + button_gap
        self.test_table_rects = self._draw_table_grid(
            surface,
            origin=(left_x, test_grid_top),
            selected=self.settings.default_test_tables,
        )

        # Speed column ----------------------------------------------------
        self.speed_rects = {}
        speed_title_surface = self.option_font.render(
            self.tr("settings.defaults.speed", default="Snelheid"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        speed_title_rect = speed_title_surface.get_rect(topleft=(right_x, content_top))
        surface.blit(speed_title_surface, speed_title_rect)

        speed_button_width = 200
        speed_button_top = speed_title_rect.bottom + button_gap
        for index, label in enumerate(self.SPEED_LABELS):
            rect = pygame.Rect(
                right_x,
                speed_button_top + index * (small_button_height + button_gap),
                speed_button_width,
                small_button_height,
            )
            selected = self.settings.default_test_speed == label
            display = self.tr(f"test_setup.speed.{label}.label", default=label)
            self.speed_rects[label] = self._draw_small_button(surface, rect, display, selected)

        # Question count column ------------------------------------------
        questions_x = right_x + speed_button_width + self.section_spacing
        questions_title_surface = self.option_font.render(
            self.tr("settings.defaults.questions", default="Aantal vragen"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        questions_title_rect = questions_title_surface.get_rect(topleft=(questions_x, content_top))
        surface.blit(questions_title_surface, questions_title_rect)

        questions_button_top = questions_title_rect.bottom + button_gap
        button_width_questions = 140
        self.question_rects = {}
        for index, quantity in enumerate(self.QUESTION_CHOICES):
            rect = pygame.Rect(
                questions_x,
                questions_button_top + index * (small_button_height + button_gap),
                button_width_questions,
                small_button_height,
            )
            selected = self.settings.default_test_questions == quantity
            self.question_rects[quantity] = self._draw_small_button(surface, rect, str(quantity), selected)

        return card.bottom

    def _draw_feedback_language_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        label_width = 220
        button_height = 48
        row_gap = self.section_spacing

        content_height = heading_h + row_gap + button_height + row_gap + button_height + row_gap + button_height
        card = self._draw_card(surface, top, int(inner * 2 + content_height))

        label_x = card.left + inner
        value_x = label_x + label_width
        row_top = card.top + inner

        heading = self.section_font.render(
            self.tr("settings.sections.feedback", default="Feedback & taal"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(label_x, row_top)))
        row_top += heading_h + row_gap

        hints_label = self.option_font.render(
            self.tr("settings.feedback.hints", default="Hints"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(hints_label, hints_label.get_rect(topleft=(label_x, row_top)))
        self.feedback_option_rects = {}
        x = value_x
        for option in self.FEEDBACK_OPTIONS:
            rect = pygame.Rect(x, row_top - 4, 200, button_height)
            selected = self.settings.feedback_style == option
            label_text = self.tr(
                f"settings.feedback.options.{option}",
                default={
                    "warm": "Warme hints",
                    "compact": "Korte hints",
                }[option],
            )
            self.feedback_option_rects[option] = self._draw_small_button(surface, rect, label_text, selected)
            x += rect.width + self.section_spacing
        row_top += button_height + row_gap

        language_label = self.option_font.render(
            self.tr("settings.feedback.language", default="Taal"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(language_label, language_label.get_rect(topleft=(label_x, row_top)))
        self.language_rects = {}
        x = value_x
        for code in self.LANGUAGE_OPTIONS:
            rect = pygame.Rect(x, row_top - 4, 180, 44)
            selected = self.settings.language == code
            label_text = self.tr(
                f"settings.feedback.languages.{code}",
                default={
                    "nl": "Nederlands",
                    "en": "English",
                }[code],
            )
            self.language_rects[code] = self._draw_small_button(surface, rect, label_text, selected)
            x += rect.width + self.section_spacing
        row_top += button_height + row_gap

        large_text_label = self.option_font.render(
            self.tr("settings.feedback.large_text", default="Grote tekst"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(large_text_label, large_text_label.get_rect(topleft=(label_x, row_top)))
        self.large_text_toggle_rect = self._draw_toggle(
            surface,
            value_x,
            row_top - 4,
            self.tr("common.toggle.on", default="Aan"),
            self.settings.large_text,
        )
        return card.bottom

    def _draw_profile_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        label_h = self.option_font.get_height()
        input_height = 52

        avatar_options = self.app.list_avatar_filenames()
        active_avatar = self.app.active_profile.avatar_filename or self.app.default_avatar_filename()
        if active_avatar and active_avatar not in avatar_options:
            avatar_options = avatar_options + [active_avatar]
        avatar_options = list(dict.fromkeys(avatar_options))
        if active_avatar and active_avatar != self.selected_avatar:
            self.selected_avatar = active_avatar
        if not self.selected_avatar and avatar_options:
            self.selected_avatar = avatar_options[0]
        avatar_rows = (len(avatar_options) + self.avatar_columns - 1) // max(self.avatar_columns, 1)
        avatar_cell = self.avatar_cell_size
        avatar_spacing = self.grid_spacing
        avatar_block_height = 0
        if avatar_rows > 0:
            avatar_block_height = (
                self.section_spacing
                + label_h
                + avatar_spacing
                + avatar_rows * avatar_cell
                + max(avatar_rows - 1, 0) * avatar_spacing
            )

        button_block_height = self.section_spacing + 56 + 68 + 56

        total_height = int(
            inner * 2
            + heading_h
            + self.section_spacing
            + label_h
            + self.grid_spacing
            + input_height
            + avatar_block_height
            + button_block_height
        )

        card = self._draw_card(surface, top, total_height)
        heading = self.section_font.render(
            self.tr("settings.sections.profiles", default="Profielen"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        name_label = self.option_font.render(
            self.tr("settings.profiles.active_name", default="Naam actief profiel"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        name_top = card.top + inner + heading.get_height() + self.section_spacing
        surface.blit(name_label, name_label.get_rect(topleft=(card.left + inner, name_top)))

        input_rect = pygame.Rect(card.left + inner, name_top + name_label.get_height() + self.grid_spacing, 360, input_height)
        color = settings.COLOR_SELECTION if self.name_input_active else settings.COLOR_CARD_INACTIVE
        pygame.draw.rect(surface, color, input_rect, border_radius=18)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, input_rect, width=2, border_radius=18)
        text_surface = self.value_font.render(self.name_buffer or " ", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text_surface, text_surface.get_rect(midleft=(input_rect.left + 18, input_rect.centery)))
        if self.name_input_active:
            cursor_x = input_rect.left + 18 + text_surface.get_width() + 4
            pygame.draw.line(surface, settings.COLOR_TEXT_PRIMARY, (cursor_x, input_rect.top + 10), (cursor_x, input_rect.bottom - 10), 2)
        self.name_input_rect = input_rect

        avatar_bottom = input_rect.bottom
        self.avatar_rects = []
        if avatar_rows > 0:
            avatar_label = self.option_font.render(
                self.tr("settings.profiles.avatar_label", default="Pick a picture"),
                True,
                settings.COLOR_TEXT_PRIMARY,
            )
            avatar_label_pos = (card.left + inner, input_rect.bottom + self.section_spacing)
            surface.blit(avatar_label, avatar_label.get_rect(topleft=avatar_label_pos))

            grid_top = avatar_label.get_rect(topleft=avatar_label_pos).bottom + avatar_spacing
            start_x = card.left + inner
            for index, filename in enumerate(avatar_options):
                col = index % self.avatar_columns
                row = index // self.avatar_columns
                rect = pygame.Rect(
                    start_x + col * (avatar_cell + avatar_spacing),
                    grid_top + row * (avatar_cell + avatar_spacing),
                    avatar_cell,
                    avatar_cell,
                )
                hover = rect.collidepoint(self.pointer_content_pos)
                selected = filename == self.selected_avatar
                palette = (
                    {
                        "top": (216, 196, 255),
                        "bottom": (176, 148, 227),
                        "border": (126, 98, 192),
                        "shadow": (102, 78, 152),
                    }
                    if selected
                    else {
                        "top": (242, 236, 228),
                        "bottom": (209, 197, 184),
                        "border": (168, 156, 145),
                        "shadow": (150, 140, 130),
                    }
                )
                face_rect = draw_glossy_button(
                    surface,
                    rect,
                    palette,
                    selected=selected,
                    hover=hover,
                    corner_radius=28,
                )
                avatar_surface = self._get_avatar_surface(filename)
                if avatar_surface is not None:
                    surface.blit(avatar_surface, avatar_surface.get_rect(center=face_rect.center))
                self.avatar_rects.append((filename, rect))
                avatar_bottom = max(avatar_bottom, rect.bottom)

        avatar_bottom = max(avatar_bottom, input_rect.bottom)
        self.profile_button_rects = {}
        palette = {
            "top": (255, 170, 59),
            "bottom": (244, 110, 34),
            "border": (172, 78, 23),
            "shadow": (138, 62, 19),
        }
        button_row_top = avatar_bottom + self.section_spacing
        button_width = 240
        column_gap = self.section_spacing * 2
        specs = [
            (
                "save_name",
                card.left + inner,
                button_row_top,
                self.tr("settings.profiles.buttons.save_name", default="Bewaar naam"),
            ),
            (
                "new_profile",
                card.left + inner + button_width + column_gap,
                button_row_top,
                self.tr("settings.profiles.buttons.new_profile", default="Nieuw profiel"),
            ),
            (
                "reset_coins",
                card.left + inner,
                button_row_top + 68,
                self.tr("settings.profiles.buttons.reset_coins", default="Reset munten"),
            ),
            (
                "delete_profile",
                card.left + inner + button_width + column_gap,
                button_row_top + 68,
                self.tr("settings.profiles.buttons.delete_profile", default="Verwijder profiel"),
            ),
        ]
        for key, x, y, label in specs:
            rect = pygame.Rect(x, y, button_width, 56)
            self.profile_button_rects[key] = rect
            face_rect = draw_glossy_button(
                surface,
                rect,
                palette,
                selected=False,
                hover=self._is_hover(rect),
                corner_radius=24,
            )
            text = self.button_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(center=face_rect.center))
        return card.bottom

    def _get_avatar_surface(self, filename: str) -> pygame.Surface | None:
        if filename in self.avatar_surface_cache:
            return self.avatar_surface_cache[filename]

        path = self.app.assets_dir / "images" / filename
        surface = load_avatar_surface(path, self.avatar_thumbnail_size, self._avatar_corner_radius())
        if surface is None:
            surface = self._generate_avatar_placeholder()
        self.avatar_surface_cache[filename] = surface
        return surface

    def _draw_data_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        button_width = 320
        button_height = 56
        row_gap = self.section_spacing

        rows = [
            (
                "export_scores",
                self.tr("settings.data.buttons.export_scores.label", default="Exporteer scores"),
                self.tr(
                    "settings.data.buttons.export_scores.description",
                    default="Slaat alle testresultaten op als JSON-bestand.",
                ),
            ),
            (
                "reset_scores",
                self.tr("settings.data.buttons.reset_scores.label", default="Reset scores actief profiel"),
                self.tr(
                    "settings.data.buttons.reset_scores.description",
                    default="Verwijdert alleen resultaten van het gekozen profiel.",
                ),
            ),
            (
                "reset_all",
                self.tr("settings.data.buttons.reset_all.label", default="Complete reset"),
                self.tr(
                    "settings.data.buttons.reset_all.description",
                    default="Wist alle profielen en scores permanent.",
                ),
            ),
        ]
        content_height = heading_h + row_gap + len(rows) * (button_height + row_gap) + self.helper_font.get_height()
        card = self._draw_card(surface, top, int(inner * 2 + content_height))

        heading = self.section_font.render(
            self.tr("settings.sections.data", default="Data & privacy"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        row_top = card.top + inner + heading_h + row_gap
        description_color = settings.COLOR_TEXT_PRIMARY
        self.data_button_rects = {}

        for key, label, description in rows:
            rect = pygame.Rect(card.left + inner, row_top, button_width, button_height)
            self.data_button_rects[key] = rect
            palette = {
                "export_scores": {"top": (84, 188, 255), "bottom": (31, 117, 232), "border": (27, 86, 182), "shadow": (21, 73, 152)},
                "reset_scores": {"top": (244, 110, 34), "bottom": (214, 78, 20), "border": (172, 58, 18), "shadow": (138, 44, 18)},
                "reset_all": {"top": (255, 131, 131), "bottom": (220, 70, 70), "border": (168, 48, 48), "shadow": (140, 36, 36)},
            }[key]
            face_rect = draw_glossy_button(
                surface,
                rect,
                palette,
                selected=False,
                hover=self._is_hover(rect),
                corner_radius=24,
            )
            text_surface = self.button_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text_surface, text_surface.get_rect(center=face_rect.center))

            description_surface = self.helper_font.render(description, True, description_color)
            desc_rect = description_surface.get_rect(topleft=(face_rect.right + self.section_spacing, face_rect.centery - description_surface.get_height() // 2))
            surface.blit(description_surface, desc_rect)

            row_top += button_height + row_gap

        info = self.helper_font.render(
            self.tr(
                "settings.data.warning",
                default="Let op: resets vragen geen bevestiging, gebruik ze bewust!",
            ),
            True,
            settings.COLOR_TEXT_DIM,
        )
        surface.blit(info, info.get_rect(topleft=(card.left + inner, row_top)))
        return card.bottom

    def _draw_support_card(self, surface: pygame.Surface, top: int) -> int:
        inner = self.card_inner_margin
        heading_h = self.section_font.get_height()
        lines = self.tr_list(
            "settings.support.lines",
            default=[
                "Dit spel is gemaakt om kinderen spelenderwijs tafels te oefenen.",
                "Geïnspireerd het totaal geen zin hebben om tafels te oefenen van mijn dochter.",
                "Ik wilde graag een spelletje opzetten voor haar waarbij leren wordt beloond en er weinig afleiding is.",
                "Belangrijker nog: geen advertenties, geen tracking, maar gewoon vrolijk en simpel leren.",
                "Vind je het waardevol? Vertel het vooral door! Echt heel blij? Dan mag je me altijd trakteren op een koffie ;)",
            ],
        )
        line_surfaces = [self.helper_font.render(line, True, settings.COLOR_TEXT_PRIMARY) for line in lines]
        content_height = heading_h + self.section_spacing
        for surface_line in line_surfaces:
            content_height += surface_line.get_height() + 6
        content_height += self.section_spacing + 56

        total_height = int(inner * 2 + content_height)
        card = self._draw_card(surface, top, total_height)
        heading = self.section_font.render(
            self.tr(
                "settings.support.heading",
                default="Voor de mama's, papa's, verzorgers en onderwijzers!",
            ),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(card.left + inner, card.top + inner)))

        y = card.top + inner + heading_h + self.grid_spacing
        for text_surface in line_surfaces:
            surface.blit(text_surface, text_surface.get_rect(topleft=(card.left + inner, y)))
            y += text_surface.get_height() + 6

        self.buy_rect = pygame.Rect(card.right - inner - 220, card.bottom - inner - 56, 220, 56)
        face_rect = draw_glossy_button(
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
        label = self.button_font.render(
            self.tr("settings.support.cta", default="Koop een koffie"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(label, label.get_rect(center=face_rect.center))

        return card.bottom

    def _draw_footer_buttons(self, surface: pygame.Surface, top: int) -> int:
        margin = settings.SCREEN_MARGIN
        self.save_rect = pygame.Rect(surface.get_width() - margin - 240, top, 240, 60)
        self.footer_back_rect = pygame.Rect(surface.get_width() - margin - 500, top, 240, 60)

        save_face = draw_glossy_button(
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
        save_label = self.tr(
            "settings.save.saved" if not self.has_unsaved_changes else "settings.save.save_changes",
            default="Opgeslagen" if not self.has_unsaved_changes else "Instellingen opslaan",
        )
        save_text = self.button_font.render(save_label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(save_text, save_text.get_rect(center=save_face.center))

        back_face = draw_glossy_button(
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
        back_text = self.button_font.render(
            self.tr("common.back", default="Terug"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(back_text, back_text.get_rect(center=back_face.center))

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
        face_rect = draw_glossy_button(
            surface,
            rect,
            palette,
            selected=False,
            hover=self._is_hover(rect),
            corner_radius=24,
        )
        text = self.option_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=face_rect.center))
        return rect

    def _draw_small_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str, selected: bool) -> pygame.Rect:
        palette = {
            "top": (137, 214, 255) if selected else (242, 236, 228),
            "bottom": (73, 158, 236) if selected else (209, 197, 184),
            "border": (45, 118, 189) if selected else (168, 156, 145),
            "shadow": (41, 99, 156) if selected else (150, 140, 130),
        }
        face_rect = draw_glossy_button(
            surface,
            rect,
            palette,
            selected=selected,
            hover=self._is_hover(rect),
            corner_radius=20,
        )
        text = self.helper_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=face_rect.center))
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
        spacing = self.grid_spacing
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
            face_rect = draw_glossy_button(
                surface,
                rect,
                palette,
                selected=is_selected,
                hover=self._is_hover(rect),
                corner_radius=18,
            )
            text = self.helper_font.render(str(value), True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(center=face_rect.center))
            rects.append((rect, value))
        return rects

    def _is_hover(self, rect: pygame.Rect) -> bool:
        return rect.collidepoint(self.pointer_content_pos)

    def _avatar_corner_radius(self) -> int:
        return max(8, int(self.avatar_thumbnail_size * 32 / max(self.avatar_cell_size, 1)))

    def _generate_avatar_placeholder(self) -> pygame.Surface:
        size = self.avatar_thumbnail_size
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        radius = self._avatar_corner_radius()
        pygame.draw.rect(surface, (240, 240, 240), surface.get_rect(), border_radius=radius)
        pygame.draw.rect(surface, (210, 210, 210), surface.get_rect(), width=4, border_radius=radius)
        letter = (self.app.active_profile.display_name[:1] if self.app.active_profile else "?").upper()
        font = settings.load_title_font(30)
        text = font.render(letter, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=(size // 2, size // 2)))
        return apply_round_corners(surface, radius)

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

    def _select_avatar(self, filename: str) -> None:
        if not filename:
            return
        profile = self.app.active_profile
        if profile is None:
            return
        current = profile.avatar_filename
        if filename == current:
            return
        self.selected_avatar = filename
        profile.avatar_filename = filename
        self.app.profiles[self.app.active_profile_index] = profile
        self.app.save_profiles()
        self.app.update_gradient_for_avatar(filename)
        self.feedback_message = self.tr(
            "settings.profiles.messages.avatar_saved",
            default="Avatar gewijzigd.",
        )
        self.feedback_timer = 3.0

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
            self.feedback_message = self.tr(
                "settings.profiles.messages.coins_reset",
                default="Munten teruggezet naar 0.",
            )
            self.feedback_timer = 3.0
            return
        if action == "delete_profile":
            if len(self.app.profiles) <= 1:
                self.feedback_message = self.tr(
                    "settings.profiles.messages.needs_one",
                    default="Je hebt minimaal één profiel nodig.",
                )
                self.feedback_timer = 3.0
                return
            profile = self.app.active_profile
            self.app.profiles = [p for p in self.app.profiles if p.identifier != profile.identifier]
            self.app.active_profile_index = 0
            self.app.active_profile = self.app.profiles[0]
            self.app.save_profiles()
            self.app.scores.clear_profile(profile.identifier)
            self.name_buffer = self.app.active_profile.display_name
            self.feedback_message = self.tr(
                "settings.profiles.messages.profile_deleted",
                default="Profiel verwijderd.",
            )
            self.feedback_timer = 3.0

    def _create_profile(self) -> None:
        identifier = self._generate_profile_id()
        display_name = self.tr(
            "settings.profiles.default_name",
            default="Speler {number}",
            number=len(self.app.profiles) + 1,
        )
        from ..models import PlayerProfile

        default_avatar = self.app.default_avatar_filename()
        profile = PlayerProfile(identifier, display_name, default_avatar, coins=0)
        self.app.profiles.append(profile)
        self.app.active_profile_index = len(self.app.profiles) - 1
        self.app.active_profile = profile
        self.app.save_profiles()
        self.name_buffer = display_name
        self.selected_avatar = profile.avatar_filename
        self.feedback_message = self.tr(
            "settings.profiles.messages.profile_created",
            default="Nieuw profiel aangemaakt.",
        )
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
            self.feedback_message = self.tr(
                "settings.data.messages.reset_scores",
                default="Scores van dit profiel gewist.",
            )
            self.feedback_timer = 3.0
        elif action == "reset_all":
            self.app.scores.clear_all()
            self.app.save_profiles()
            self.feedback_message = self.tr(
                "settings.data.messages.reset_all",
                default="Alle data gewist.",
            )
            self.feedback_timer = 3.0

    def _export_scores(self) -> None:
        export_dir: Path = self.app.data_dir
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = export_dir / f"scores_export_{timestamp}.json"
        export_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.app.scores.all_scores(), indent=2), encoding="utf-8")
        self.feedback_message = self.tr(
            "settings.data.messages.exported",
            default="Scores opgeslagen naar {filename}.",
            filename=path.name,
        )
        self.feedback_timer = 3.0

    def _apply_name_change(self) -> None:
        new_name = self.name_buffer.strip()
        if not new_name:
            self.feedback_message = self.tr(
                "settings.profiles.messages.name_empty",
                default="Naam mag niet leeg zijn.",
            )
            self.feedback_timer = 3.0
            self.name_buffer = self.app.active_profile.display_name
            return
        self.app.active_profile.display_name = new_name
        self.app.save_profiles()
        self.feedback_message = self.tr(
            "settings.profiles.messages.name_saved",
            default="Naam opgeslagen.",
        )
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
        self.feedback_message = self.tr(
            "settings.save.confirmation",
            default="Instellingen opgeslagen.",
        )
        self.feedback_timer = 3.0

    def _show_support_message(self) -> None:
        self.feedback_message = self.tr(
            "settings.support.thank_you",
            default="Bedankt! Koffielink volgt binnenkort.",
        )
        self.feedback_timer = 3.0

    def update(self, delta_time: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer = max(self.feedback_timer - delta_time, 0.0)

    def _apply_music_volume(self) -> None:
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(1.0 if self.settings.music_enabled else 0.0)


__all__ = ["SettingsScene"]
