"""Command templates per device type.

These are surfaced in the admin panel as a guided checklist so users
know what to capture. Essential commands feed the auto-mapping that
the entity factory uses to expose capabilities (volume, hvac modes,
etc.).
"""
from __future__ import annotations

from .const import CommandCategory, DeviceType
from .models import CommandTemplate

COMMAND_TEMPLATES: dict[DeviceType, list[CommandTemplate]] = {
    DeviceType.TV: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
        CommandTemplate("Volume Up", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Volume Down", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Mute", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Source/Input", CommandCategory.NAVIGATION, essential=True),
        CommandTemplate("Channel Up", CommandCategory.CHANNEL, essential=True),
        CommandTemplate("Channel Down", CommandCategory.CHANNEL, essential=True),
        CommandTemplate("Up", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Down", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Left", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Right", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Select/OK", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Back/Return", CommandCategory.NAVIGATION, essential=False),
    ],
    DeviceType.AC: [
        CommandTemplate("Power On", CommandCategory.POWER, essential=True),
        CommandTemplate("Power Off", CommandCategory.POWER, essential=True),
        CommandTemplate("Mode: Cool", CommandCategory.MODE, essential=True),
        CommandTemplate("Mode: Heat", CommandCategory.MODE, essential=False),
        CommandTemplate("Mode: Fan", CommandCategory.MODE, essential=False),
        CommandTemplate("Mode: Dry", CommandCategory.MODE, essential=False),
        CommandTemplate("Mode: Auto", CommandCategory.MODE, essential=False),
        CommandTemplate("Fan: Low", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Fan: Medium", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Fan: High", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Fan: Auto", CommandCategory.FAN_SPEED, essential=False),
        CommandTemplate("Swing Toggle", CommandCategory.CUSTOM, essential=False),
    ],
    DeviceType.FAN: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
        CommandTemplate("Speed Up", CommandCategory.FAN_SPEED, essential=True),
        CommandTemplate("Speed Down", CommandCategory.FAN_SPEED, essential=True),
        CommandTemplate("Oscillate", CommandCategory.CUSTOM, essential=False),
        CommandTemplate("Timer", CommandCategory.CUSTOM, essential=False),
    ],
    DeviceType.SOUNDBAR: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
        CommandTemplate("Volume Up", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Volume Down", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Mute", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Source/Input", CommandCategory.NAVIGATION, essential=True),
    ],
    DeviceType.PROJECTOR: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
        CommandTemplate("Source/Input", CommandCategory.NAVIGATION, essential=True),
        CommandTemplate("Volume Up", CommandCategory.VOLUME, essential=False),
        CommandTemplate("Volume Down", CommandCategory.VOLUME, essential=False),
        CommandTemplate("Mute", CommandCategory.VOLUME, essential=False),
    ],
    DeviceType.OTHER: [
        CommandTemplate("Power", CommandCategory.POWER, essential=True),
    ],
}


def get_templates_for_device_type(
    device_type: DeviceType | str,
) -> list[CommandTemplate]:
    """Return the templates for ``device_type``."""
    if isinstance(device_type, str):
        try:
            device_type = DeviceType(device_type)
        except ValueError:
            device_type = DeviceType.OTHER
    return list(COMMAND_TEMPLATES.get(device_type, []))
