"""Interactive practice mode without time pressure."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence

import pygame

from .. import settings
from ..models import PracticeConfig
from ..ui import Button, draw_glossy_button
from .base import Scene


@dataclass(frozen=True)
class PracticeQuestion:
    left: int
    right: int

    @property
    def answer(self) -> int:
        return self.left * self.right

    def as_text(self) -> str:
        return f"{self.left} x {self.right}"


class PracticeSessionScene(Scene):
    """Runs an endless practice loop with adaptive difficulty."""

    def __init__(self, app: "App", config: PracticeConfig) -> None:
        super().__init__(app)
        self.config = config

        self.title_font = settings.load_title_font(40)
        self.question_font = settings.load_font(110)
        self.helper_font = settings.load_font(26)
        self.count_font = settings.load_font(32)
        self.feedback_font = settings.load_font(32)

        self.table_stats: Dict[int, Dict[str, float]] = defaultdict(
            lambda: {"questions": 0.0, "correct": 0.0, "incorrect": 0.0, "total_time": 0.0}
        )
        self.history: List[tuple[PracticeQuestion, str, bool, float]] = []

        self.answer_effects: List[dict[str, object]] = []

        self.elapsed = 0.0
        self.question_start_time = 0.0

        self._initial_prompt = self.tr(
            "practice_session.feedback.initial",
            default=self.tr(
                "common.feedback.answer_hint",
                default="Typ het antwoord en druk op ENTER",
            ),
        )
        self.feedback_message = self._initial_prompt
        self.feedback_timer = 0.0

        self.input_value = ""
        self.total_attempts = 0
        self.correct_answers = 0
        self.streak = 0

        self.current_question: PracticeQuestion = self._create_question()
        self.awaiting_retry = False

        default_positive = self.tr_list(
            "common.feedback.correct_default",
            default=["Top!", "Geweldig!", "Lekker bezig!"],
        )
        self._positive_feedback_options = (
            self.tr_list(
                "practice_session.feedback.correct",
                default=default_positive,
            )
            or default_positive
        )

        self.back_palette = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }
        self.back_button = Button(
            pygame.Rect(0, 0, 160, 52),
            self.tr("common.stop", default="Stoppen"),
            self.helper_font,
            self.back_palette,
            text_color=settings.COLOR_TEXT_PRIMARY,
            callback=self.on_back,
        )
        self.back_button_rect: pygame.Rect | None = None

    # Event handling -------------------------------------------------
    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                    self.on_back()
                    return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.on_back()
                    return
                if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                    self.input_value = self.input_value[:-1]
                elif event.key == pygame.K_RETURN:
                    self._submit_answer()
                elif event.unicode.isdigit():
                    if len(self.input_value) < 4:
                        self.input_value += event.unicode

    # Update ---------------------------------------------------------
    def update(self, delta_time: float) -> None:
        self.elapsed += delta_time
        if self.feedback_timer > 0:
            self.feedback_timer = max(self.feedback_timer - delta_time, 0)
            if self.feedback_timer == 0:
                self.feedback_message = self._initial_prompt

    # Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._draw_header(surface)
        self._draw_question(surface)
        self._draw_input(surface)
        self._draw_progress(surface)
        self._draw_feedback(surface)
        self._draw_answer_effects(surface)
        self._draw_back_button(surface)

    # Draw helpers ---------------------------------------------------
    def _draw_header(self, surface: pygame.Surface) -> None:
        profile = self.app.active_profile
        margin = settings.SCREEN_MARGIN
        back_right = (self.back_button_rect.right + 40) if self.back_button_rect else (margin + 40)
        title_label = self.tr(
            "practice_session.title",
            default="Oefenen met {name}",
            name=profile.display_name,
        )
        title_text = self.title_font.render(title_label, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(title_text, (back_right, margin - 20))

        tables_text = ", ".join(str(n) for n in self.config.tables)
        subtitle_label = self.tr(
            "practice_session.tables",
            default="Tafels: {tables}",
            tables=tables_text,
        )
        subtitle = self.helper_font.render(subtitle_label, True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, (back_right + 4, margin + 24))

    def _draw_question(self, surface: pygame.Surface) -> None:
        question_surface = self.question_font.render(self.current_question.as_text(), True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(question_surface, question_surface.get_rect(center=self._question_center()))

    def _draw_input(self, surface: pygame.Surface) -> None:
        input_box = pygame.Rect(0, 0, 260, 74)
        input_box.center = (surface.get_width() // 2, surface.get_height() // 2 + 40)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, input_box, border_radius=22)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, input_box, width=3, border_radius=22)
        answer_text = self.count_font.render(self.input_value or "?", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(answer_text, answer_text.get_rect(center=input_box.center))
        hint_text = self.tr(
            "practice_session.input_hint",
            default=self.tr(
                "common.feedback.answer_hint",
                default="Typ het antwoord en druk op ENTER",
            ),
        )
        hint = self.helper_font.render(hint_text, True, settings.COLOR_TEXT_DIM)
        surface.blit(hint, hint.get_rect(center=(input_box.centerx, input_box.bottom + 36)))

    def _draw_progress(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        turns_text = self.tr(
            "practice_session.progress.turns",
            default=self.tr(
                "common.stats.turns",
                default="Beurten: {count}",
                count=self.total_attempts,
            ),
            count=self.total_attempts,
        )
        progress_text = self.count_font.render(turns_text, True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(progress_text, (margin, surface.get_height() - margin - 100))

        correct_label = self.tr(
            "practice_session.progress.correct",
            default=self.tr(
                "common.stats.correct",
                default="Goed: {count}",
                count=self.correct_answers,
            ),
            count=self.correct_answers,
        )
        wrong_label = self.tr(
            "practice_session.progress.wrong",
            default=self.tr(
                "common.stats.incorrect",
                default="Fout: {count}",
                count=self.total_attempts - self.correct_answers,
            ),
            count=self.total_attempts - self.correct_answers,
        )
        streak_label = self.tr(
            "practice_session.progress.streak",
            default=self.tr(
                "common.stats.streak",
                default="Streak: {count}",
                count=self.streak,
            ),
            count=self.streak,
        )
        correct_text = self.helper_font.render(correct_label, True, settings.COLOR_SELECTION)
        wrong_text = self.helper_font.render(wrong_label, True, settings.COLOR_ACCENT_LIGHT)
        streak_text = self.helper_font.render(streak_label, True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(correct_text, (margin, surface.get_height() - margin - 60))
        surface.blit(wrong_text, (margin + 160, surface.get_height() - margin - 60))
        surface.blit(streak_text, (margin, surface.get_height() - margin - 30))

    def _draw_feedback(self, surface: pygame.Surface) -> None:
        if not self.feedback_message:
            return
        alpha = 255 if self.feedback_timer > 1 else int(255 * self.feedback_timer)
        text_surface = self.feedback_font.render(self.feedback_message, True, settings.COLOR_ACCENT_LIGHT)
        text_surface.set_alpha(alpha)
        rect = text_surface.get_rect(center=(surface.get_width() // 2, settings.SCREEN_MARGIN + 120))
        surface.blit(text_surface, rect)

    def _draw_back_button(self, surface: pygame.Surface) -> None:
        margin = settings.SCREEN_MARGIN
        stop_label = self.tr("common.stop", default="Stoppen")
        self.back_button.label = stop_label
        text = self.helper_font.render(stop_label, True, settings.COLOR_TEXT_PRIMARY)
        padding_x = 32
        padding_y = 18
        width = text.get_width() + padding_x * 2
        height = text.get_height() + padding_y * 2
        rect = pygame.Rect(margin, margin + 6, width, height)
        self.back_button.set_rect(rect)
        self.back_button.render(surface, hover=rect.collidepoint(pygame.mouse.get_pos()))
        self.back_button_rect = rect

    def _question_center(self) -> tuple[int, int]:
        rect = self.app.screen.get_rect()
        return (rect.centerx, rect.centery - 80)

    # Logic ----------------------------------------------------------
    def _create_question(self) -> PracticeQuestion:
        table = self._select_table()
        right = random.randint(1, 10)
        question = PracticeQuestion(table, right)
        self.question_start_time = self.elapsed
        return question

    def _select_table(self) -> int:
        weights = []
        tables = self.config.tables
        for table in tables:
            stats = self.table_stats[table]
            incorrect = stats["incorrect"]
            attempts = stats["questions"]
            avg_time = stats["total_time"] / attempts if attempts else 0.0
            weight = 1.0 + incorrect * 2.5 + avg_time / 4.0
            weights.append(max(weight, 0.1))
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(tables)
        r = random.uniform(0, total_weight)
        cumulative = 0.0
        for table, weight in zip(tables, weights):
            cumulative += weight
            if r <= cumulative:
                return table
        return tables[-1]

    def _submit_answer(self) -> None:
        if not self.input_value:
            self.feedback_message = self.tr(
                "practice_session.feedback.enter_answer",
                default=self.tr(
                    "common.feedback.enter_answer",
                    default="Tik eerst een antwoord in.",
                ),
            )
            self.feedback_timer = 1.5
            return

        question = self.current_question
        try:
            guess = int(self.input_value)
        except ValueError:
            self.feedback_message = self.tr(
                "practice_session.feedback.digits_only",
                default=self.tr(
                    "common.feedback.digits_only",
                    default="Gebruik alleen cijfers.",
                ),
            )
            self.feedback_timer = 1.5
            self.input_value = ""
            return

        answer_time = max(self.elapsed - self.question_start_time, 0.0)
        is_correct = guess == question.answer

        self.total_attempts += 1
        stats = self.table_stats[self._determine_table(question)]
        stats["questions"] += 1
        stats["total_time"] += answer_time
        if is_correct:
            stats["correct"] += 1
        else:
            stats["incorrect"] += 1

        self.history.append((question, self.input_value, is_correct, answer_time))

        if is_correct:
            self.correct_answers += 1
            self.streak += 1
            messages = self.tr_list(
                "practice_session.feedback.correct",
                default=self._positive_feedback_options,
            )
            self.feedback_message = random.choice(messages or self._positive_feedback_options)
            self.feedback_timer = 1.0
            self._spawn_answer_effect(question.as_text())
            self._next_question()
        else:
            self.streak = 0
            self.feedback_message = self.tr(
                "practice_session.feedback.almost",
                default="Bijna! {left} x {right} = {answer}",
                left=question.left,
                right=question.right,
                answer=question.answer,
            )
            self.feedback_timer = 2.5
            self.awaiting_retry = True

        self.input_value = ""

    def _next_question(self) -> None:
        self.current_question = self._create_question()
        self.awaiting_retry = False

    def _determine_table(self, question: PracticeQuestion) -> int:
        if question.left in self.config.tables:
            return question.left
        if question.right in self.config.tables:
            return question.right
        return question.left

    def _spawn_answer_effect(self, text: str) -> None:
        surface = self.question_font.render(text, True, settings.COLOR_SELECTION)
        effect = {
            "surface": surface,
            "start": self.elapsed,
            "duration": 0.45,
            "center": self._question_center(),
            "size": surface.get_size(),
        }
        self.answer_effects.append(effect)

    def _draw_answer_effects(self, surface: pygame.Surface) -> None:
        active: List[dict[str, object]] = []
        for effect in self.answer_effects:
            progress = (self.elapsed - effect["start"]) / effect["duration"]
            if progress >= 1:
                continue
            scale = 1.0 + 1.2 * progress
            width, height = effect["size"]
            scaled = pygame.transform.smoothscale(effect["surface"], (int(width * scale), int(height * scale)))
            scaled.set_alpha(int(255 * (1 - progress)))
            rect = scaled.get_rect(center=effect["center"])
            surface.blit(scaled, rect)
            active.append(effect)
        self.answer_effects = active

    def on_back(self) -> None:
        from .practice_summary import PracticeSummaryScene

        table_stats = {int(k): dict(v) for k, v in self.table_stats.items()}
        self.app.change_scene(
            PracticeSummaryScene,
            total_attempts=self.total_attempts,
            correct=self.correct_answers,
            streak=self.streak,
            table_stats=table_stats,
            history=self.history,
            config=self.config,
        )
