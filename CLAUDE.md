# ha-thinklab-display — working rules

Home Assistant custom integration (domain `thinklab_display`) for the
ThinkLab e-paper display (firmware repo **ThinkLab-ESP**, host service
**ThinkLab-Host**). It polls the board's `/status.json` and sends commands
to its web API. The JSON fields and endpoints are defined by the firmware's
`src/modules/web_server.cpp`; a change there and here goes together, with
`MIN_FIRMWARE` in `const.py` raised when the integration needs a newer board.

- **Public repo (MIT).** No real addresses, MACs, SSIDs or logins in code,
  tests or docs (tests use 192.168.1.50 and a made-up MAC). Where the
  owner's board sits is in `claude-setup/homelab.md`.
- Branches: `main` (releases) and `dev` (work). Push to `dev`. Releases
  (tag + GitHub release, version in `manifest.json` and CHANGELOG) only when
  the owner asks.
- **Checks before pushing**, in the dev box venv `~/.venvs/sprout-track-ha`
  (shared with ha-sprout-track; has pytest-homeassistant-custom-component and
  ruff): `ruff check .`, `ruff format --check .`, `python -m pytest -q`; also
  `~/.venvs/sprout-track-ha-min/bin/python -m pytest -q` for the oldest
  supported Home Assistant (2025.8, `hacs.json`). GitHub runs the same plus
  hassfest and HACS (`validate.yml`).
- **In the owner's Home Assistant**: see `homelab.md` (*ThinkLab ESP
  display*). Changes go there only after the checks pass; a new version
  needs a Home Assistant restart.
- Entities: `has_entity_name`, translation keys, English and German in
  `translations/`. A new entity gets a translation, an icon in
  `icons.json` and a test.
- README and CHANGELOG follow the owner's house style (badges, highlights,
  tables; `## vX.Y.Z — date`, Added / Changed / Fixed / Under the hood,
  *Unreleased* on top); update both with every user-visible change.
