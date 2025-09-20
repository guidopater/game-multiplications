# Project Definition

This document captures the shared understanding of the multiplication game so future updates can build on the same foundations.

## Vision & Tone
- A playful, confidence-building environment for children to master multiplication.
- Bright visuals, gentle audio, and positive reinforcement over pressure.
- Profiles keep progress personal while allowing siblings to share one installation.

## Core Flows
- **Main Menu (`MainMenuScene`)**: hub that surfaces the primary modes, profile selector, and quick feedback.
- **Practice Mode**
  - No timers or coins; focus on repetition and understanding.
  - Player chooses tables only (`PracticeSetupScene`).
  - Session (`PracticeSessionScene`) adapts question weighting using recent accuracy and answer time so tricky tables resurface more often.
  - Exiting shows a summary (`PracticeSummaryScene`) with accuracy, streaks, tricky tables, and quick tips. Players can restart with the same configuration or return to the menu.
- **Progress Overview**
  - "Hoe deed je het?" opens `ProgressOverviewScene` with the latest test highlight, friendly trends, and a leaderboard comparing profiles.
  - Pulls historical tests from `ScoreRepository` and spotlights tricky tables to focus on next time.
- **Settings (`SettingsScene`)**
  - Central place for audio toggles, default practice/test voorkeuren, feedbackstijl, taalkeuze, en grote-tekstmodus.
  - Beheert profielen (naam wijzigen, nieuw profiel, reset munten) en data-acties (export/reset).
  - Bevat een "koop een koffie"-call-to-action met uitleg over het advertentievrije, privacyvriendelijke karakter van het spel.
- **Test Mode** (partially implemented)
  - Time-bound challenge configured in `TestSetupScene` with table selection, number of questions, and speed presets.
  - Results will feed coins and the leaderboard through `ScoreRepository`.

## Data & Persistence
- Profiles live in `data/profiles.json` and include identifier, display name, avatar, and coin balance.
- Test results persist via `ScoreRepository` into `data/scores.json` for future leaderboards.
- Practice sessions are ephemeral; statistics exist in-memory and inform adaptive question selection plus the summary UI.

## Design Principles
1. **Warm feedback**: celebrate correct answers, soften mistakes with guidance rather than penalties.
2. **Progress transparency**: show key stats (attempts, streak, accuracy) without overwhelming detail.
3. **Adaptivity**: track per-table timing and correctness to prioritise what needs work.
4. **Low friction**: keyboard-friendly input, minimal clicks to start practising, graceful handling of missing assets.
5. **Resilience**: degrade visuals or sounds when assets are missing instead of crashing.

## Scene Interaction Overview
- `App` initialises pygame, loads profiles/sounds, stores shared resources, and swaps scenes.
- Scenes inherit from `Scene` for consistent gradient backgrounds and optional back buttons.
- UI helpers like `draw_glossy_button` provide the signature candy look.
- Practice scenes currently operate independently; test and future screens should follow the same scene contract so the main menu can swap seamlessly.

## Next Architectural Steps
- Complete the test session/summaries and persist results with richer analytics.
- Build the leaderboard and settings scenes linked from the menu.
- Factor out shared table-selection widgets if configuration UIs start to diverge.
- Consider a lightweight service layer for awarding coins or achievements once multiple scenes need the same logic.

Keep this file updated whenever we introduce new scenes, persistence rules, or guiding principles.
