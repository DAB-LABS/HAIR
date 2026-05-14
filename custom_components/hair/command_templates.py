"""Command templates and action options per device type.

Templates are surfaced in the admin panel as dropdown options so users
know what to capture. Action options define the canonical action keys
that entity platforms use to determine which features to expose.
"""
from __future__ import annotations

from .const import CommandCategory, DeviceType
from .models import CommandTemplate

COMMAND_TEMPLATES: dict[DeviceType, list[CommandTemplate]] = {
    DeviceType.MEDIA_PLAYER: [
        CommandTemplate("Power On", CommandCategory.POWER, essential=True),
        CommandTemplate("Power Off", CommandCategory.POWER, essential=True),
        CommandTemplate("Volume Up", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Volume Down", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Mute", CommandCategory.VOLUME, essential=True),
        CommandTemplate("Source/Input", CommandCategory.NAVIGATION, essential=True),
        CommandTemplate("Channel Up", CommandCategory.CHANNEL, essential=False),
        CommandTemplate("Channel Down", CommandCategory.CHANNEL, essential=False),
        CommandTemplate("Up", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Down", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Left", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Right", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Select/OK", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Back/Return", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Guide", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Menu", CommandCategory.NAVIGATION, essential=False),
        CommandTemplate("Play", CommandCategory.MEDIA_CONTROL, essential=False),
        CommandTemplate("Pause", CommandCategory.MEDIA_CONTROL, essential=False),
        CommandTemplate("Stop", CommandCategory.MEDIA_CONTROL, essential=False),
        CommandTemplate("Rewind", CommandCategory.MEDIA_CONTROL, essential=False),
        CommandTemplate("Fast Forward", CommandCategory.MEDIA_CONTROL, essential=False),
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
    DeviceType.LIGHT: [
        CommandTemplate("On", CommandCategory.POWER, essential=True),
        CommandTemplate("Off", CommandCategory.POWER, essential=True),
        CommandTemplate("Brightness Up", CommandCategory.BRIGHTNESS, essential=False),
        CommandTemplate("Brightness Down", CommandCategory.BRIGHTNESS, essential=False),
    ],
    DeviceType.SWITCH: [
        CommandTemplate("On", CommandCategory.POWER, essential=True),
        CommandTemplate("Off", CommandCategory.POWER, essential=True),
    ],
    DeviceType.SCREEN: [
        CommandTemplate("Open", CommandCategory.COVER, essential=True),
        CommandTemplate("Close", CommandCategory.COVER, essential=True),
        CommandTemplate("Stop", CommandCategory.COVER, essential=False),
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


# ---------------------------------------------------------------------------
# Action options: canonical action keys per device type
# ---------------------------------------------------------------------------
# Each entry is (action_key, human_label). The action_key is stored in
# EntityConfig.command_mapping and read by entity platforms to determine
# which HA features to expose.

ACTION_OPTIONS: dict[DeviceType, list[tuple[str, str]]] = {
    DeviceType.MEDIA_PLAYER: [
        ("turn_on", "Power On"),
        ("turn_off", "Power Off"),
        ("power_toggle", "Power Toggle"),
        ("volume_up", "Volume Up"),
        ("volume_down", "Volume Down"),
        ("mute", "Mute"),
        ("select_source", "Source/Input"),
        ("channel_up", "Channel Up"),
        ("channel_down", "Channel Down"),
        ("navigate_up", "Up"),
        ("navigate_down", "Down"),
        ("navigate_left", "Left"),
        ("navigate_right", "Right"),
        ("navigate_select", "Select/OK"),
        ("navigate_back", "Back/Return"),
        ("guide", "Guide"),
        ("menu", "Menu"),
        ("play", "Play"),
        ("pause", "Pause"),
        ("stop", "Stop"),
        ("rewind", "Rewind"),
        ("fast_forward", "Fast Forward"),
    ],
    DeviceType.AC: [
        ("turn_on", "Power On"),
        ("turn_off", "Power Off"),
        ("mode_cool", "Mode: Cool"),
        ("mode_heat", "Mode: Heat"),
        ("mode_fan_only", "Mode: Fan"),
        ("mode_dry", "Mode: Dry"),
        ("mode_auto", "Mode: Auto"),
        ("fan_low", "Fan: Low"),
        ("fan_medium", "Fan: Medium"),
        ("fan_high", "Fan: High"),
        ("fan_auto", "Fan: Auto"),
        ("swing_toggle", "Swing Toggle"),
    ],
    DeviceType.FAN: [
        ("turn_on", "Power"),
        ("turn_off", "Power Off"),
        ("power_toggle", "Power Toggle"),
        ("speed_up", "Speed Up"),
        ("speed_down", "Speed Down"),
        ("oscillate", "Oscillate"),
    ],
    DeviceType.LIGHT: [
        ("turn_on", "On"),
        ("turn_off", "Off"),
        ("brightness_up", "Brightness Up"),
        ("brightness_down", "Brightness Down"),
    ],
    DeviceType.SWITCH: [
        ("turn_on", "On"),
        ("turn_off", "Off"),
    ],
    DeviceType.SCREEN: [
        ("open_cover", "Open"),
        ("close_cover", "Close"),
        ("stop_cover", "Stop"),
    ],
    DeviceType.OTHER: [],
}


def get_action_options(
    device_type: DeviceType | str,
) -> list[dict[str, str]]:
    """Return the action options for a device type as dicts."""
    if isinstance(device_type, str):
        try:
            device_type = DeviceType(device_type)
        except ValueError:
            return []
    return [
        {"key": key, "label": label}
        for key, label in ACTION_OPTIONS.get(device_type, [])
    ]
