"""Onboarding scene for first-time profile creation."""

from __future__ import annotations

import random
import string
from typing import List, Tuple

import pygame

from .. import settings
from ..models import PlayerProfile
from ..ui import draw_glossy_button
from ..avatar_utils import load_avatar_surface, apply_round_corners
from .base import Scene


class ProfileOnboardingScene(Scene):
    """Guides brand-new players through creating their first profile."""

    INPUT_HEIGHT = 64
    AVATAR_CELL = 112
    AVATAR_SPACING = 18
    AVATAR_THUMB = 82

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.title_font = settings.load_title_font(64)
        self.subtitle_font = settings.load_font(30)
        self.label_font = settings.load_font(28)
        self.input_font = settings.load_font(32)
        self.button_font = settings.load_font(32)
        self.feedback_font = settings.load_font(24)

        self.name_buffer = ""
        self.name_input_active = True
        self.feedback_message = ""
        self.feedback_timer = 0.0

        self.section_spacing = 32

        self.avatar_filenames: List[str] = list(dict.fromkeys(app.list_avatar_filenames()))
        if not self.avatar_filenames:
            self.avatar_filenames = [""]
        self.selected_avatar = self.avatar_filenames[0] if self.avatar_filenames else ""

        self.avatar_rects: List[Tuple[str, pygame.Rect]] = []
        self.avatar_cache: dict[str, pygame.Surface | None] = {}
        self.continue_rect: pygame.Rect | None = None
        self.name_input_rect: pygame.Rect | None = None

        if self.selected_avatar:
            self.app.update_gradient_for_avatar(self.selected_avatar)

    # Event handling -------------------------------------------------
    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.name_input_active and event.key not in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self._handle_name_input(event)
                    continue
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._create_profile()
                    continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._handle_mouse_click(event.pos):
                    continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self.name_input_active = False

    def _handle_mouse_click(self, position: Tuple[int, int]) -> bool:
        if self.continue_rect and self.continue_rect.collidepoint(position):
            self._create_profile()
            return True

        if self.name_input_rect and self.name_input_rect.collidepoint(position):
            self.name_input_active = True
            return True

        for filename, rect in self.avatar_rects:
            if rect.collidepoint(position):
                self.selected_avatar = filename
                self.feedback_message = ""
                self.app.update_gradient_for_avatar(filename)
                return True
        self.name_input_active = False
        return False

    def _handle_name_input(self, event: pygame.event.Event) -> None:
        if self.feedback_message:
            self.feedback_message = ""
        if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
            self.name_buffer = self.name_buffer[:-1]
            return
        if event.key == pygame.K_TAB:
            self.name_input_active = False
            return
        if event.unicode and len(self.name_buffer) < 18:
            if event.unicode.isprintable():
                self.name_buffer += event.unicode

    # Update ---------------------------------------------------------
    def update(self, delta_time: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer = max(self.feedback_timer - delta_time, 0.0)
            if self.feedback_timer == 0:
                self.feedback_message = ""

    # Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._draw_content(surface)

    def _draw_content(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        width = surface.get_width()
        height = surface.get_height()

        title_text = self.tr("onboarding.title", default="Welkom bij Tafelhelden!")
        title_surface = self.title_font.render(title_text, True, settings.COLOR_TEXT_PRIMARY)
        subtitle_surface = self.subtitle_font.render(
            self.tr(
                "onboarding.subtitle",
                default="Laten we een profiel maken zodat je munten en voortgang kunt bijhouden.",
            ),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )

        surface.blit(title_surface, title_surface.get_rect(center=(width // 2, margin + 40)))
        surface.blit(subtitle_surface, subtitle_surface.get_rect(center=(width // 2, margin + 110)))

        card_width = min(900, width - margin * 2)
        card_left = (width - card_width) // 2
        card_top = margin + 160
        inner = 36

        current_columns = max(1, min(5, (card_width - inner * 2) // (self.AVATAR_CELL)))
        if current_columns == 0:
            current_columns = 1
        total_avatars = len(self.avatar_filenames)
        avatar_rows = (total_avatars + current_columns - 1) // current_columns
        avatar_block_height = 0
        if total_avatars:
            avatar_block_height = (
                self.section_spacing
                + self.label_font.get_height()
                + self.AVATAR_SPACING
                + avatar_rows * self.AVATAR_CELL
                + max(0, avatar_rows - 1) * self.AVATAR_SPACING
            )

        card_height = (
            inner * 2
            + self.label_font.get_height()
            + self.INPUT_HEIGHT
            + self.section_spacing
            + avatar_block_height
            + self.section_spacing
            + 86
            + 40
        )

        name_label = self.label_font.render(
            self.tr("onboarding.name_label", default="Hoe heet je?"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        name_label_pos = (card_left + inner, card_top + inner)
        input_top = name_label_pos[1] + name_label.get_height() + 12
        input_rect = pygame.Rect(card_left + inner, input_top, card_width - inner * 2, self.INPUT_HEIGHT)
        self.name_input_rect = input_rect

        placeholder = self.tr("onboarding.name_placeholder", default="Type your name")
        display_text = self.name_buffer if self.name_buffer else placeholder
        color = settings.COLOR_TEXT_PRIMARY if self.name_buffer else (225, 225, 225)
        text_surface = self.input_font.render(display_text, True, color)

        error_surface: pygame.Surface | None = None
        error_height = 0
        if self.feedback_message and not self.name_buffer:
            error_surface = self.feedback_font.render(self.feedback_message, True, (255, 90, 90))
            error_height = error_surface.get_height() + 18

        card_rect = pygame.Rect(card_left, card_top, card_width, card_height + error_height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card_rect, border_radius=36)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, card_rect, width=3, border_radius=36)

        surface.blit(name_label, name_label.get_rect(topleft=name_label_pos))

        border_color = settings.COLOR_SELECTION if self.name_input_active else settings.COLOR_ACCENT
        pygame.draw.rect(surface, settings.COLOR_CARD_INACTIVE, input_rect, border_radius=28)
        pygame.draw.rect(surface, border_color, input_rect, width=3, border_radius=28)

        surface.blit(text_surface, text_surface.get_rect(midleft=(input_rect.left + 24, input_rect.centery)))
        if self.name_input_active and self.name_buffer:
            cursor_x = input_rect.left + 24 + text_surface.get_width() + 4
            pygame.draw.line(surface, settings.COLOR_TEXT_PRIMARY, (cursor_x, input_rect.top + 12), (cursor_x, input_rect.bottom - 12), 3)

        if error_surface is not None:
            surface.blit(error_surface, error_surface.get_rect(topleft=(card_left + inner, input_rect.bottom + 12)))

        avatar_top = input_rect.bottom + self.section_spacing + error_height
        self.avatar_rects = []
        if total_avatars:
            avatar_label = self.label_font.render(
                self.tr("onboarding.avatar_label", default="Pick a picture"),
                True,
                settings.COLOR_TEXT_PRIMARY,
            )
            surface.blit(avatar_label, avatar_label.get_rect(topleft=(card_left + inner, avatar_top)))
            grid_top = avatar_top + avatar_label.get_height() + self.AVATAR_SPACING
            cell = self.AVATAR_CELL
            spacing = self.AVATAR_SPACING
            start_x = card_left + inner
            for index, filename in enumerate(self.avatar_filenames):
                col = index % current_columns
                row = index // current_columns
                rect = pygame.Rect(
                    start_x + col * (cell + spacing),
                    grid_top + row * (cell + spacing),
                    cell,
                    cell,
                )
                hover = rect.collidepoint(pygame.mouse.get_pos())
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
                face = draw_glossy_button(
                    surface,
                    rect,
                    palette,
                    selected=selected,
                    hover=hover,
                    corner_radius=32,
                )
                avatar_surface = self._get_avatar_surface(filename)
                if avatar_surface is not None:
                    surface.blit(avatar_surface, avatar_surface.get_rect(center=face.center))
                self.avatar_rects.append((filename, rect))
            avatar_bottom = grid_top + avatar_rows * cell + max(0, avatar_rows - 1) * spacing
        else:
            avatar_bottom = avatar_top

        button_top = avatar_bottom + self.section_spacing
        button_rect = pygame.Rect(card_left + inner, button_top, card_width - inner * 2, 86)
        mouse_pos = pygame.mouse.get_pos()
        face_rect = draw_glossy_button(
            surface,
            button_rect,
            {
                "top": (116, 227, 128),
                "bottom": (63, 186, 94),
                "border": (36, 140, 67),
                "shadow": (45, 122, 59),
            },
            selected=False,
            hover=button_rect.collidepoint(mouse_pos),
            corner_radius=32,
        )
        button_label = self.button_font.render(
            self.tr("onboarding.start_button", default="Ik ben klaar!"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(button_label, button_label.get_rect(center=face_rect.center))
        self.continue_rect = button_rect

        if self.feedback_message and (self.name_buffer or not self.name_input_active):
            feedback_surface = self.feedback_font.render(self.feedback_message, True, (255, 90, 90))
            surface.blit(feedback_surface, feedback_surface.get_rect(center=(width // 2, card_rect.bottom + 24)))

    # Helpers --------------------------------------------------------
    def _create_profile(self) -> None:
        name = self.name_buffer.strip()
        if not name:
            self._set_feedback(self.tr("onboarding.errors.name_empty", default="Vul een naam in"))
            self.name_input_active = True
            return
        display_name = name.title()
        avatar = self.selected_avatar or self.app.default_avatar_filename()
        identifier = self._generate_identifier(name)
        profile = PlayerProfile(identifier, display_name, avatar, coins=0)
        self.app.profiles.append(profile)
        self.app.active_profile_index = len(self.app.profiles) - 1
        self.app.active_profile = profile
        self.app.save_profiles()
        self.app._apply_profile_style(profile)

        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)

    def _generate_identifier(self, name: str) -> str:
        base = "".join(ch for ch in name.lower() if ch.isalnum()) or "speler"
        candidate = base
        existing = {profile.identifier for profile in self.app.profiles}
        suffix = 1
        while candidate in existing:
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate

    def _set_feedback(self, message: str) -> None:
        self.feedback_message = message
        self.feedback_timer = 3.0

    def _get_avatar_surface(self, filename: str) -> pygame.Surface | None:
        if filename in self.avatar_cache:
            return self.avatar_cache[filename]
        if not filename:
            surface = self._generate_placeholder_avatar()
            self.avatar_cache[filename] = surface
            return surface
        path = self.app.assets_dir / "images" / filename
        surface = load_avatar_surface(path, self.AVATAR_THUMB, self._avatar_corner_radius())
        if surface is None:
            surface = self._generate_placeholder_avatar()
        self.avatar_cache[filename] = surface
        return surface

    def _generate_placeholder_avatar(self) -> pygame.Surface:
        size = self.AVATAR_THUMB
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        radius = self._avatar_corner_radius()
        pygame.draw.rect(surface, (255, 207, 96), surface.get_rect(), border_radius=radius)
        pygame.draw.rect(surface, (255, 175, 64), surface.get_rect(), width=4, border_radius=radius)
        letter = (self.name_buffer[:1] or random.choice(string.ascii_uppercase)).upper()
        font = settings.load_title_font(34)
        text = font.render(letter, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=(size // 2, size // 2)))
        return apply_round_corners(surface, radius)

    def _avatar_corner_radius(self) -> int:
        return max(8, int(self.AVATAR_THUMB * 32 / self.AVATAR_CELL))
