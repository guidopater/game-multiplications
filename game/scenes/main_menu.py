"""Main menu scene with playful visuals."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import pygame

from .. import settings
from ..ui import draw_glossy_button
from .base import Scene


@dataclass(frozen=True)
class MenuOption:
    label: str
    action: str


class MainMenuScene(Scene):
    """Entry scene that lets the player choose what to do."""

    AVATAR_SIZE = 92

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.title_font = settings.load_title_font(72)
        self.subtitle_font = settings.load_font(32)
        self.option_font = settings.load_font(36)
        self.feedback_font = settings.load_font(24)
        self.profile_font = settings.load_font(20)

        self.options: List[MenuOption] = [
            MenuOption(label="Oefenen", action="practice"),
            MenuOption(label="Testen", action="test"),
            MenuOption(label="Hoe deed je het?", action="leaderboard"),
            MenuOption(label="Instellingen", action="settings"),
            MenuOption(label="Afsluiten", action="quit"),
        ]
        self.selected_index = 0
        self.option_rects: List[pygame.Rect] = []

        self.feedback_message = ""
        self.feedback_timer = 0.0
        self._time = 0.0

        # Decorative bubbles drifting in the background.
        self._bubbles = [
            (pygame.Vector2(140, 160), 32, 0.0),
            (pygame.Vector2(820, 220), 48, 1.6),
            (pygame.Vector2(320, 420), 40, 3.2),
            (pygame.Vector2(640, 120), 36, 2.4),
            (pygame.Vector2(900, 380), 54, 0.8),
        ]

        self._avatar_cache: dict[str, pygame.Surface] = {}
        self.profile_rects: List[Tuple[pygame.Rect, str]] = []
        self.button_palette: List[dict[str, tuple[int, int, int]]] = [
            {
                "top": (255, 170, 59),
                "bottom": (244, 110, 34),
                "border": (172, 78, 23),
                "shadow": (173, 69, 19),
            },
            {
                "top": (80, 215, 86),
                "bottom": (40, 158, 66),
                "border": (31, 124, 50),
                "shadow": (24, 112, 46),
            },
            {
                "top": (84, 188, 255),
                "bottom": (31, 117, 232),
                "border": (27, 86, 182),
                "shadow": (21, 73, 152),
            },
            {
                "top": (194, 144, 255),
                "bottom": (145, 92, 224),
                "border": (111, 64, 184),
                "shadow": (89, 53, 152),
            },
            {
                "top": (255, 144, 198),
                "bottom": (235, 91, 150),
                "border": (184, 63, 120),
                "shadow": (152, 52, 102),
            },
        ]
        self.button_size = (420, 96)
        self.button_spacing = 24

    # Event handling -------------------------------------------------
    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_index = (self.selected_index - 1) % len(self.options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_index = (self.selected_index + 1) % len(self.options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.activate_option(self.selected_index)

            elif event.type == pygame.MOUSEMOTION:
                for index, rect in enumerate(self.option_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_index = index
                        break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._handle_profile_click(event.pos):
                    continue
                for index, rect in enumerate(self.option_rects):
                    if rect.collidepoint(event.pos):
                        if hasattr(self.app, "sounds") and "click" in self.app.sounds:
                            self.app.sounds["click"].play()
                        self.activate_option(index)
                        break

    def _handle_profile_click(self, position: Tuple[int, int]) -> bool:
        for rect, profile_id in self.profile_rects:
            if rect.collidepoint(position):
                profile = next((p for p in self.app.profiles if p.identifier == profile_id), None)
                if profile:
                    self.app.set_active_profile(profile)
                    self.feedback_message = f"Hoi {profile.display_name}!"
                    self.feedback_timer = 1.8
                return True
        return False

    # Update ---------------------------------------------------------
    def update(self, delta_time: float) -> None:
        self._time += delta_time
        if self.feedback_timer > 0:
            self.feedback_timer = max(self.feedback_timer - delta_time, 0)
            if self.feedback_timer == 0:
                self.feedback_message = ""

    # Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._draw_bubbles(surface)
        self._draw_title(surface)
        self._draw_options(surface)
        self._draw_feedback(surface)
        self._draw_profile_selector(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        profile = self.app.active_profile
        margin = settings.SCREEN_MARGIN
        left_x = margin
        title = self.title_font.render(f"Hoi {profile.display_name}!", True, settings.COLOR_TEXT_PRIMARY)
        subtitle = self.subtitle_font.render("Waar heb je zin in vandaag?", True, settings.COLOR_TEXT_DIM)

        title_rect = title.get_rect()
        title_rect.topleft = (left_x, margin + 10)
        surface.blit(title, title_rect)

        subtitle_rect = subtitle.get_rect()
        subtitle_rect.topleft = (left_x + 8, title_rect.bottom + 16)
        surface.blit(subtitle, subtitle_rect)

    def _draw_options(self, surface: pygame.Surface) -> None:
        base_y = settings.SCREEN_MARGIN + 160
        button_width, button_height = self.button_size
        self.option_rects = []
        menu_x = (surface.get_width() - button_width) // 2

        mouse_pos = pygame.mouse.get_pos()

        for index, option in enumerate(self.options):
            palette = self.button_palette[index % len(self.button_palette)]
            base_rect = pygame.Rect(
                menu_x,
                base_y + index * (button_height + self.button_spacing),
                button_width,
                button_height,
            )

            is_selected = index == self.selected_index
            is_hover = base_rect.collidepoint(mouse_pos)
            face_rect = draw_glossy_button(surface, base_rect, palette, selected=is_selected, hover=is_hover)

            text_surface = self.option_font.render(option.label, True, (255, 255, 255))
            surface.blit(text_surface, text_surface.get_rect(center=face_rect.center))

            self.option_rects.append(base_rect)

    def _draw_feedback(self, surface: pygame.Surface) -> None:
        if not self.feedback_message:
            return

        alpha = 255 if self.feedback_timer > 1 else int(255 * self.feedback_timer)
        text_surface = self.feedback_font.render(self.feedback_message, True, settings.COLOR_ACCENT_LIGHT)
        text_surface.set_alpha(alpha)
        rect = text_surface.get_rect(center=(surface.get_width() // 2, surface.get_height() - 80))
        surface.blit(text_surface, rect)

    def _draw_bubbles(self, surface: pygame.Surface) -> None:
        for center, radius, phase in self._bubbles:
            offset = math.sin(self._time * 1.2 + phase) * 12
            position = (center.x, center.y + offset)
            pygame.draw.circle(surface, settings.COLOR_ACCENT, position, radius)
            pygame.draw.circle(surface, settings.COLOR_ACCENT_LIGHT, position, radius - 10)

    def _draw_profile_selector(self, surface: pygame.Surface) -> None:
        spacing = 24
        margin = settings.SCREEN_MARGIN
        size = self.AVATAR_SIZE
        total_width = len(self.app.profiles) * size + (len(self.app.profiles) - 1) * spacing
        origin_x = surface.get_width() - margin - total_width
        origin_y = surface.get_height() - margin - size

        label = self.feedback_font.render("Wie speelt er?", True, settings.COLOR_TEXT_DIM)
        label_rect = label.get_rect(bottomright=(surface.get_width() - margin, origin_y - 16))
        surface.blit(label, label_rect)

        self.profile_rects = []
        for index, profile in enumerate(self.app.profiles):
            avatar_surface = self._get_avatar_surface(profile)
            x = origin_x + index * (size + spacing)
            rect = pygame.Rect(x, origin_y, size, size)

            # Background circle
            glow_surface = pygame.Surface((size + 24, size + 24), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surface,
                (255, 255, 255, 80),
                ((size + 24) // 2, (size + 24) // 2),
                (size + 24) // 2,
            )
            surface.blit(glow_surface, (rect.centerx - (size + 24) // 2, rect.centery - (size + 24) // 2))

            is_active = profile.identifier == self.app.active_profile.identifier
            display_surface = avatar_surface if is_active else self._make_inactive_avatar(avatar_surface)
            surface.blit(display_surface, rect)

            border_color = settings.COLOR_SELECTION if is_active else (90, 100, 120)
            pygame.draw.circle(surface, border_color, rect.center, size // 2 + 4, width=4)

            name_color = settings.COLOR_TEXT_PRIMARY if is_active else settings.COLOR_TEXT_DIM
            name_surface = self.profile_font.render(profile.display_name, True, name_color)
            name_rect = name_surface.get_rect(midtop=(rect.centerx, rect.bottom + 6))
            surface.blit(name_surface, name_rect)

            if self.app.coin_icon:
                coin_rect = self.app.coin_icon.get_rect(midtop=(rect.centerx - 20, name_rect.bottom + 6))
                surface.blit(self.app.coin_icon, coin_rect)
                coin_text = self.profile_font.render(str(profile.coins), True, name_color)
                coin_text_rect = coin_text.get_rect(midtop=(coin_rect.centerx + 24, name_rect.bottom + 8))
                surface.blit(coin_text, coin_text_rect)
            else:
                coin_text = self.profile_font.render(f"{profile.coins}", True, name_color)
                surface.blit(coin_text, coin_text.get_rect(midtop=(rect.centerx, name_rect.bottom + 6)))

            self.profile_rects.append((rect, profile.identifier))

    def _get_avatar_surface(self, profile) -> pygame.Surface:
        cached = self._avatar_cache.get(profile.identifier)
        if cached:
            return cached

        avatar_surface: pygame.Surface | None = None

        if profile.avatar_filename:
            path = profile.resolve_avatar_path(self.app.assets_dir)
            try:
                avatar_surface = pygame.image.load(path).convert_alpha()
            except (FileNotFoundError, pygame.error):
                avatar_surface = None

        if avatar_surface is None:
            avatar_surface = self._generate_default_avatar(profile.identifier)

        avatar_surface = pygame.transform.smoothscale(avatar_surface, (self.AVATAR_SIZE, self.AVATAR_SIZE))

        mask = pygame.Surface((self.AVATAR_SIZE, self.AVATAR_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (self.AVATAR_SIZE // 2, self.AVATAR_SIZE // 2), self.AVATAR_SIZE // 2)
        masked = pygame.Surface((self.AVATAR_SIZE, self.AVATAR_SIZE), pygame.SRCALPHA)
        masked.blit(avatar_surface, (0, 0))
        masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self._avatar_cache[profile.identifier] = masked
        return masked

    @staticmethod
    def _make_inactive_avatar(surface: pygame.Surface) -> pygame.Surface:
        faded = surface.copy()
        faded.fill((140, 140, 140, 180), special_flags=pygame.BLEND_RGBA_MULT)
        faded.set_alpha(180)
        return faded

    def _generate_default_avatar(self, identifier: str) -> pygame.Surface:
        palette = {
            "feline": ((255, 160, 190), (255, 110, 170)),
            "julius": ((120, 210, 255), (80, 170, 240)),
        }
        primary, secondary = palette.get(identifier, ((220, 220, 220), (180, 180, 180)))

        surface = pygame.Surface((self.AVATAR_SIZE, self.AVATAR_SIZE), pygame.SRCALPHA)
        center = self.AVATAR_SIZE // 2
        pygame.draw.circle(surface, primary, (center, center), center - 6)
        pygame.draw.circle(surface, secondary, (center, center - 12), center // 2)
        pygame.draw.circle(surface, (255, 255, 255), (center - 12, center - 12), 8)
        pygame.draw.circle(surface, (255, 255, 255), (center + 12, center - 12), 8)
        pygame.draw.circle(surface, (0, 0, 0), (center - 12, center - 12), 4)
        pygame.draw.circle(surface, (0, 0, 0), (center + 12, center - 12), 4)
        pygame.draw.arc(surface, (0, 0, 0), (center - 18, center - 6, 36, 28), 3.4, 6.2, 4)
        return surface

    def activate_option(self, index: int) -> None:
        option = self.options[index]
        if option.action == "quit":
            self.app.running = False
        elif option.action == "test":
            from .test_setup import TestSetupScene

            self.app.change_scene(TestSetupScene)
        else:
            # Placeholder until the dedicated scenes are ready.
            self.feedback_message = f"'{option.label}' komt binnenkort!"
            self.feedback_timer = 2.5


__all__ = ["MainMenuScene"]
