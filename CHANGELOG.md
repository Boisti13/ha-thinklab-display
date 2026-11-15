# Changelog

All notable changes, newest first. Each release is tagged `vX.Y.Z` on `main`.

## Unreleased

## v0.1.0 — 2026-11-15

### Added
- First version: config flow with mDNS discovery (`_arduino._tcp`), re-auth, reconfigure and a poll-interval option; one device per board (ID from its MAC).
- Sensors: case temperature, fan duty, speed, curve demand and manual time left, host answer age, Wi-Fi signal, last restart, parse errors.
- Binary sensors: host link problem, fan running.
- Fan mode select (auto / manual), fan duty number (sets manual), buttons for next page, redraw and restart.
- Diagnostics (login and SSID redacted); English and German; brand icon.

### Under the hood
- Tests with `pytest-homeassistant-custom-component`; GitHub checks: hassfest, HACS, ruff, tests on the newest and on Home Assistant 2025.8.
