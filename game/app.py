"""Main application loop for the multiplication game."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Type

import pygame

from . import settings
from .locale import Translator
from .models import PlayerProfile, GameSettings
from .scenes.base import Scene
from .scenes.main_menu import MainMenuScene
from .preferences import SettingsStore
from .storage import ScoreRepository
from .avatar_utils import gradient_from_avatar


class App:
    """Owns the main loop, current scene, and shared resources."""

    def __init__(self) -> None:
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        is_web = sys.platform == "emscripten" or bool(os.environ.get("PYGBAG"))
        if is_web:
            screen_size = (1280, 720)
            self.screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
        else:
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
        if not is_web:
            self.data_dir.mkdir(parents=True, exist_ok=True)

        self._avatar_options = self._discover_avatars()

        self.scores = ScoreRepository(self.data_dir / "scores.json")
        self.settings_store = SettingsStore(self.data_dir / "settings.json")
        self.settings: GameSettings = self.settings_store.load()
        self.translator = Translator(self.assets_dir / "locale", self.settings.language, default_language="nl")
        self.profiles = self._load_profiles()
        self.active_profile_index = 0
        self.active_profile: PlayerProfile | None = self.profiles[0] if self.profiles else None
        self._base_gradient = (settings.GRADIENT_TOP, settings.GRADIENT_BOTTOM)
        self._avatar_gradient_cache: Dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {}
        self.coin_icon = self._load_coin_icon(self.assets_dir / "images" / "coin.png")
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._load_sounds()
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(1.0 if self.settings.music_enabled else 0.0)
        if self.active_profile is not None:
            self._apply_profile_style(self.active_profile)
        self.save_profiles()

        if self.active_profile is not None:
            self._scene: Scene = MainMenuScene(self)
        else:
            from .scenes.profile_onboarding import ProfileOnboardingScene

            self._scene = ProfileOnboardingScene(self)

        print(f"Scene: {type(self._scene).name}")        

    @property
    def scene(self) -> Scene:
        return self._scene

    def change_scene(self, new_scene_cls: Type[Scene], **kwargs: object) -> None:
        """Replace the active scene with a new one."""

        self._scene = new_scene_cls(self, **kwargs)

    def list_avatar_filenames(self) -> List[str]:
        """Return available avatar assets sorted by numeric suffix."""

        if not self._avatar_options:
            return []
        return list(self._avatar_options)

    def default_avatar_filename(self, fallback_index: int | None = None) -> str:
        if not self._avatar_options:
            return ""
        if fallback_index is not None and 0 <= fallback_index < len(self._avatar_options):
            return self._avatar_options[fallback_index]
        return self._avatar_options[0]

    def set_active_profile(self, profile: PlayerProfile) -> None:
        try:
            index = next(i for i, p in enumerate(self.profiles) if p.identifier == profile.identifier)
        except StopIteration:
            index = 0
        self.active_profile_index = index
        self.active_profile = profile
        self._apply_profile_style(profile)

    def _load_profiles(self) -> List[PlayerProfile]:
        """Load player profiles from JSON if available."""

        # Load from localStorage in web builds
        if sys.platform == "emscripten" or bool(os.environ.get("PYGBAG")):
            try:
                import js  # type: ignore

                raw = js.localStorage.getItem("profiles")
                if raw is None:
                    return []
                payload = json.loads(str(raw))
            except Exception:
                return []
        else:
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
                if not avatar_filename:
                    avatar_filename = self.default_avatar_filename()
                profiles.append(PlayerProfile(identifier, display_name, avatar_filename, coins=coins))
        return profiles

    def save_profiles(self) -> None:
        data = [profile.to_dict() for profile in self.profiles]
        if sys.platform == "emscripten" or bool(os.environ.get("PYGBAG")):
            try:
                import js  # type: ignore

                js.localStorage.setItem("profiles", json.dumps(data))
            except Exception:
                pass
        else:
            config_path = self.data_dir / "profiles.json"
            config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _apply_profile_style(self, profile: PlayerProfile | None) -> None:
        avatar_filename = profile.avatar_filename if profile else None
        self.update_gradient_for_avatar(avatar_filename)

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
        if profile is None:
            return 0
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

    def _discover_avatars(self) -> List[str]:
        images_dir = self.assets_dir / "images"
        if not images_dir.exists():
            return []
        pattern = re.compile(r"avatar_(\d+)\.png$", re.IGNORECASE)
        avatars: List[tuple[int, str]] = []
        for path in images_dir.glob("avatar_*.png"):
            match = pattern.match(path.name)
            if match:
                try:
                    index = int(match.group(1))
                except ValueError:
                    index = 0
                avatars.append((index, path.name))
            else:
                avatars.append((10_000, path.name))
        if not avatars:
            return []
        avatars.sort(key=lambda item: (item[0], item[1]))
        return [name for _, name in avatars]

    def update_gradient_for_avatar(self, avatar_filename: str | None) -> None:
        top, bottom = self._get_gradient_for_avatar(avatar_filename)
        settings.GRADIENT_TOP = top
        settings.GRADIENT_BOTTOM = bottom

    def _get_gradient_for_avatar(self, avatar_filename: str | None) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        if not avatar_filename:
            return self._base_gradient
        cached = self._avatar_gradient_cache.get(avatar_filename)
        if cached:
            return cached
        path = self.assets_dir / "images" / avatar_filename
        gradient = gradient_from_avatar(path, self._base_gradient)
        self._avatar_gradient_cache[avatar_filename] = gradient
        return gradient


__all__ = ["App"]
