"""Summary screen for a completed test."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, TYPE_CHECKING

import pygame

from .. import settings
from ..ui import draw_glossy_button
from ..models import TestConfig, TestResult
from .base import Scene

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from .test_session import Question


class TestSummaryScene(Scene):
    """Shows results and allows the player to continue."""

    def __init__(
        self,
        app: "App",
        result: TestResult,
        history: Sequence[Tuple[object, str, bool]],
        time_up: bool,
        config: TestConfig,
        speed_label: str,
        table_stats: dict[int, dict[str, float]],
        coin_delta: int,
    ) -> None:
        super().__init__(app)
        self.result = result
        self.history = history
        self.time_up = time_up
        self.config = config
        self.speed_label = speed_label
        self.table_stats = {int(k): dict(v) for k, v in table_stats.items()}
        self.coin_delta = coin_delta
        self.total_coins = getattr(self.app.active_profile, "coins", 0)

        self.title_font = settings.load_title_font(52)
        self.stat_font = settings.load_font(32)
        self.helper_font = settings.load_font(24)
        self.button_font = settings.load_font(30)

        self.buttons: List[Tuple[str, pygame.Rect]] = []
        self.show_back_button = False
        self.back_button_rect: pygame.Rect | None = None
        self.back_palette = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }
        self.button_palettes = {
            "Nog een keer!": {
                "top": (255, 170, 59),
                "bottom": (244, 110, 34),
                "border": (172, 78, 23),
                "shadow": (138, 62, 19),
            },
            "Terug naar menu": {
                "top": (73, 195, 86),
                "bottom": (40, 158, 66),
                "border": (31, 124, 50),
                "shadow": (24, 112, 46),
            },
        }

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                    self._handle_back_action()
                    return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._restart_test()
                    return
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._handle_back_action()
                    return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for label, rect in self.buttons:
                    if rect.collidepoint(event.pos):
                        if label == "Terug naar menu":
                            from .main_menu import MainMenuScene

                            self.app.change_scene(MainMenuScene)
                        else:
                            self._restart_test()
                        return

    def update(self, delta_time: float) -> None:
        # No dynamic state to update.
        return

    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._draw_back_button(surface)
        self._draw_title(surface)
        self._draw_stats(surface)
        self._draw_history(surface)
        self._draw_suggestion(surface)
        self._draw_buttons(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        back_right = (self.back_button_rect.right + 40) if self.back_button_rect else (margin + 40)
        heading = "Tijd is op!" if self.time_up else "Test afgerond!"
        title = self.title_font.render(heading, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(back_right, margin - 30)))

        subtitle = self.helper_font.render(
            f"Goed gedaan {self.result.profile_name}! Snelheid: {self.speed_label}",
            True,
            settings.COLOR_TEXT_DIM,
        )
        surface.blit(subtitle, subtitle.get_rect(topleft=(back_right + 4, margin + 24)))

    def _draw_stats(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header_font = settings.load_title_font(32)
        lines = [
            self.stat_font.render(f"Goed: {self.result.correct}", True, settings.COLOR_SELECTION),
            self.stat_font.render(f"Fout: {self.result.incorrect}", True, settings.COLOR_ACCENT_LIGHT),
            self.stat_font.render(f"Nauwkeurigheid: {self.result.accuracy * 100:.0f}%", True, settings.COLOR_TEXT_PRIMARY),
            self.helper_font.render(
                f"Beantwoord: {self.result.answered} van {self.result.question_count}",
                True,
                settings.COLOR_TEXT_DIM,
            ),
            self.helper_font.render(
                f"Resterende tijd: {int(max(self.result.time_limit_seconds - self.result.elapsed_seconds, 0.0))//60:02d}:{int(max(self.result.time_limit_seconds - self.result.elapsed_seconds, 0.0))%60:02d}",
                True,
                settings.COLOR_TEXT_DIM,
            ),
        ]
        coins_label = f"Munten: {'+' if self.coin_delta >= 0 else ''}{self.coin_delta}"
        coins_line = self.stat_font.render(coins_label, True, settings.COLOR_ACCENT)
        total_line = self.helper_font.render(f"Totaal nu: {self.total_coins}", True, settings.COLOR_TEXT_PRIMARY)
        lines.extend([coins_line, total_line])
        max_width = max(line.get_width() for line in lines)
        card_width = max(420, max_width + 64)
        card_height = 40 + sum(line.get_height() + 16 for line in lines)
        card = pygame.Rect(margin, margin + 80, card_width, card_height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, card, width=3, border_radius=28)

        y = card.top + 24
        for line in lines:
            surface.blit(line, line.get_rect(topleft=(card.left + 32, y)))
            y += line.get_height() + 12

    def _draw_history(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header_font = settings.load_title_font(32)
        header = header_font.render("Foutjes om van te leren", True, settings.COLOR_TEXT_PRIMARY)
        mistakes = [entry for entry in self.history if entry[2] is False]
        content_lines: List[pygame.Surface]
        if not mistakes:
            content_lines = [self.helper_font.render("Geen foutjes! Geweldig!", True, settings.COLOR_SELECTION)]
        else:
            content_lines = [
                self.helper_font.render(
                    f"{question.left} x {question.right} = {question.answer} (jij zei {answer})",
                    True,
                    settings.COLOR_TEXT_PRIMARY,
                )
                for question, answer, _ in mistakes[:5]
            ]

        max_width = max([header.get_width()] + [line.get_width() for line in content_lines])
        area_width = max(380, max_width + 64)
        area_height = 40 + header.get_height() + len(content_lines) * 32
        area = pygame.Rect(surface.get_width() - margin - area_width, margin + 80, area_width, area_height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, area, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, area, width=3, border_radius=28)
        surface.blit(header, header.get_rect(topleft=(area.left + 24, area.top + 18)))

        y = area.top + 70
        for line in content_lines:
            surface.blit(line, line.get_rect(topleft=(area.left + 24, y)))
            y += 32

    def _draw_buttons(self, surface: pygame.Surface) -> None:
        self.buttons = []
        margin = settings.SCREEN_MARGIN
        retry_rect = pygame.Rect(surface.get_width() - margin - 300, surface.get_height() - margin - 86, 300, 86)
        menu_rect = pygame.Rect(surface.get_width() - margin - 620, surface.get_height() - margin - 86, 300, 86)
        mouse_pos = pygame.mouse.get_pos()
        mouse_pos = pygame.mouse.get_pos()

        info = [
            ("Nog een keer!", retry_rect, self.button_palettes["Nog een keer!"]),
            ("Terug naar menu", menu_rect, self.button_palettes["Terug naar menu"]),
        ]

        for label, rect, palette in info:
            face_rect = draw_glossy_button(
                surface,
                rect,
            palette,
            selected=False,
            hover=rect.collidepoint(mouse_pos),
            corner_radius=32,
        )
            text = self.button_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(center=face_rect.center))
            self.buttons.append((label, rect))

    def _restart_test(self) -> None:
        from .test_session import TestSessionScene

        self.app.change_scene(TestSessionScene, config=self.config, speed_label=self.speed_label)

    def _draw_suggestion(self, surface: pygame.Surface) -> None:
        suggestion = self._generate_suggestion()
        if not suggestion:
            return

        margin = settings.SCREEN_MARGIN
        margin = settings.SCREEN_MARGIN
        max_text_width = 0
        wrapped = self._wrap_text(suggestion, 520, self.helper_font)
        if wrapped:
            max_text_width = max(self.helper_font.size(line)[0] for line in wrapped)
        card_width = max(520, max_text_width + 64)
        card_height = 40 + 32 + len(wrapped) * 32
        card = pygame.Rect(margin, surface.get_height() - margin - card_height, card_width, card_height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, card, width=3, border_radius=28)

        heading_font = settings.load_title_font(32)
        heading = heading_font.render("Tip voor de volgende keer", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(topleft=(card.left + 28, card.top + 20)))

        y = card.top + 68
        for line in wrapped:
            text_surface = self.helper_font.render(line, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text_surface, text_surface.get_rect(topleft=(card.left + 28, y)))
            y += 32

    def _generate_suggestion(self) -> str:
        tricky = self.result.tricky_tables()
        slow = self.result.slowest_tables()

        if all(value.get("questions", 0) == value.get("correct", 0) for value in self.table_stats.values()):
            return "Fantastisch! Alle tafels gingen vlekkeloos. Kies gerust een nieuw avontuur."

        if tricky:
            table = tricky[0]
            stats = self.table_stats.get(table, {})
            incorrect = int(stats.get("incorrect", 0))
            average = stats.get("total_time", 0.0) / max(stats.get("questions", 1), 1)
            return (
                f"Neem de tafel van {table} nog even door. Er gingen {incorrect} sommen mis en het kost gemiddeld"
                f" {average:.1f}s. Een oefenrondje maakt je supersnel!"
            )

        if slow:
            table = slow[0]
            stats = self.table_stats.get(table, {})
            average = stats.get("total_time", 0.0) / max(stats.get("questions", 1), 1)
            return (
                f"Je bent heel precies! Misschien kun je de tafel van {table} nog eens oefenen om nog sneller te worden."
                f" Nu kost een som gemiddeld {average:.1f}s."
            )

        return "Blijf oefenen en daag jezelf uit met een mix van tafels voor nog meer snelheid."

    @staticmethod
    def _wrap_text(text: str, max_width: int, font: pygame.font.Font) -> List[str]:
        words = text.split()
        lines: List[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _handle_back_action(self) -> None:
        if hasattr(self.app, "sounds") and "back" in self.app.sounds:
            self.app.sounds["back"].play()
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)

    def on_back(self) -> None:
        self._handle_back_action()

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
            self.back_palette,
            selected=False,
            hover=rect.collidepoint(pygame.mouse.get_pos()),
            corner_radius=28,
        )
        surface.blit(text, text.get_rect(center=face_rect.center))
        self.back_button_rect = rect
