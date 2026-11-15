# ThinkLab Display for Home Assistant

[![Validate](https://github.com/Boisti13/ha-thinklab-display/actions/workflows/validate.yml/badge.svg)](https://github.com/Boisti13/ha-thinklab-display/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/Boisti13/ha-thinklab-display?include_prereleases&sort=semver)](https://github.com/Boisti13/ha-thinklab-display/releases)
[![HACS: custom](https://img.shields.io/badge/HACS-custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![License: MIT](https://img.shields.io/github/license/Boisti13/ha-thinklab-display)](LICENSE)

A Home Assistant integration for the **ThinkLab display**: a small ESP32-C3
e-paper screen that sits on a Proxmox host's USB port and shows the host's
load, guests and disks
([firmware](https://github.com/Boisti13/ThinkLab-ESP),
[host service](https://github.com/Boisti13/ThinkLab-Host)). The board also
measures the case temperature and drives a case fan. This integration
brings all of that into Home Assistant as one device, and lets you control
the fan and the screen.

## Highlights

- **Set up in the UI**: the board is found on the network by itself
  (mDNS); enter its web login and you're done. Or type the address.
- **Case temperature and fan**: duty, speed, what the temperature curve
  asks for, auto or manual, minutes left in manual mode
- **Fan control**: a mode select (auto / manual) and a duty slider; manual
  mode ends on the board by itself after an hour or at 50 °C
- **Host link**: a problem sensor when the screen stops getting data from
  the Proxmox host, and the age of the last answer
- **Screen buttons**: next page, redraw, restart the board
- **Local only**: talks to the board's web API on your network, nothing in
  the cloud. Re-auth, reconfigure, poll interval option, diagnostics.
  English and German.

## Install

| Step | |
|---|---|
| 1 | HACS → ⋮ → *Custom repositories* → `https://github.com/Boisti13/ha-thinklab-display`, type *Integration* |
| 2 | Download **ThinkLab Display**, restart Home Assistant |
| 3 | *Settings → Devices & services*: accept the discovered board, or *Add integration → ThinkLab Display* |
| 4 | Enter the board's web login (`WEB_USER`/`WEB_PASS` from its `secrets.ini`) |

Needs board firmware **0.3.2** or later (it sends the board's MAC address,
which the integration uses as the device's ID) and Home Assistant 2025.8 or
later.

## Entities

One device per board (named after its host name, e.g. *ThinkLab-esp32*).

| Entity | Type | What |
|---|---|---|
| Case temperature | sensor | DS18B20 in the case, °C |
| Fan duty | sensor | PWM duty the fan gets, % |
| Fan speed | sensor | tachometer, rpm |
| Fan manual time left | sensor | until the board goes back to auto |
| Fan curve demand | sensor (diagnostic) | what the temperature curve asks for, % |
| Host answer age | sensor (diagnostic) | seconds since the last answer from the host |
| Wi-Fi signal | sensor (diagnostic) | dBm |
| Last restart | sensor (diagnostic) | when the board last started |
| Parse errors | sensor (diagnostic, off by default) | answers the board couldn't read |
| Host link | binary sensor (problem) | on when the screen marks its data stale |
| Fan | binary sensor (running) | fan on or off |
| Fan mode | select | *auto* (temperature curve) or *manual* (keeps the current duty) |
| Fan duty setting | number | sets manual mode at that duty, 0–100 % |
| Next page, Redraw page | button | e-paper screen |
| Restart | button (config) | restarts the board |

## Example

Tell me when the case fan is driven but doesn't turn:

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.thinklab_esp32_fan_1_speed
    below: 100
    for: "00:05:00"
conditions:
  - condition: state
    entity_id: binary_sensor.thinklab_esp32_fan
    state: "on"
actions:
  - action: notify.notify
    data:
      message: "ThinkLab case fan stopped"
```

## How it works

Every 30 seconds (option: 10–600) the integration reads the board's
`/status.json` with HTTP basic auth. Commands are `POST`s:
`/api/fan/manual/<0..100>`, `/api/fan/auto`, `/api/ui/page/next`,
`/api/ui/page/update`, `/api/esp/reboot`. While the board is off the network
its entities are *unavailable*; a refused login starts re-authentication.

## Layout

| Path | What |
|---|---|
| `custom_components/thinklab_display/` | the integration |
| `tests/` | pytest with `pytest-homeassistant-custom-component`, a recorded `status.json` |
| `.github/workflows/validate.yml` | hassfest, HACS, ruff, tests on the newest and the oldest supported Home Assistant |

## Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest -q
```

`requirements_test_min.txt` pins the oldest supported Home Assistant
(2025.8.0, as in `hacs.json`). See [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)
