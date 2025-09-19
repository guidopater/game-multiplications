# Table Practice Game

A colourful multiplication practice game for kids, built with Python and Pygame. The project starts with a playful main menu and will grow into full practice and test modes, complete with configurable time limits and a persistent leaderboard.

## Getting Started

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:
   ```bash
   pip install pygame
   ```
3. Run the game:
   ```bash
   python3 main.py
   ```

## Roadmap

- Practice mode without time pressure.
- Test mode with selectable time limits (10 / 8 / 7 minutes signalled by animal mascots).
- Table selection screen for focused practice.
- Leaderboard that tracks accuracy and speed.
- Vibrant animations, sound effects, and UI polish.

## Project Structure (in progress)

- `main.py` – entry point that launches the game loop.
- `game/` – core package containing application logic and scenes.
  - `app.py` – manages the window, main loop, and active scene.
  - `settings.py` – shared constants (resolution, colours, fonts).
  - `scenes/` – scene modules (main menu implemented; more coming soon).
- `assets/` – images, fonts, and sounds.
- `data/` – persistent files such as leaderboards and profile configuration.

### Personalising Profiles

- Update `data/profiles.json` to add, remove, or rename profiles.
- Place matching avatar images in `assets/images/` (PNG with transparency works best).
- Omit the `avatar` field to use the playful default icon that the game generates on the fly.

## Display

The game opens in a standard macOS window that defaults to the full screen size and can be resized if needed.

Contributions, ideas, and playful suggestions are welcome!
