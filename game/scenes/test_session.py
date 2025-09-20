"""Timed multiplication test session."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence, Tuple

import pygame

from .. import settings
from ..ui import draw_glossy_button
from ..models import TestConfig, TestResult
from .base import Scene


@dataclass(frozen=True)
class Question:
    left: int
    right: int

    @property
    def answer(self) -> int:
        return self.left * self.right

    def as_text(self) -> str:
        return f"{self.left} x {self.right}"


class TestSessionScene(Scene):
    """Runs through a timed sequence of multiplication questions."""

    def __init__(self, app: "App", config: TestConfig, speed_label: str) -> None:
        super().__init__(app)
        self.config = config
        self.speed_label = speed_label

        self.title_font = settings.load_title_font(40)
        self.question_font = settings.load_font(110)
        self.helper_font = settings.load_font(26)
        self.count_font = settings.load_font(32)
        self.feedback_font = settings.load_font(32)

        self.questions: List[Question] = self._generate_questions(config)
        self.current_index = 0
        self.input_value = ""
        self.correct = 0
        self.incorrect = 0
        self.history: List[Tuple[Question, str, bool]] = []

        self.elapsed = 0.0
        self.feedback_message = "Succes! Je kunt met ENTER antwoorden."
        self.feedback_timer = 3.0
        self.finished = False
        self.question_start_time = 0.0
        self.table_stats: dict[int, dict[str, float]] = defaultdict(
            lambda: {"questions": 0.0, "correct": 0.0, "incorrect": 0.0, "total_time": 0.0}
        )
        self.session_coins = 0
        self.coin_delta = 0
        self.answer_effects: List[dict[str, object]] = []
        self.coin_effects: List[dict[str, object]] = []
        self.coin_font = settings.load_font(26)
        self.coin_target_pos: tuple[float, float] | None = (
            self.app.screen.get_width() - settings.SCREEN_MARGIN - 40,
            settings.SCREEN_MARGIN + 20,
        )
        self.show_back_button = False
        self.back_button_rect: pygame.Rect | None = None
        self.back_palette = {
            "top": (216, 196, 255),
            "bottom": (176, 148, 227),
            "border": (126, 98, 192),
            "shadow": (102, 78, 152),
        }

    # Event handling -------------------------------------------------
    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        if self.finished:
            return

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                    self.on_back()
                    return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from .main_menu import MainMenuScene

                    self.app.change_scene(MainMenuScene)
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
        if self.finished:
            return

        self.elapsed += delta_time
        remaining = self.config.time_limit_seconds - self.elapsed
        if remaining <= 0:
            self._finish_session(time_up=True)

        if self.feedback_timer > 0:
            self.feedback_timer = max(self.feedback_timer - delta_time, 0)
            if self.feedback_timer == 0:
                self.feedback_message = ""

    # Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        Scene.draw_vertical_gradient(surface, settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._draw_header(surface)
        self._draw_question(surface)
        self._draw_input(surface)
        self._draw_progress(surface)
        self._draw_feedback(surface)
        self._draw_answer_effects(surface)
        self._draw_coin_effects(surface)
        self._draw_back_button(surface)

    # Draw helpers ---------------------------------------------------
    def _draw_header(self, surface: pygame.Surface) -> None:
        profile = self.app.active_profile
        margin = settings.SCREEN_MARGIN
        title_x = margin + 200
        title_text = self.title_font.render(
            f"Test voor {profile.display_name} – {self.speed_label}",
            True,
            settings.COLOR_TEXT_PRIMARY,
        )
        surface.blit(title_text, (title_x, margin - 20))

        tables_text = ", ".join(str(n) for n in self.config.tables)
        subtitle = self.helper_font.render(f"Tafels: {tables_text}", True, settings.COLOR_TEXT_DIM)
        surface.blit(subtitle, (title_x + 4, margin + 24))

        remaining = max(self.config.time_limit_seconds - self.elapsed, 0.0)
        minutes = int(remaining) // 60
        seconds = int(remaining) % 60
        timer_text = self.count_font.render(f"Tijd: {minutes:02d}:{seconds:02d}", True, settings.COLOR_ACCENT_LIGHT)
        timer_x = surface.get_width() - margin - timer_text.get_width() - 20
        surface.blit(timer_text, (timer_x, margin - 20))

        coin_icon = getattr(self.app, "coin_icon", None)
        base_total = profile.coins
        session_color = settings.COLOR_ACCENT if self.session_coins else settings.COLOR_TEXT_DIM
        session_text = self.helper_font.render(f"Munten ronde: {self.session_coins}", True, session_color)
        total_text = self.helper_font.render(f"Totaal: {base_total}", True, settings.COLOR_TEXT_PRIMARY)
        info_x = surface.get_width() - margin - 220
        info_y = margin + 10
        if coin_icon:
            icon_rect = coin_icon.get_rect(topleft=(info_x, info_y))
            surface.blit(coin_icon, icon_rect)
            session_rect = session_text.get_rect(midleft=(icon_rect.right + 10, icon_rect.centery))
            surface.blit(session_text, session_rect)
            total_rect = total_text.get_rect(midleft=(icon_rect.right + 10, icon_rect.centery + 28))
            surface.blit(total_text, total_rect)
            self.coin_target_pos = icon_rect.center
        else:
            session_rect = session_text.get_rect(topleft=(info_x, info_y))
            surface.blit(session_text, session_rect)
            total_rect = total_text.get_rect(topleft=(info_x, session_rect.bottom + 8))
            surface.blit(total_text, total_rect)
            self.coin_target_pos = session_rect.center

    def _draw_question(self, surface: pygame.Surface) -> None:
        if self.current_index >= len(self.questions):
            return
        question = self.questions[self.current_index]
        question_surface = self.question_font.render(question.as_text(), True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(question_surface, question_surface.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 - 80)))

    def _draw_input(self, surface: pygame.Surface) -> None:
        input_box = pygame.Rect(0, 0, 260, 74)
        input_box.center = (surface.get_width() // 2, surface.get_height() // 2 + 40)
        pygame.draw.rect(surface, settings.COLOR_CARD_BASE, input_box, border_radius=22)
        pygame.draw.rect(surface, settings.COLOR_ACCENT, input_box, width=3, border_radius=22)
        answer_text = self.count_font.render(self.input_value or "?", True, settings.COLOR_TEXT_PRIMARY)
        surface.blit(answer_text, answer_text.get_rect(center=input_box.center))
        hint = self.helper_font.render("Typ het antwoord en druk op ENTER", True, settings.COLOR_TEXT_DIM)
        surface.blit(hint, hint.get_rect(center=(input_box.centerx, input_box.bottom + 36)))

    def _draw_progress(self, surface: pygame.Surface) -> None:
        total = len(self.questions)
        progress_text = self.count_font.render(f"{self.current_index + 1 if self.current_index < total else total}/{total}", True, settings.COLOR_TEXT_PRIMARY)
        margin = settings.SCREEN_MARGIN
        surface.blit(progress_text, (margin, surface.get_height() - margin - 120))

        correct_text = self.helper_font.render(f"Goed: {self.correct}", True, settings.COLOR_SELECTION)
        wrong_text = self.helper_font.render(f"Fout: {self.incorrect}", True, settings.COLOR_ACCENT_LIGHT)
        surface.blit(correct_text, (margin, surface.get_height() - margin - 80))
        surface.blit(wrong_text, (margin + 140, surface.get_height() - margin - 80))

    def _draw_feedback(self, surface: pygame.Surface) -> None:
        if not self.feedback_message:
            return
        alpha = 255 if self.feedback_timer > 1 else int(255 * self.feedback_timer)
        text_surface = self.feedback_font.render(self.feedback_message, True, settings.COLOR_ACCENT_LIGHT)
        text_surface.set_alpha(alpha)
        surface.blit(text_surface, text_surface.get_rect(center=(surface.get_width() // 2, settings.SCREEN_MARGIN + 10)))

    # Logic ----------------------------------------------------------
    def _generate_questions(self, config: TestConfig) -> List[Question]:
        questions: List[Question] = []
        for _ in range(config.question_count):
            table = random.choice(config.tables)
            right = random.randint(1, 10)
            if random.random() > 0.5:
                questions.append(Question(table, right))
            else:
                questions.append(Question(right, table))
        random.shuffle(questions)
        return questions

    def _submit_answer(self) -> None:
        if self.current_index >= len(self.questions):
            return
        if not self.input_value:
            self.feedback_message = "Tik eerst een antwoord in."
            self.feedback_timer = 1.5
            return

        question = self.questions[self.current_index]
        try:
            guess = int(self.input_value)
        except ValueError:
            self.feedback_message = "Gebruik alleen cijfers."
            self.feedback_timer = 1.5
            self.input_value = ""
            return

        is_correct = guess == question.answer
        answer_time = max(self.elapsed - self.question_start_time, 0.0)
        self.history.append((question, self.input_value, is_correct))
        self._record_table_stat(question, is_correct, answer_time)

        table = self._determine_table(question)
        per_reward = self._per_question_reward(table)
        delta = per_reward if is_correct else -max(2, per_reward // 2)
        if delta:
            self.session_coins = max(0, self.session_coins + delta)
            self._spawn_coin_effect(delta)

        if is_correct:
            self.correct += 1
            self.feedback_message = random.choice(["Yes!", "Top!", "Lekker bezig!"])
            self.feedback_timer = 1.0
            self.app.play_sound("good")
            self._spawn_answer_effect(question.as_text())
        else:
            self.incorrect += 1
            self.feedback_message = f"Oei! {question.left} x {question.right} = {question.answer}"
            self.feedback_timer = 2.5
            self.app.play_sound("wrong")

        self.input_value = ""
        self.current_index += 1
        self.question_start_time = self.elapsed

        if self.current_index >= len(self.questions):
            self._finish_session(time_up=False)

    def _finish_session(self, *, time_up: bool) -> None:
        if self.finished:
            return
        self.finished = True
        result = TestResult(
            profile_id=self.app.active_profile.identifier,
            profile_name=self.app.active_profile.display_name,
            tables=self.config.tables,
            question_count=self.config.question_count,
            answered=len(self.history),
            correct=self.correct,
            incorrect=self.incorrect,
            time_limit_seconds=self.config.time_limit_seconds,
            elapsed_seconds=min(self.elapsed, self.config.time_limit_seconds),
            timestamp=datetime.now(),
            table_stats={int(k): dict(v) for k, v in self.table_stats.items()},
        )
        self.coin_delta = self._calculate_reward(result)
        if self.coin_delta:
            self.app.adjust_active_coins(self.coin_delta)
        self.app.scores.record_test(result)

        from .test_summary import TestSummaryScene

        self.app.change_scene(
            TestSummaryScene,
            result=result,
            history=self.history,
            time_up=time_up,
            config=self.config,
            speed_label=self.speed_label,
            table_stats=self.table_stats,
            coin_delta=self.coin_delta,
        )

    def _record_table_stat(self, question: Question, is_correct: bool, answer_time: float) -> None:
        table = self._determine_table(question)
        stats = self.table_stats[table]
        stats["questions"] += 1
        stats["total_time"] += answer_time
        if is_correct:
            stats["correct"] += 1
        else:
            stats["incorrect"] += 1

    def _determine_table(self, question: Question) -> int:
        if question.left in self.config.tables:
            return question.left
        if question.right in self.config.tables:
            return question.right
        # Fallback: return the larger multiplier
        return max(question.left, question.right)

    def _per_question_reward(self, table: int) -> int:
        # Base reward scales gently with table difficulty (roughly 2–4 coins).
        return 2 + table // 4

    def _calculate_reward(self, result: TestResult) -> int:
        total = 0
        for question, _, is_correct in self.history:
            table = self._determine_table(question)
            per = self._per_question_reward(table)
            if is_correct:
                total += per
            else:
                total -= 2

        total = max(0, total)

        if result.time_limit_seconds:
            ratio = result.remaining_seconds / result.time_limit_seconds
        else:
            ratio = 0.0
        time_bonus = int(ratio * 8)
        speed_bonus = {
            "Slak": 0,
            "Schildpad": 2,
            "Haas": 4,
            "Cheeta": 6,
        }.get(self.speed_label, 0)
        total += max(0, time_bonus + speed_bonus)

        return total

    def on_back(self) -> None:
        if hasattr(self.app, "sounds") and "back" in self.app.sounds:
            self.app.sounds["back"].play()
        from .test_setup import TestSetupScene

        self.app.change_scene(TestSetupScene)

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

    def _question_center(self) -> tuple[int, int]:
        rect = self.app.screen.get_rect()
        return (rect.centerx, rect.centery - 80)

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

    def _spawn_coin_effect(self, delta: int) -> None:
        if delta == 0:
            return
        start_pos = self._question_center()
        end_pos = self.coin_target_pos or start_pos
        color = settings.COLOR_SELECTION if delta > 0 else (255, 120, 120)
        self.coin_effects.append(
            {
                "value": delta,
                "start": self.elapsed,
                "duration": 0.85,
                "start_pos": start_pos,
                "end_pos": end_pos,
                "color": color,
            }
        )

    def _draw_answer_effects(self, surface: pygame.Surface) -> None:
        active: List[dict[str, object]] = []
        for effect in self.answer_effects:
            progress = (self.elapsed - effect["start"]) / effect["duration"]
            if progress >= 1:
                continue
            scale = 1.0 + 1.4 * progress
            width, height = effect["size"]
            scaled = pygame.transform.smoothscale(
                effect["surface"], (int(width * scale), int(height * scale))
            )
            scaled.set_alpha(int(255 * (1 - progress)))
            rect = scaled.get_rect(center=effect["center"])
            surface.blit(scaled, rect)
            active.append(effect)
        self.answer_effects = active

    def _draw_coin_effects(self, surface: pygame.Surface) -> None:
        active: List[dict[str, object]] = []
        for effect in self.coin_effects:
            progress = (self.elapsed - effect["start"]) / effect["duration"]
            if progress >= 1:
                continue
            eased = 1 - (1 - progress) ** 2
            start_x, start_y = effect["start_pos"]
            end_x, end_y = effect["end_pos"]
            x = start_x + (end_x - start_x) * eased
            y = start_y + (end_y - start_y) * eased
            text = self.coin_font.render(f"{effect['value']:+d}", True, effect["color"])
            text.set_alpha(int(255 * (1 - progress)))
            rect = text.get_rect(center=(x, y))
            surface.blit(text, rect)
            active.append(effect)
        self.coin_effects = active
