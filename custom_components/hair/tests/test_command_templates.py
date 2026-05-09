"""Tests for the command templates module."""
from __future__ import annotations

from custom_components.hair.command_templates import (
    COMMAND_TEMPLATES,
    get_templates_for_device_type,
)
from custom_components.hair.const import CommandCategory, DeviceType


def test_tv_templates_have_essentials():
    templates = get_templates_for_device_type(DeviceType.TV)
    essential_names = {t.name for t in templates if t.essential}
    assert {"Power", "Volume Up", "Volume Down", "Mute"} <= essential_names


def test_unknown_device_type_falls_back_to_other():
    templates = get_templates_for_device_type("not-real")
    assert templates == COMMAND_TEMPLATES[DeviceType.OTHER]


def test_string_input_resolves_to_enum():
    templates = get_templates_for_device_type("ac")
    names = [t.name for t in templates]
    assert "Power On" in names
    assert "Mode: Cool" in names


def test_categories_are_valid_enums():
    for templates in COMMAND_TEMPLATES.values():
        for template in templates:
            assert isinstance(template.category, CommandCategory)
