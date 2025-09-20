"""Configuration scene for the timed test mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import pygame

from .. import settings
from ..ui import draw_glossy_button

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - numpy is expected but degrade gracefully
    np = None
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
        self.show_back_button = False
        self.back_button_rect: pygame.Rect | None = None

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
        self.palette_back = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }
        self.tables_bottom = settings.SCREEN_MARGIN
        self.tables_right = settings.SCREEN_MARGIN
        self.question_column_x = 0
        self.speed_palettes: dict[int, dict[str, tuple[int, int, int]]] = {}

    # Event handling -------------------------------------------------
    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                    self._handle_back_action()
                    return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._handle_back_action()
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
                        if self.selected_speed_index != index:
                            self.selected_speed_index = index
                        break
                for rect, index in self.question_rects:
                    if rect.collidepoint(event.pos):
                        if self.selected_question_index != index:
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
        self._draw_back_button(surface)
        self._draw_title(surface)
        self._draw_tables(surface)
        self._draw_speed(surface)
        self._draw_questions(surface)
        self._draw_start_button(surface)
        self._draw_feedback(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        back_right = (self.back_button_rect.right + 40) if self.back_button_rect else (margin + 90)
        left_x = back_right
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
        self.table_header_top = header_y

        cols = 5
        button_size = (150, 64)
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

        if self.TABLE_VALUES:
            visible_cols = min(cols, len(self.TABLE_VALUES))
            self.tables_right = start_x + visible_cols * (button_size[0] + spacing) - spacing
        else:
            self.tables_right = start_x

        rows = (len(self.TABLE_VALUES) + cols - 1) // cols
        hint = self.helper_font.render("Tip: druk op 'A' voor alles, 'C' om te wissen", True, settings.COLOR_TEXT_DIM)
        hint_y = start_y + rows * (button_size[1] + spacing) + 12
        surface.blit(hint, hint.get_rect(topleft=(header_x, hint_y)))
        self.tables_bottom = hint_y + hint.get_height()

    def _draw_speed(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header_y = self.tables_bottom + 40
        header = self.section_font.render("Hoe snel ga je?", True, settings.COLOR_ACCENT_LIGHT)
        header_pos = header.get_rect(topleft=(margin + 30, header_y))
        surface.blit(header, header_pos)
        self.speed_rects = []

        base_x = margin + 30
        base_y = header_pos.bottom + 32
        spacing = 24
        card_width = 148
        card_height = 148
        mouse_pos = pygame.mouse.get_pos()

        for index, option in enumerate(self.SPEED_OPTIONS):
            rect = pygame.Rect(base_x + index * (card_width + spacing), base_y, card_width, card_height)
            is_selected = index == self.selected_speed_index
            base_palette = self.speed_palettes.get(index)
            if base_palette is None:
                base_palette = self.palette_table_active if is_selected else self.palette_table_inactive
            palette = base_palette if is_selected else self._desaturate_palette(base_palette)

            face_rect = draw_glossy_button(
                surface,
                rect,
                palette,
                selected=is_selected,
                hover=rect.collidepoint(mouse_pos),
                corner_radius=32,
            )

            image = self.level_images[index] if index < len(self.level_images) else None
            if image:
                inset = 28
                scaled = pygame.transform.smoothscale(image, (face_rect.width - inset, face_rect.height - inset))
                if not is_selected:
                    scaled = self._greyscale_surface(scaled)
                    scaled.set_alpha(150)
                surface.blit(scaled, scaled.get_rect(center=face_rect.center))
            else:
                label = self.option_font.render(f"{option.animal} {option.label}", True, settings.COLOR_TEXT_PRIMARY)
                surface.blit(label, label.get_rect(center=face_rect.center))

            self.speed_rects.append((rect, index))

    def _draw_questions(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        width = 260
        height = 72
        spacing = 22
        base_x = self.tables_right + 80
        header_top = getattr(self, "table_header_top", self.tables_bottom)
        header = self.section_font.render("Hoeveel sommen", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(header, header.get_rect(topleft=(base_x, header_top)))
        base_y = header_top + 60
        self.question_rects = []
        mouse_pos = pygame.mouse.get_pos()
        self.question_column_x = base_x

        for index, amount in enumerate(self.QUESTION_CHOICES):
            rect = pygame.Rect(base_x, base_y + index * (height + spacing), width, height)
            is_selected = index == self.selected_question_index
            palette = self.palette_question_active if is_selected else self.palette_question_inactive
            face_rect = draw_glossy_button(surface, rect, palette, selected=is_selected, hover=rect.collidepoint(mouse_pos))
            label = self.option_font.render(f"{amount} sommen", True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(label, label.get_rect(center=face_rect.center))
            self.question_rects.append((rect, index))

    def _draw_start_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        width = 260
        height = 86
        base_x = getattr(self, "question_column_x", surface.get_width() - margin - width)
        rect = pygame.Rect(base_x, surface.get_height() - margin - height, width, height)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        face_rect = draw_glossy_button(
            surface,
            rect,
            self.palette_start,
            selected=False,
            hover=hover,
            corner_radius=32,
        )
        estimate = self._estimate_max_reward()
        estimate_text = self.helper_font.render(f"Te verdienen: {estimate} munten", True, settings.COLOR_TEXT_DIM)
        surface.blit(estimate_text, estimate_text.get_rect(center=(face_rect.centerx, face_rect.top - 24)))
        text = self.button_font.render("Start!", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(text, text.get_rect(center=face_rect.center))
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

    def on_back(self) -> None:
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)

    def _handle_back_action(self) -> None:
        if hasattr(self.app, "sounds") and "back" in self.app.sounds:
            self.app.sounds["back"].play()
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)


    def _draw_back_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        text = self.helper_font.render("Terug", True, settings.COLOR_TEXT_PRIMARY)
        padding_x = 32
        padding_y = 18
        width = text.get_width() + padding_x * 2
        height = text.get_height() + padding_y * 2
        rect = pygame.Rect(margin, margin + 6, width, height)
        face_rect = draw_glossy_button(
            surface,
            rect,
            self.palette_back,
            selected=False,
            hover=rect.collidepoint(pygame.mouse.get_pos()),
            corner_radius=28,
        )
        surface.blit(text, text.get_rect(center=face_rect.center))
        self.back_button_rect = rect

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
            if np is not None:
                self.speed_palettes[index - 1] = self._palette_from_image(image)
        return images

    def _palette_from_image(self, surface: pygame.Surface) -> dict[str, tuple[int, int, int]]:
        arr = np.array(pygame.transform.smoothscale(surface, (50, 50)))
        rgb = arr[:, :, :3].reshape(-1, 3).mean(axis=0)
        base = tuple(int(c) for c in rgb)
        return {
            "top": self._lighten_color(base, 0.18),
            "bottom": self._darken_color(base, 0.18),
            "border": self._darken_color(base, 0.35),
            "shadow": self._darken_color(base, 0.55),
        }

    @staticmethod
    def _lighten_color(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        return tuple(min(255, int(c + (255 - c) * amount)) for c in color)

    @staticmethod
    def _darken_color(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        return tuple(max(0, int(c * (1 - amount))) for c in color)

    @staticmethod
    def _desaturate_palette(palette: dict[str, tuple[int, int, int]]) -> dict[str, tuple[int, int, int]]:
        def to_grey(col: tuple[int, int, int]) -> tuple[int, int, int]:
            avg = int(col[0] * 0.299 + col[1] * 0.587 + col[2] * 0.114)
            return (avg, avg, avg)

        base = to_grey(palette["top"])
        return {
            "top": TestSetupScene._lighten_color(base, 0.1),
            "bottom": TestSetupScene._darken_color(base, 0.1),
            "border": TestSetupScene._darken_color(base, 0.25),
            "shadow": TestSetupScene._darken_color(base, 0.45),
        }

    @staticmethod
    def _greyscale_surface(surface: pygame.Surface) -> pygame.Surface:
        if np is None:
            grey = surface.copy()
            grey.fill((120, 120, 120, 0), special_flags=pygame.BLEND_RGB_MULT)
            return grey

        grey = surface.copy()
        arr = pygame.surfarray.pixels3d(grey)
        luminance = (arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114).astype("uint8")
        arr[:, :, 0] = luminance
        arr[:, :, 1] = luminance
        arr[:, :, 2] = luminance
        del arr
        return grey

    def _estimate_max_reward(self) -> int:
        if not self.selected_tables:
            return 0
        avg_table = sum(self.selected_tables) / len(self.selected_tables)
        per_question = 6 + avg_table
        questions = self.QUESTION_CHOICES[self.selected_question_index]
        speed = self.SPEED_OPTIONS[self.selected_speed_index]
        time_bonus = speed.minutes * 2
        return int(per_question * questions + time_bonus)
        return images
