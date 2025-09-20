"""Summary screen for a completed test."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, TYPE_CHECKING

import pygame

from .. import settings
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
    ) -> None:
        super().__init__(app)
        self.result = result
        self.history = history
        self.time_up = time_up
        self.config = config
        self.speed_label = speed_label
        self.table_stats = {int(k): dict(v) for k, v in table_stats.items()}

        self.title_font = settings.load_title_font(52)
        self.stat_font = settings.load_font(32)
        self.helper_font = settings.load_font(24)
        self.button_font = settings.load_font(30)

        self.buttons: List[Tuple[str, pygame.Rect]] = []
        self.show_back_button = True

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            if self.handle_back_button_event(event):
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._restart_test()
                    return
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    from .main_menu import MainMenuScene

                    self.app.change_scene(MainMenuScene)
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
        self._draw_title(surface)
        self._draw_stats(surface)
        self._draw_history(surface)
        self._draw_suggestion(surface)
        self._draw_buttons(surface)
        self.render_back_button(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        heading = "Tijd is op!" if self.time_up else "Test afgerond!"
        title = self.title_font.render(heading, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(margin, margin - 30)))

        subtitle = self.helper_font.render(
            f"Goed gedaan {self.result.profile_name}! Snelheid: {self.speed_label}",
            True,
            settings.COLOR_TEXT_DIM,
        )
        surface.blit(subtitle, subtitle.get_rect(topleft=(margin + 4, margin + 24)))

    def _draw_stats(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        card = pygame.Rect(margin, margin + 80, 440, 240)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, card, width=3, border_radius=28)

        accuracy = self.result.accuracy * 100
        correct_line = self.stat_font.render(f"Goed: {self.result.correct}", True, settings.COLOR_SELECTION)
        wrong_line = self.stat_font.render(f"Fout: {self.result.incorrect}", True, settings.COLOR_ACCENT_LIGHT)
        accuracy_line = self.stat_font.render(f"Nauwkeurigheid: {accuracy:.0f}%", True, settings.COLOR_TEXT_PRIMARY)
        answered_line = self.helper_font.render(
            f"Beantwoord: {self.result.answered} van {self.result.question_count}",
            True,
            settings.COLOR_TEXT_DIM,
        )
        remaining = max(self.result.time_limit_seconds - self.result.elapsed_seconds, 0.0)
        minutes = int(remaining) // 60
        seconds = int(remaining) % 60
        time_line = self.helper_font.render(
            f"Resterende tijd: {minutes:02d}:{seconds:02d}",
            True,
            settings.COLOR_TEXT_DIM,
        )

        surface.blit(correct_line, correct_line.get_rect(topleft=(card.left + 32, card.top + 28)))
        surface.blit(wrong_line, wrong_line.get_rect(topleft=(card.left + 32, card.top + 74)))
        surface.blit(accuracy_line, accuracy_line.get_rect(topleft=(card.left + 32, card.top + 122)))
        surface.blit(answered_line, answered_line.get_rect(topleft=(card.left + 32, card.top + 170)))
        surface.blit(time_line, time_line.get_rect(topleft=(card.left + 32, card.top + 206)))

    def _draw_history(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header = self.stat_font.render("Foutjes om van te leren", True, settings.COLOR_ACCENT_LIGHT)
        area = pygame.Rect(surface.get_width() - margin - 420, margin + 80, 420, 280)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, area, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, area, width=3, border_radius=28)
        surface.blit(header, header.get_rect(topleft=(area.left + 24, area.top + 18)))

        mistakes = [entry for entry in self.history if entry[2] is False]
        y = area.top + 70
        if not mistakes:
            text = self.helper_font.render("Geen foutjes! Geweldig!", True, settings.COLOR_SELECTION)
            surface.blit(text, text.get_rect(topleft=(area.left + 24, y)))
        else:
            for question, answer, _ in mistakes[:5]:
                line = self.helper_font.render(
                    f"{question.left} x {question.right} = {question.answer} (jij zei {answer})",
                    True,
                    settings.COLOR_TEXT_PRIMARY,
                )
                surface.blit(line, line.get_rect(topleft=(area.left + 24, y)))
                y += 36

    def _draw_buttons(self, surface: pygame.Surface) -> None:
        self.buttons = []
        margin = settings.SCREEN_MARGIN
        retry_rect = pygame.Rect(surface.get_width() - margin - 220, surface.get_height() - margin - 72, 220, 72)
        menu_rect = pygame.Rect(surface.get_width() - margin - 470, surface.get_height() - margin - 72, 220, 72)

        for label, rect, colour in [
            ("Nog een keer!", retry_rect, settings.COLOR_ACCENT),
            ("Terug naar menu", menu_rect, settings.COLOR_SELECTION),
        ]:
            pygame.draw.rect(surface, colour, rect, border_radius=24)
            text = self.button_font.render(label, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text, text.get_rect(center=rect.center))
            self.buttons.append((label, rect))

    def _restart_test(self) -> None:
        from .test_session import TestSessionScene

        self.app.change_scene(TestSessionScene, config=self.config, speed_label=self.speed_label)

    def on_back(self) -> None:
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)

    def _draw_suggestion(self, surface: pygame.Surface) -> None:
        suggestion = self._generate_suggestion()
        if not suggestion:
            return

        margin = settings.SCREEN_MARGIN
        card = pygame.Rect(margin, surface.get_height() - margin - 180, 540, 140)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, card, width=3, border_radius=28)

        heading = self.stat_font.render("Tip voor de volgende keer", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(heading, heading.get_rect(topleft=(card.left + 28, card.top + 20)))

        wrapped = self._wrap_text(suggestion, card.width - 56, self.helper_font)
        y = card.top + 68
        for line in wrapped:
            text_surface = self.helper_font.render(line, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text_surface, text_surface.get_rect(topleft=(card.left + 28, y)))
            y += 30

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
