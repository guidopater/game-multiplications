"""Summary screen for practice sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterable, List, Sequence, Tuple

import pygame

from .. import settings
from ..models import PracticeConfig  # for type hints
from ..ui import Button, draw_glossy_button
from .base import Scene


if TYPE_CHECKING:
    from .practice_session import PracticeQuestion


class PracticeSummaryScene(Scene):
    """Shows quick feedback after a practice run."""

    def __init__(
        self,
        app: "App",
        total_attempts: int,
        correct: int,
        streak: int,
        table_stats: Dict[int, Dict[str, float]],
        history: Sequence[Tuple["PracticeQuestion", str, bool, float]],
        config: PracticeConfig | None = None,
    ) -> None:
        super().__init__(app)
        self.total_attempts = total_attempts
        self.correct = correct
        self.streak = streak
        self.table_stats = table_stats
        self.history = history
        self.config = config

        self.title_font = settings.load_title_font(52)
        self.stat_font = settings.load_font(32)
        self.helper_font = settings.load_font(24)
        self.button_font = settings.load_font(30)

        self.buttons: List[Button] = []
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
        self.back_button_rect: pygame.Rect | None = None

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                    self._handle_back_action()
                    return
                for button in self.buttons:
                    if button.handle_event(event):
                        return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._restart_practice()
                    return
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._handle_back_action()
                    return

    def update(self, delta_time: float) -> None:
        return

    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._draw_back_button(surface)
        self._draw_title(surface)
        self._draw_stats(surface)
        self._draw_history(surface)
        self._draw_suggestion(surface)
        self._draw_recent_attempts(surface)
        self._draw_buttons(surface)

    def _draw_title(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        back_right = (self.back_button_rect.right + 40) if self.back_button_rect else (margin + 40)
        title = self.title_font.render("Goed geoefend!", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(back_right, margin - 30)))

    def _draw_stats(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        header_font = settings.load_title_font(32)
        accuracy = (self.correct / self.total_attempts) * 100 if self.total_attempts else 0.0
        lines = [
            self.stat_font.render(f"Beurten: {self.total_attempts}", True, settings.COLOR_TEXT_PRIMARY),
            self.stat_font.render(f"Goed: {self.correct}", True, settings.COLOR_SELECTION),
            self.stat_font.render(f"Nauwkeurigheid: {accuracy:.0f}%", True, settings.COLOR_TEXT_PRIMARY),
            self.helper_font.render(f"Langste streak: {self.streak}", True, settings.COLOR_TEXT_DIM),
        ]
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
        header = header_font.render("Lastige tafels", True, settings.COLOR_TEXT_PRIMARY)

        stats = sorted(
            self.table_stats.items(),
            key=lambda item: (item[1]["incorrect"], item[1]["total_time"] / item[1]["questions"] if item[1]["questions"] else 0),
            reverse=True,
        )
        lines: List[pygame.Surface] = []
        for table, data in stats[:4]:
            if data["questions"] == 0:
                continue
            incorrect = int(data["incorrect"])
            avg_time = data["total_time"] / data["questions"]
            color = settings.COLOR_ACCENT_LIGHT if incorrect else settings.COLOR_TEXT_DIM
            text = self.helper_font.render(
                f"Tafel {table}: {incorrect} fout, {avg_time:.1f}s gemiddeld",
                True,
                color,
            )
            lines.append(text)
        if not lines:
            lines = [self.helper_font.render("Alle tafels zien er goed uit!", True, settings.COLOR_SELECTION)]

        max_width = max(header.get_width(), max(line.get_width() for line in lines))
        area_width = max(420, max_width + 64)
        area_height = 40 + header.get_height() + len(lines) * 32
        area = pygame.Rect(surface.get_width() - margin - area_width, margin + 80, area_width, area_height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, area, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, area, width=3, border_radius=28)
        surface.blit(header, header.get_rect(topleft=(area.left + 24, area.top + 18)))

        y = area.top + 70
        for line in lines:
            surface.blit(line, line.get_rect(topleft=(area.left + 24, y)))
            y += 32

    def _draw_suggestion(self, surface: pygame.Surface) -> None:
        suggestion = self._generate_suggestion()
        if not suggestion:
            return

        margin = settings.SCREEN_MARGIN
        wrapped = self._wrap_text(suggestion, 520, self.helper_font)
        max_width = max(self.helper_font.size(line)[0] for line in wrapped) if wrapped else 0
        card_width = max(520, max_width + 64)
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

    def _draw_buttons(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        mouse_pos = pygame.mouse.get_pos()
        retry_rect = pygame.Rect(surface.get_width() - margin - 300, surface.get_height() - margin - 86, 300, 86)
        menu_rect = pygame.Rect(surface.get_width() - margin - 620, surface.get_height() - margin - 86, 300, 86)

        retry_button = Button(
            retry_rect,
            "Nog een keer!",
            self.button_font,
            self.button_palettes["Nog een keer!"],
            text_color=settings.COLOR_TEXT_PRIMARY,
            callback=self._restart_practice,
        )
        menu_button = Button(
            menu_rect,
            "Terug naar menu",
            self.button_font,
            self.button_palettes["Terug naar menu"],
            text_color=settings.COLOR_TEXT_PRIMARY,
            callback=self._handle_back_action,
        )

        self.buttons = [retry_button, menu_button]
        for button in self.buttons:
            button.render(surface, hover=button.rect.collidepoint(mouse_pos))

    def _restart_practice(self) -> None:
        if self.config is not None:
            from .practice_session import PracticeSessionScene

            self.app.change_scene(PracticeSessionScene, config=self.config)
        else:
            from .practice_setup import PracticeSetupScene

            self.app.change_scene(PracticeSetupScene)

    def _handle_back_action(self) -> None:
        from .main_menu import MainMenuScene

        self.app.change_scene(MainMenuScene)

    def _draw_recent_attempts(self, surface: pygame.Surface) -> None:
        if not self.history:
            return

        margin = settings.SCREEN_MARGIN
        recent = list(self.history[-5:])
        recent.reverse()
        rows: List[pygame.Surface] = []
        for question, answer, is_correct, duration in recent:
            label = question.as_text() if hasattr(question, "as_text") else str(question)
            prefix = "OK" if is_correct else "X"
            if is_correct:
                text = f"{prefix} {label} = {answer} ({duration:.1f}s)"
            else:
                correct_value = question.answer if hasattr(question, "answer") else "?"
                text = f"{prefix} {label} != {answer} -> {correct_value} ({duration:.1f}s)"
            color = settings.COLOR_SELECTION if is_correct else settings.COLOR_TEXT_PRIMARY
            rows.append(self.helper_font.render(text, True, color))

        width = max(row.get_width() for row in rows)
        header_font = settings.load_title_font(28)
        header = header_font.render("Laatste beurten", True, settings.COLOR_TEXT_PRIMARY)
        card_width = max(420, width + 56)
        card_height = header.get_height() + 36 + len(rows) * 32
        card = pygame.Rect(
            surface.get_width() - margin - card_width,
            surface.get_height() - margin - card_height - 110,
            card_width,
            card_height,
        )
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=24)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, card, width=2, border_radius=24)
        surface.blit(header, header.get_rect(topleft=(card.left + 24, card.top + 18)))

        y = card.top + header.get_height() + 30
        for row in rows:
            surface.blit(row, row.get_rect(topleft=(card.left + 24, y)))
            y += 30

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

    def _generate_suggestion(self) -> str:
        tricky = sorted(
            self.table_stats.items(),
            key=lambda item: (item[1]["incorrect"], item[1]["total_time"] / item[1]["questions"] if item[1]["questions"] else 0),
            reverse=True,
        )
        for table, stats in tricky:
            if stats["incorrect"]:
                return (
                    f"Focus nog even op tafel {table}. Er gingen {int(stats['incorrect'])} sommen mis en het kost gemiddeld"
                    f" {stats['total_time']/max(stats['questions'], 1):.1f}s. Een herhaling helpt!"
                )
        if tricky:
            table, stats = tricky[0]
            avg = stats['total_time'] / max(stats['questions'], 1)
            return f"Tafel {table} gaat goed! Probeer je tijd nog wat te verlagen (nu {avg:.1f}s)."
        return "Goed gedaan! Kies een mix van tafels om jezelf te blijven uitdagen."

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
