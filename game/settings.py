"""Global settings and helper functions for the multiplication game."""

from __future__ import annotations

from pathlib import Path

import pygame

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
FPS = 60
SCREEN_MARGIN = 96

# Colour palette aligned with the vibrant avatar artwork.
COLOR_BACKGROUND = (255, 145, 90)
COLOR_ACCENT = (254, 191, 76)
COLOR_ACCENT_LIGHT = (255, 255, 255)
COLOR_TEXT_PRIMARY = (35, 46, 67)
COLOR_TEXT_DIM = (102, 92, 92)
COLOR_SELECTION = (73, 195, 86)
COLOR_INACTIVE_OVERLAY = (255, 255, 255, 60)
COLOR_CARD_BASE = (255, 220, 198)
COLOR_CARD_INACTIVE = (228, 206, 192)
COLOR_NAV_BG = (255, 191, 71)
COLOR_NAV_ICON = (83, 49, 74)

GRADIENT_TOP = (255, 163, 68)
GRADIENT_BOTTOM = (248, 73, 147)

ROOT_DIR = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT_DIR / "assets" / "fonts"
TITLE_FONT_FILE = FONT_DIR / "palamecia_titling.otf"
FONT_PREFERRED = "Avenir Next"
BODY_FALLBACK = "Verdana"


def load_font(size: int) -> pygame.font.Font:
    """Return a font object, falling back to the default if preferred not found."""

    pygame.font.init()
    font_path = pygame.font.match_font(FONT_PREFERRED, bold=False, italic=False)
    if not font_path:
        font_path = pygame.font.match_font(BODY_FALLBACK, bold=False, italic=False)
    return pygame.font.Font(font_path, size) if font_path else pygame.font.Font(None, size)


def load_title_font(size: int) -> pygame.font.Font:
    """Return the custom title font if available, otherwise fall back."""

    pygame.font.init()
    if TITLE_FONT_FILE.exists():
        try:
            return pygame.font.Font(str(TITLE_FONT_FILE), size)
        except OSError:
            # Fall back to system font if the custom font can't be loaded.
            pass
    return load_font(size)
