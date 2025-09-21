"""Progress and leaderboard overview for completed tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

import pygame

from .. import settings
from ..models import TestResult
from ..ui import draw_glossy_button
from .base import Scene


@dataclass(frozen=True)
class ProfileSummary:
    profile_id: str
    display_name: str
    tests: int
    average_accuracy: float
    best_accuracy: float
    last_played: datetime | None


class ProgressOverviewScene(Scene):
    """Shows recent results for the active player and a friendly leaderboard."""

    def __init__(self, app: "App") -> None:
        super().__init__(app)

        self.title_font = settings.load_title_font(54)
        self.section_font = settings.load_title_font(32)
        self.body_font = settings.load_font(24)
        self.small_font = settings.load_font(20)
        self.button_font = settings.load_font(28)
        self.stat_font = settings.load_font(30)

        self.buttons: List[tuple[str, pygame.Rect]] = []
        self.leaderboard_rows: List[ProfileSummary] = []
        self.recent_results: List[TestResult] = []
        self.latest_result: TestResult | None = None
        self.tricky_tables: List[tuple[int, float, float]] = []
        self.top_back_rect: pygame.Rect | None = None

        self._load_data()

        self.button_palettes = {
            "start_test": {
                "top": (255, 170, 59),
                "bottom": (244, 110, 34),
                "border": (172, 78, 23),
                "shadow": (138, 62, 19),
            },
            "go_practice": {
                "top": (84, 188, 255),
                "bottom": (31, 117, 232),
                "border": (27, 86, 182),
                "shadow": (21, 73, 152),
            },
            "back": {
                "top": (216, 196, 255),
                "bottom": (176, 148, 227),
                "border": (126, 98, 192),
                "shadow": (102, 78, 152),
            },
        }
        self.action_labels = {
            "start_test": self.tr(
                "progress_overview.actions.start_test",
                default="Start nieuwe test",
            ),
            "go_practice": self.tr(
                "progress_overview.actions.go_practice",
                default="Ga oefenen",
            ),
            "back": self.tr("progress_overview.actions.back", default=self.tr("common.back", default="Terug")),
        }

    def _load_data(self) -> None:
        active_id = self.app.active_profile.identifier
        raw_results = self.app.scores.get_test_results(active_id)
        self.recent_results = self._parse_results(raw_results)
        self.latest_result = self.recent_results[-1] if self.recent_results else None
        self.tricky_tables = self._aggregate_tricky_tables(self.recent_results)
        self.leaderboard_rows = self._build_leaderboard()

    def _parse_results(self, payloads: Sequence[dict]) -> List[TestResult]:
        results: List[TestResult] = []
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            try:
                results.append(TestResult.from_serialisable(payload))
            except Exception:  # pragma: no cover - guard against bad payloads
                continue
        results.sort(key=lambda result: result.timestamp)
        return results

    def _aggregate_tricky_tables(self, results: Sequence[TestResult]) -> List[tuple[int, float, float]]:
        combined: Dict[int, Dict[str, float]] = {}
        for result in results:
            for table, stats in result.table_stats.items():
                target = combined.setdefault(table, {"incorrect": 0.0, "questions": 0.0, "total_time": 0.0})
                target["incorrect"] += float(stats.get("incorrect", 0.0))
                target["questions"] += float(stats.get("questions", 0.0))
                target["total_time"] += float(stats.get("total_time", 0.0))

        summary: List[tuple[int, float, float]] = []
        for table, stats in combined.items():
            incorrect = stats["incorrect"]
            questions = stats["questions"]
            avg_time = stats["total_time"] / questions if questions else 0.0
            summary.append((table, incorrect, avg_time))

        summary.sort(key=lambda item: (item[1], item[2]), reverse=True)
        return summary[:4]

    def _build_leaderboard(self) -> List[ProfileSummary]:
        summaries: List[ProfileSummary] = []
        for profile in self.app.profiles:
            results = self._parse_results(self.app.scores.get_test_results(profile.identifier))
            if not results:
                continue
            tests = len(results)
            total_accuracy = sum(result.accuracy for result in results)
            best_accuracy = max(result.accuracy for result in results)
            average_accuracy = total_accuracy / tests if tests else 0.0
            last_played = max(result.timestamp for result in results)
            summaries.append(
                ProfileSummary(
                    profile_id=profile.identifier,
                    display_name=profile.display_name,
                    tests=tests,
                    average_accuracy=average_accuracy,
                    best_accuracy=best_accuracy,
                    last_played=last_played,
                )
            )

        summaries.sort(key=lambda item: (item.average_accuracy, item.tests), reverse=True)
        return summaries

    # Event handling -------------------------------------------------
    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for action, rect in self.buttons:
                    if rect.collidepoint(event.pos):
                        self._handle_button(action)
                        return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    from .main_menu import MainMenuScene

                    self.app.change_scene(MainMenuScene)
                    return
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._handle_button("start_test")
                    return

    def _handle_button(self, action: str) -> None:
        if action == "start_test":
            from .test_setup import TestSetupScene

            self.app.change_scene(TestSetupScene)
        elif action == "go_practice":
            from .practice_setup import PracticeSetupScene

            self.app.change_scene(PracticeSetupScene)
        else:
            from .main_menu import MainMenuScene

            self.app.change_scene(MainMenuScene)

    # Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        self._refresh_action_labels()
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self.buttons = []
        self._draw_header(surface)
        if not self.recent_results:
            self._draw_empty_state(surface)
        else:
            self._draw_top_row(surface)
            self._draw_trend_card(surface)
        self._draw_history(surface)
        self._draw_buttons(surface)

    def _refresh_action_labels(self) -> None:
        self.action_labels["start_test"] = self.tr(
            "progress_overview.actions.start_test",
            default="Start nieuwe test",
        )
        self.action_labels["go_practice"] = self.tr(
            "progress_overview.actions.go_practice",
            default="Ga oefenen",
        )
        self.action_labels["back"] = self.tr(
            "progress_overview.actions.back",
            default=self.tr("common.back", default="Terug"),
        )

    def _draw_header(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        back_rect = pygame.Rect(margin, margin - 6, 160, 48)
        palette = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }
        draw_glossy_button(
            surface,
            back_rect,
            palette,
            selected=False,
            hover=back_rect.collidepoint(pygame.mouse.get_pos()),
            corner_radius=24,
        )
        back_label = self.action_labels["back"]
        back_text = self.button_font.render(back_label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(back_text, back_text.get_rect(center=back_rect.center))
        self.top_back_rect = back_rect

        offset = back_rect.right + 24
        profile = self.app.active_profile
        title_text = self.tr(
            "progress_overview.title",
            default="Hoe deed je het, {name}?",
            name=profile.display_name,
        )
        title = self.title_font.render(title_text, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title, title.get_rect(topleft=(offset, margin - 20)))

        subtitle_text = self.tr(
            "progress_overview.subtitle",
            default="Bekijk je voortgang en vergelijk met de rest van het team!",
        )
        subtitle = self.body_font.render(subtitle_text, True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, subtitle.get_rect(topleft=(offset + 6, margin + 34)))

    def _draw_empty_state(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        card = pygame.Rect(
            margin,
            margin + 120,
            surface.get_width() - margin * 2,
            220,
        )
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=32)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, card, width=3, border_radius=32)

        heading_text = self.tr(
            "progress_overview.empty.heading",
            default="Nog geen tests",
        )
        heading = self.section_font.render(heading_text, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(heading, heading.get_rect(center=(card.centerx, card.top + 70)))

        message_lines = self.tr_list(
            "progress_overview.empty.lines",
            default=[
                "Je hebt nog geen test gedaan.",
                "Start een nieuwe test om je vooruitgang bij te houden!",
            ],
        )
        y = card.top + 120
        for line in message_lines:
            text_surface = self.body_font.render(line, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text_surface, text_surface.get_rect(center=(card.centerx, y)))
            y += 34

    def _draw_top_row(self, surface: pygame.Surface) -> None:
        assert self.latest_result is not None
        margin = settings.SCREEN_MARGIN
        top_offset = margin + 110
        row_height = 220
        half_width = (surface.get_width() - margin * 3) // 2

        left_card = pygame.Rect(margin, top_offset, half_width, row_height)
        right_card = pygame.Rect(margin * 2 + half_width, top_offset, half_width, row_height)

        self._draw_recent_highlight(surface, left_card)
        self._draw_leaderboard(surface, right_card)

    def _draw_recent_highlight(self, surface: pygame.Surface, card: pygame.Rect) -> None:
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=32)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, card, width=3, border_radius=32)

        heading = self.section_font.render(
            self.tr("progress_overview.latest.heading", default="Laatste test"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(card.left + 32, card.top + 28)))

        assert self.latest_result is not None
        latest = self.latest_result
        timestamp = latest.timestamp.strftime("%d %b %Y, %H:%M")
        tables = ", ".join(str(n) for n in latest.tables) or "-"
        accuracy = f"{latest.accuracy * 100:.0f}%"
        duration = self._format_duration(latest.elapsed_seconds)
        remaining = self._format_duration(latest.remaining_seconds)

        stats = {
            "tables": tables,
            "accuracy": accuracy,
            "answered": f"{latest.answered}/{latest.question_count}",
            "time_used": duration,
            "remaining": remaining,
        }

        info_x = card.left + 32
        info_y = card.top + 90
        timestamp_surface = self.body_font.render(
            self.tr(
                "progress_overview.latest.completed_on",
                default="Afgerond op {timestamp}",
                timestamp=timestamp,
            ),
            True,
            settings.COLOR_TEXT_DIM,
        )
        surface.blit(timestamp_surface, (info_x, info_y))
        info_y += 36

        for key, value in stats.items():
            label_text = self.tr(
                f"progress_overview.latest.labels.{key}",
                default={
                    "tables": "Tafels",
                    "accuracy": "Nauwkeurigheid",
                    "answered": "Beantwoord",
                    "time_used": "Gebruikte tijd",
                    "remaining": "Over",
                }[key],
            )
            label_surface = self.small_font.render(label_text, True, settings.COLOR_TEXT_DIM)
            value_surface = self.stat_font.render(value, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(label_surface, (info_x, info_y))
            surface.blit(value_surface, (info_x + 180, info_y - 6))
            info_y += 48

    def _draw_trend_card(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        top_offset = margin + 110 + 220 + margin // 2
        card = pygame.Rect(
            margin,
            top_offset,
            surface.get_width() - margin * 2,
            170,
        )
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, card, width=3, border_radius=28)

        heading = self.section_font.render(
            self.tr("progress_overview.trends.heading", default="Trends"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(card.left + 28, card.top + 24)))

        streak = self._longest_streak(self.recent_results)
        average_accuracy = self._average_accuracy(self.recent_results)
        change = self._accuracy_change(self.recent_results)
        average_time = self._average_time(self.recent_results)

        messages = [
            self.tr(
                "progress_overview.trends.average_accuracy",
                default="Gemiddelde nauwkeurigheid: {value}",
                value=f"{average_accuracy * 100:.0f}%",
            ),
            self.tr(
                "progress_overview.trends.change",
                default="Verandering t.o.v. vorige: {delta}",
                delta=f"{change:+.0f} punten",
            ),
            self.tr(
                "progress_overview.trends.longest_streak",
                default="Langste streak: {value}",
                value=streak,
            ),
            self.tr(
                "progress_overview.trends.average_time",
                default="Gem. reactietijd: {value}",
                value=f"{average_time:.1f}s",
            ),
        ]

        y = card.top + 80
        for message in messages:
            text_surface = self.body_font.render(message, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text_surface, (card.left + 32, y))
            y += 32

        if self.tricky_tables:
            hint = self.small_font.render(
                self.tr("progress_overview.trends.focus_label", default="Focus tafels:"),
                True,
                settings.COLOR_TEXT_DIM,
            )
            surface.blit(hint, (card.right - 210, card.top + 24))
            ty = card.top + 56
            for table, incorrect, avg_time in self.tricky_tables:
                text_value = self.tr(
                    "progress_overview.trends.focus_item",
                    default="Tafel {table}: {incorrect} fout, {average}s",
                    table=table,
                    incorrect=int(incorrect),
                    average=f"{avg_time:.1f}",
                )
                text = self.small_font.render(text_value, True, settings.COLOR_TEXT_PRIMARY)
                surface.blit(text, (card.right - 210, ty))
                ty += 26

    def _draw_history(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        top_offset = margin + 110 + 220 + margin // 2 + 170 + margin // 2
        available_height = surface.get_height() - top_offset - margin - 120
        card = pygame.Rect(
            margin,
            top_offset,
            surface.get_width() - margin * 2,
            max(160, available_height),
        )
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=28)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, card, width=3, border_radius=28)

        heading = self.section_font.render(
            self.tr("progress_overview.history.heading", default="Laatste resultaten"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(card.left + 28, card.top + 24)))

        recent = list(self.recent_results[-5:])
        recent.reverse()
        y = card.top + 80
        for result in recent:
            date_text = result.timestamp.strftime("%d %b")
            accuracy = f"{result.accuracy * 100:.0f}%"
            tables = ", ".join(str(n) for n in result.tables) or "-"
            line_text = self.tr(
                "progress_overview.history.item",
                default="{date} • {accuracy} • Tafels {tables}",
                date=date_text,
                accuracy=accuracy,
                tables=tables,
            )
            line = self.body_font.render(line_text, True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(line, (card.left + 28, y))
            y += 32

    def _draw_leaderboard(self, surface: pygame.Surface, card: pygame.Rect | None = None) -> None:
        if card is None:
            margin = settings.SCREEN_MARGIN
            top_offset = margin + 110
            width = surface.get_width() - margin * 2
            height = surface.get_height() - margin * 2 - 140
            card = pygame.Rect(margin, top_offset, width, height)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, card, border_radius=32)
        pygame.draw.rect(surface, settings.COLOR_ACCENT_LIGHT, card, width=3, border_radius=32)

        heading = self.section_font.render(
            self.tr("progress_overview.leaderboard.heading", default="Leaderboard"),
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(heading, heading.get_rect(topleft=(card.left + 28, card.top + 26)))

        if not self.leaderboard_rows:
            message = self.body_font.render(
                self.tr(
                    "progress_overview.leaderboard.empty",
                    default="Nog niemand heeft een test gedaan.",
                ),
                True,
                settings.COLOR_TEXT_PRIMARY,
            )
            surface.blit(message, (card.left + 28, card.top + 90))
            return

        header_defs = [
            ("name", card.left + 28),
            ("tests", card.left + 200),
            ("average", card.left + 280),
            ("best", card.left + 380),
            ("last", card.left + 500),
        ]
        col_x = [pos for _, pos in header_defs]
        for key, x in header_defs:
            text = self.tr(
                f"progress_overview.leaderboard.headers.{key}",
                default={
                    "name": "Naam",
                    "tests": "Tests",
                    "average": "Gem. %",
                    "best": "Beste %",
                    "last": "Laatste",
                }[key],
            )
            header_surface = self.small_font.render(text, True, settings.COLOR_TEXT_DIM)
            surface.blit(header_surface, (x, card.top + 74))

        y = card.top + 108
        active_id = self.app.active_profile.identifier
        for index, summary in enumerate(self.leaderboard_rows[:8]):
            color = settings.COLOR_SELECTION if summary.profile_id == active_id else settings.COLOR_TEXT_PRIMARY
            name_surface = self.body_font.render(summary.display_name, True, color)
            surface.blit(name_surface, (col_x[0], y))

            tests_surface = self.body_font.render(str(summary.tests), True, color)
            surface.blit(tests_surface, (col_x[1], y))

            avg_surface = self.body_font.render(f"{summary.average_accuracy * 100:.0f}%", True, color)
            surface.blit(avg_surface, (col_x[2], y))

            best_surface = self.body_font.render(f"{summary.best_accuracy * 100:.0f}%", True, color)
            surface.blit(best_surface, (col_x[3], y))

            if summary.last_played:
                last_surface = self.body_font.render(summary.last_played.strftime("%d %b"), True, color)
                surface.blit(last_surface, (col_x[4], y))

            y += 36
            if index % 2 == 1:
                divider = pygame.Rect(card.left + 24, y - 4, card.width - 48, 1)
                pygame.draw.rect(surface, (255, 255, 255, 60), divider)

    def _draw_buttons(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        bottom = surface.get_height() - margin - 90
        total_width = 700
        right = surface.get_width() - margin
        start_x = right - total_width

        configs = [
            ("start_test", pygame.Rect(start_x, bottom, 240, 78)),
            ("go_practice", pygame.Rect(start_x + 260, bottom, 220, 78)),
        ]

        mouse_pos = pygame.mouse.get_pos()
        self.buttons = []
        if self.top_back_rect is not None:
            self.buttons.append(("back", self.top_back_rect))
        for action, rect in configs:
            face = draw_glossy_button(
                surface,
                rect,
                self.button_palettes[action],
                selected=False,
                hover=rect.collidepoint(mouse_pos),
                corner_radius=28,
            )
            text_surface = self.button_font.render(self.action_labels[action], True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(text_surface, text_surface.get_rect(center=face.center))
            self.buttons.append((action, rect))

        if self.top_back_rect is not None:
            back_face = draw_glossy_button(
                surface,
                self.top_back_rect,
                self.button_palettes["back"],
                selected=False,
                hover=self.top_back_rect.collidepoint(mouse_pos),
                corner_radius=24,
            )
            back_text = self.button_font.render(self.action_labels["back"], True, settings.COLOR_TEXT_PRIMARY)
            surface.blit(back_text, back_text.get_rect(center=back_face.center))

    # Helpers --------------------------------------------------------
    def _average_accuracy(self, results: Sequence[TestResult]) -> float:
        if not results:
            return 0.0
        return sum(result.accuracy for result in results) / len(results)

    def _average_time(self, results: Sequence[TestResult]) -> float:
        answered = sum(result.answered for result in results)
        if answered == 0:
            return 0.0
        total_time = sum(result.elapsed_seconds for result in results)
        return total_time / max(answered, 1)

    def _accuracy_change(self, results: Sequence[TestResult]) -> float:
        if len(results) < 2:
            return 0.0
        latest = results[-1].accuracy * 100
        previous = results[-2].accuracy * 100
        return latest - previous

    def _longest_streak(self, results: Sequence[TestResult]) -> int:
        best = 0
        running = 0
        for result in results:
            if result.accuracy == 1.0:
                running += 1
            else:
                running = 0
            best = max(best, running)
        return best

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(int(seconds), 0)
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes:02d}:{secs:02d}"


__all__ = ["ProgressOverviewScene"]
