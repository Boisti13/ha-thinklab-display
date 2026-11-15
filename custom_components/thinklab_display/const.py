"""Constants for the ThinkLab display integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "thinklab_display"
MANUFACTURER = "ThinkLab"
MODEL = "ESP32-C3 e-paper host display"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 600

# The firmware that first sends everything this integration reads ("mac" etc.)
MIN_FIRMWARE = "0.3.2"

# Uptime may drift by a few seconds between polls; only move the boot time
# when it changes by more than this, so the sensor doesn't flap.
BOOT_TIME_TOLERANCE = timedelta(seconds=60)

FAN_MODE_AUTO = "auto"
FAN_MODE_MANUAL = "manual"
