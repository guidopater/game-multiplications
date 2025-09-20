"""Main application loop for the multiplication game."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Type

import pygame

from . import settings
from .models import PlayerProfile, GameSettings
from .scenes.base import Scene
from .scenes.main_menu import MainMenuScene
from .preferences import SettingsStore
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
        pygame.display.set_caption("Tafelhelden")
        root = Path(__file__).resolve().parents[1]
        icon_path = root / "assets" / "images" / "icon.png"
        if icon_path.exists():
            try:
                icon_surface = pygame.image.load(str(icon_path)).convert_alpha()
                pygame.display.set_icon(icon_surface)
            except pygame.error:
                pass
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets_dir = root / "assets"
        self.data_dir = root / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.scores = ScoreRepository(self.data_dir / "scores.json")
        self.settings_store = SettingsStore(self.data_dir / "settings.json")
        self.settings: GameSettings = self.settings_store.load()
        self.profiles = self._load_profiles()
        if not self.profiles:
            self.profiles = [
                PlayerProfile("feline", "Feline", "avatar_1.png", coins=0),
                PlayerProfile("julius", "Julius", "avatar_2.png", coins=0),
            ]
            self.save_profiles()
        self.active_profile_index = 0
        self.active_profile: PlayerProfile = self.profiles[self.active_profile_index]
        self.profile_styles: dict[str, dict[str, tuple[int, int, int] | tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
            "feline": {
                "gradient": ((255, 163, 68), (248, 73, 147)),
            },
            "julius": {
                "gradient": ((92, 215, 144), (33, 150, 83)),
            },
        }
        self.coin_icon = self._load_coin_icon(self.assets_dir / "images" / "coin.png")
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._load_sounds()
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(1.0 if self.settings.music_enabled else 0.0)
        self._apply_profile_style(self.active_profile.identifier)
        self.save_profiles()

        self._scene: Scene = MainMenuScene(self)

    @property
    def scene(self) -> Scene:
        return self._scene

    def change_scene(self, new_scene_cls: Type[Scene], **kwargs: object) -> None:
        """Replace the active scene with a new one."""

        self._scene = new_scene_cls(self, **kwargs)

    def set_active_profile(self, profile: PlayerProfile) -> None:
        try:
            index = next(i for i, p in enumerate(self.profiles) if p.identifier == profile.identifier)
        except StopIteration:
            index = 0
        self.active_profile_index = index
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
            coins = int(item.get("coins", 0))
            if identifier:
                profiles.append(PlayerProfile(identifier, display_name, avatar_filename, coins=coins))
        return profiles

    def save_profiles(self) -> None:
        config_path = self.data_dir / "profiles.json"
        data = [profile.to_dict() for profile in self.profiles]
        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

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
            "good": "good1.mp3",
            "wrong": "wrong.mp3",
            "back": "whoosh.mp3",
        }
        for key, filename in sound_map.items():
            path = self.assets_dir / "sounds" / filename
            if path.exists():
                try:
                    self.sounds[key] = pygame.mixer.Sound(str(path))
                except pygame.error:
                    continue

    def play_sound(self, key: str) -> None:
        if not self.settings.effects_enabled:
            return
        sound = self.sounds.get(key)
        if sound:
            sound.play()

    def toggle_music(self, enabled: bool) -> None:
        self.settings.music_enabled = enabled
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(1.0 if enabled else 0.0)
        self.save_settings()

    def adjust_active_coins(self, delta: int) -> int:
        profile = self.active_profile
        profile.coins = max(0, profile.coins + delta)
        self.profiles[self.active_profile_index] = profile
        self.save_profiles()
        return profile.coins

    def save_settings(self) -> None:
        self.settings_store.save(self.settings)

    def _load_coin_icon(self, path: Path) -> pygame.Surface | None:
        if not path.exists():
            return None
        try:
            icon = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None
        return pygame.transform.smoothscale(icon, (28, 28))

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
