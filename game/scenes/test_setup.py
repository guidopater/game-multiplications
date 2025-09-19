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
        self.level_images = self._load_level_images()

        self.feedback_message = ""
        self.feedback_timer = 0.0
        self.show_back_button = True

        self.palette_table_active = {
            "top": (116, 227, 128),
            "bottom": (63, 186, 94),
            "border": (36, 140, 67),
            "shadow": (45, 122, 59),
        }
        self.palette_table_inactive = {
            "top": (242, 236, 228),
            "bottom": (209, 197, 184),
            "border": (168, 156, 145),
            "shadow": (150, 140, 130),
        }
        self.palette_question_active = {
            "top": (137, 214, 255),
            "bottom": (73, 158, 236),
            "border": (45, 118, 189),
            "shadow": (41, 99, 156),
        }
        self.palette_question_inactive = {
            "top": (242, 236, 228),
            "bottom": (209, 197, 184),
            "border": (168, 156, 145),
            "shadow": (150, 140, 130),
        }
        self.palette_start = {
            "top": (255, 215, 90),
            "bottom": (247, 176, 49),
            "border": (191, 128, 38),
            "shadow": (160, 109, 34),
        }

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
        left_x = margin + 90
        title = self.title_font.render("Testmodus", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(left_x, margin + 10)))
        subtitle = self.helper_font.render("Kies jouw uitdaging en druk op Start!", True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, subtitle.get_rect(topleft=(left_x + 6, margin + 68)))

    def _draw_tables(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header_x = margin + 30
        header_y = margin + 120
        header = self.section_font.render("Voor welke tafels wil je gaan?", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(header_x, header_y)))

        cols = 5
        button_size = (150, 70)
        spacing = 16
        start_x = header_x
        start_y = header_y + 60
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
            palette = self.palette_table_active if is_selected else self.palette_table_inactive
            face_rect, elevation = self._draw_capsule(surface, rect, palette, is_selected, rect.collidepoint(mouse_pos))
            label = self.option_font.render(f"Tafel {value}", True, settings.COLOR_TEXT_PRIMARY)
            label_rect = label.get_rect(center=face_rect.center)
            label_rect.y -= elevation
            surface.blit(label, label_rect)
            self.table_rects.append((face_rect, value))

        hint = self.helper_font.render("Tip: druk op 'A' voor alles, 'C' om te wissen", True, settings.COLOR_TEXT_DIM)
        rows = (len(self.TABLE_VALUES) + cols - 1) // cols
        hint_y = start_y + rows * (button_size[1] + spacing) + 12
        surface.blit(hint, hint.get_rect(topleft=(header_x, hint_y)))

    def _draw_speed(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header = self.section_font.render("Hoe snel ga je?", True, settings.COLOR_ACCENT_LIGHT)
        header_pos = header.get_rect(topleft=(margin + 30, margin + 330))
        surface.blit(header, header_pos)
        self.speed_rects = []

        base_x = margin + 30
        base_y = header_pos.bottom + 40
        spacing = 28
        card_width = 208
        card_height = 120
        mouse_pos = pygame.mouse.get_pos()

        for index, option in enumerate(self.SPEED_OPTIONS):
            rect = pygame.Rect(base_x + index * (card_width + spacing), base_y, card_width, card_height)
            is_selected = index == self.selected_speed_index
            palette = self.palette_table_active if is_selected else self.palette_table_inactive
            face_rect, _ = self._draw_capsule(surface, rect, palette, is_selected, rect.collidepoint(mouse_pos))

            image = self.level_images[index] if index < len(self.level_images) else None
            if image:
                scaled = pygame.transform.smoothscale(image, (face_rect.width - 20, face_rect.height - 20))
                surface.blit(scaled, scaled.get_rect(center=face_rect.center))
            else:
                label = self.option_font.render(f"{option.animal} {option.label}", True, settings.COLOR_TEXT_PRIMARY)
                surface.blit(label, label.get_rect(center=face_rect.center))

            self.speed_rects.append((face_rect, index))

    def _draw_questions(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        width = 260
        height = 72
        spacing = 22
        base_x = surface.get_width() - margin - width - 60
        base_y = margin + 160
        header = self.section_font.render("Hoeveel sommen wil je doen?", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(base_x, margin + 110)))
        self.question_rects = []
        mouse_pos = pygame.mouse.get_pos()

        for index, amount in enumerate(self.QUESTION_CHOICES):
            rect = pygame.Rect(base_x, base_y + index * (height + spacing), width, height)
            is_selected = index == self.selected_question_index
            palette = self.palette_question_active if is_selected else self.palette_question_inactive
            face_rect, elevation = self._draw_capsule(surface, rect, palette, is_selected, rect.collidepoint(mouse_pos))
            label = self.option_font.render(f"{amount} sommen", True, settings.COLOR_TEXT_PRIMARY)
            label_rect = label.get_rect(center=face_rect.center)
            label_rect.y -= elevation
            surface.blit(label, label_rect)
            self.question_rects.append((face_rect, index))

    def _draw_start_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        width = 260
        height = 86
        rect = pygame.Rect(surface.get_width() - margin - width, surface.get_height() - margin - height, width, height)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        face_rect, elevation = self._draw_capsule(surface, rect, self.palette_start, False, hover)
        text = self.button_font.render("Start!", True, settings.COLOR_TEXT_PRIMARY)
        text_rect = text.get_rect(center=face_rect.center)
        text_rect.y -= elevation
        surface.blit(text, text_rect)
        self.start_rect = face_rect

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

    def on_back(self) -> None:
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)

    def _draw_capsule(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        palette: dict[str, tuple[int, int, int]],
        selected: bool,
        hover: bool,
    ) -> tuple[pygame.Rect, int]:
        radius = 28
        depth_rest = 12
        depth_hover = 6
        depth_pressed = 0

        if selected:
            elevation = depth_pressed
        elif hover:
            elevation = depth_hover
        else:
            elevation = depth_rest

        shadow_rect = rect.move(0, elevation)
        pygame.draw.rect(surface, palette["shadow"], shadow_rect, border_radius=radius)

        face_height = rect.height - (depth_rest - elevation)
        face_rect = pygame.Rect(rect.left, rect.top - (depth_rest - elevation), rect.width, face_height)

        button_surface = pygame.Surface((face_rect.width, face_rect.height), pygame.SRCALPHA)
        for y in range(face_rect.height):
            ratio = y / max(face_rect.height - 1, 1)
            color = tuple(
                int(palette["top"][i] + (palette["bottom"][i] - palette["top"][i]) * ratio)
                for i in range(3)
            )
            pygame.draw.line(button_surface, color, (0, y), (face_rect.width, y))

        mask = pygame.Surface((face_rect.width, face_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        button_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        surface.blit(button_surface, face_rect.topleft)
        pygame.draw.rect(surface, palette["border"], face_rect, width=4, border_radius=radius)

        return face_rect, (depth_rest - elevation)

    def _load_level_images(self) -> List[pygame.Surface]:
        images: List[pygame.Surface] = []
        for index in range(1, 5):
            path = self.app.assets_dir / "images" / f"level_{index}.png"
            if not path.exists():
                continue
            try:
                image = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue
            images.append(image)
        return images
