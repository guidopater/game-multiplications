"""Main application loop for the multiplication game."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Type

import pygame

from . import settings
from .models import PlayerProfile
from .scenes.base import Scene
from .scenes.main_menu import MainMenuScene
from .storage import ScoreRepository


class App:
    """Owns the main loop, current scene, and shared resources."""

    def __init__(self) -> None:
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        display_info = pygame.display.Info()
        screen_size = (display_info.current_w, display_info.current_h)
        self.screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
        settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT = screen_size
        settings.SCREEN_SIZE = screen_size
        pygame.display.set_caption("Tafelheld")
        icon_path = root / "assets" / "images" / "icon.png"
        if icon_path.exists():
            try:
                icon_surface = pygame.image.load(str(icon_path)).convert_alpha()
                pygame.display.set_icon(icon_surface)
            except pygame.error:
                pass
        self.clock = pygame.time.Clock()
        self.running = True

        root = Path(__file__).resolve().parents[1]
        self.assets_dir = root / "assets"
        self.data_dir = root / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.scores = ScoreRepository(self.data_dir / "scores.json")
        self.profiles = self._load_profiles()
        if not self.profiles:
            self.profiles = [
                PlayerProfile("feline", "Feline", "avatar_feline.png"),
                PlayerProfile("julius", "Julius", "avatar_julius.png"),
            ]
        self.active_profile: PlayerProfile = self.profiles[0]
        self.profile_styles: dict[str, dict[str, tuple[int, int, int] | tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
            "feline": {
                "gradient": ((255, 163, 68), (248, 73, 147)),
            },
            "julius": {
                "gradient": ((92, 215, 144), (33, 150, 83)),
            },
        }
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._load_sounds()
        self._apply_profile_style(self.active_profile.identifier)

        self._scene: Scene = MainMenuScene(self)

    @property
    def scene(self) -> Scene:
        return self._scene

    def change_scene(self, new_scene_cls: Type[Scene], **kwargs: object) -> None:
        """Replace the active scene with a new one."""

        self._scene = new_scene_cls(self, **kwargs)

    def set_active_profile(self, profile: PlayerProfile) -> None:
        self.active_profile = profile
        self._apply_profile_style(profile.identifier)

    def _load_profiles(self) -> List[PlayerProfile]:
        """Load player profiles from JSON if available."""

        config_path = self.data_dir / "profiles.json"
        if not config_path.exists():
            return []

        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if not isinstance(payload, list):
            return []

        profiles: List[PlayerProfile] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            identifier = str(item.get("id", "")).strip()
            display_name = str(item.get("display_name", "")).strip() or identifier.capitalize()
            avatar_filename = str(item.get("avatar", "")).strip()
            if identifier:
                profiles.append(PlayerProfile(identifier, display_name, avatar_filename))
        return profiles

    def _apply_profile_style(self, profile_id: str) -> None:
        style = self.profile_styles.get(profile_id)
        if not style:
            style = next(iter(self.profile_styles.values()), None)
        if style and "gradient" in style:
            top, bottom = style["gradient"]  # type: ignore[assignment]
            settings.GRADIENT_TOP = top
            settings.GRADIENT_BOTTOM = bottom

    def _load_sounds(self) -> None:
        if not pygame.mixer.get_init():
            return
        sound_map = {
            "good": "good.wav",
            "wrong": "wrong.wav",
        }
        for key, filename in sound_map.items():
            path = self.assets_dir / "sounds" / filename
            if path.exists():
                try:
                    self.sounds[key] = pygame.mixer.Sound(str(path))
                except pygame.error:
                    continue

    def play_sound(self, key: str) -> None:
        sound = self.sounds.get(key)
        if sound:
            sound.play()

    def run(self) -> None:
        """Main loop of the application."""

        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            self._scene.handle_events(events)
            self._scene.update(dt)
            self._scene.render(self.screen)
            pygame.display.flip()

        pygame.quit()


__all__ = ["App"]
