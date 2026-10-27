"""Auto-map knows the button names other code sets give the same buttons.

Imported code sets name their buttons their own way: one family writes
"Power Toggle", "Direction Up" and "Select", another (in capitals,
title-cased on import) "Cursor Up" and "Menu Main". Each name below maps
to an action key HAIR already has; a name that could mean more than one
button is left out. Every name that mapped before maps the same way.
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.hair.command_templates import ACTION_OPTIONS
from custom_components.hair.const import DeviceType
from custom_components.hair.device_manager import (
    AUTO_MAP_RULES,
    DeviceManager,
    auto_map_feature,
)
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.remote_state import FILL_NAMES, plan_fill
from custom_components.hair.vocabulary import _build, localized_auto_map
from custom_components.hair.wig_adapters import convert

from .test_remote_state import _remote, _trigger

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"

# The table before this round, verbatim. Every entry must still map the
# same way.
PINNED_BEFORE = {
    "power": "power_toggle",
    "power on": "turn_on",
    "power off": "turn_off",
    "volume up": "volume_up",
    "volume down": "volume_down",
    "mute": "mute",
    "channel up": "channel_up",
    "channel down": "channel_down",
    "source/input": "select_source",
    "source": "select_source",
    "input": "select_source",
    "up": "navigate_up",
    "down": "navigate_down",
    "left": "navigate_left",
    "right": "navigate_right",
    "select/ok": "navigate_select",
    "back/return": "navigate_back",
    "mode: cool": "mode_cool",
    "mode: heat": "mode_heat",
    "mode: fan": "mode_fan_only",
    "mode: dry": "mode_dry",
    "mode: auto": "mode_auto",
    "fan: low": "fan_low",
    "fan: medium": "fan_medium",
    "fan: high": "fan_high",
    "fan: auto": "fan_auto",
    "speed up": "speed_up",
    "speed down": "speed_down",
    "speed cycle": "speed_cycle",
    "speed 1": "speed_1",
    "speed 2": "speed_2",
    "speed 3": "speed_3",
    "speed 4": "speed_4",
    "speed 5": "speed_5",
    "speed 6": "speed_6",
    "speed 7": "speed_7",
    "speed 8": "speed_8",
    "speed 9": "speed_9",
    "speed 10": "speed_10",
    "oscillate": "oscillate",
    "swing toggle": "swing_toggle",
    "timer": "timer",
    "on": "turn_on",
    "off": "turn_off",
    "brightness up": "brightness_up",
    "brightness down": "brightness_down",
    "color temp warmer": "color_temp_warmer",
    "color temp cooler": "color_temp_cooler",
    "open": "open_cover",
    "close": "close_cover",
    "guide": "guide",
    "menu": "menu",
    "play": "play",
    "pause": "pause",
    "rewind": "rewind",
    "fast forward": "fast_forward",
}

NEW = {
    "power toggle": "power_toggle",
    "direction up": "navigate_up",
    "direction down": "navigate_down",
    "direction left": "navigate_left",
    "direction right": "navigate_right",
    "cursor up": "navigate_up",
    "cursor down": "navigate_down",
    "cursor left": "navigate_left",
    "cursor right": "navigate_right",
    "arrow up": "navigate_up",
    "arrow down": "navigate_down",
    "arrow left": "navigate_left",
    "arrow right": "navigate_right",
    "up arrow": "navigate_up",
    "down arrow": "navigate_down",
    "left arrow": "navigate_left",
    "right arrow": "navigate_right",
    "select": "navigate_select",
    "ok": "navigate_select",
    "cursor enter": "navigate_select",
    "back": "navigate_back",
    "return": "navigate_back",
    "menu main": "menu",
    "main menu": "menu",
    "epg": "guide",
    "input next": "select_source",
    "mute toggle": "mute",
    "vol up": "volume_up",
    "vol down": "volume_down",
    "volume +": "volume_up",
    "volume -": "volume_down",
    "stop": "stop",
    "fan speed up": "speed_up",
    "fan speed down": "speed_down",
    "oscillation": "oscillate",
}

# Considered and left out: no key, or more than one button.
LEFT_OUT = [
    "exit", "enter", "home", "setup", "info", "channel prev",
    "previous channel", "input hdmi 1", "input tv", "input select",
    "standby", "play/pause", "forward", "reverse", "skip", "fan speed",
    "fan", "speed", "swing", "rotate", "dimmer", "dim", "bright", "light",
    "open/close", "eject", "sleep", "arrow enter", "digit 1", "1",
]

ALL_TYPES = [
    DeviceType.MEDIA_PLAYER, DeviceType.AC, DeviceType.FAN,
    DeviceType.LIGHT, DeviceType.SWITCH, DeviceType.SCREEN, DeviceType.OTHER,
]


def _types_offering(key: str) -> list[DeviceType]:
    return [t for t in ALL_TYPES if key in {k for k, _ in ACTION_OPTIONS[t]}]


def _map(device_type, names):
    """A Device of this type gets these commands, each auto-mapped."""
    device = IRDevice(name="Test", device_type=device_type)
    manager = DeviceManager.__new__(DeviceManager)
    for name in names:
        command = IRCommand(name=name)
        device.add_command(command)
        manager._auto_map_command(device, command)
    return device.entity_config.command_mapping


class TestTable:
    def test_existing_entries_are_unchanged(self):
        for name, key in PINNED_BEFORE.items():
            assert AUTO_MAP_RULES[name] == key, name

    def test_the_table_is_exactly_the_old_one_plus_the_new_names(self):
        assert AUTO_MAP_RULES == {**PINNED_BEFORE, **NEW}
        assert not set(NEW) & set(PINNED_BEFORE)

    def test_every_new_key_is_an_action_some_type_offers(self):
        for name, key in NEW.items():
            assert _types_offering(key), (name, key)

    def test_names_are_casefolded(self):
        for name in NEW:
            assert name == name.casefold()


class TestNewNames:
    @pytest.mark.parametrize("name,key", sorted(NEW.items()))
    def test_maps_on_every_type_that_offers_the_key(self, name, key):
        for device_type in _types_offering(key):
            for spelling in (name, name.title(), name.upper()):
                assert auto_map_feature(spelling, device_type) == key
                assert _map(device_type, [spelling]) == {key: spelling}

    @pytest.mark.parametrize("name", LEFT_OUT)
    def test_left_out_names_stay_unmapped(self, name):
        for device_type in ALL_TYPES:
            assert auto_map_feature(name, device_type) is None, name

    def test_a_bare_speed_stays_unmapped(self):
        assert auto_map_feature("Speed", DeviceType.FAN) is None
        assert auto_map_feature("Fan Speed", DeviceType.FAN) is None


class TestBenchImports:
    """The three import fixtures, made into a Device the way Make HAIR
    Device does: each signal's alias becomes a command, auto-mapped."""

    def _mapped(self, fixture, device_type=DeviceType.MEDIA_PLAYER):
        result = convert((FIXTURES / fixture).read_text(), fixture)
        wigs = result.wigs or ([result.wig] if result.wig else [])
        assert len(wigs) == 1
        names = [signal.alias for signal in wigs[0].signals]
        return _map(device_type, names)

    def test_harmony(self):
        assert self._mapped("harmony_device_with_commands_fixture_audio_fa-2100.json") == {
            "power_toggle": "Power Toggle",
            "mute": "Mute",
            "volume_up": "Volume Up",
            "volume_down": "Volume Down",
        }

    def test_global_cache(self):
        assert self._mapped("globalcache_codeset.csv") == {
            "power_toggle": "Power",
            "volume_up": "Volume Up",
            "volume_down": "Volume Down",
            "mute": "Mute",
            "channel_up": "Channel Up",
            "channel_down": "Channel Down",
            "guide": "Guide",
            "menu": "Menu Main",
        }

    def test_tasmota(self):
        assert self._mapped("tasmota_codes.txt") == {
            "power_toggle": "Power",
            "volume_up": "Volume Up",
            "volume_down": "Volume Down",
            "mute": "Mute",
            "select_source": "Input",
            "menu": "Menu",
            "guide": "Guide",
        }


class TestTypedRemote:
    def test_the_fill_by_names_picks_up_new_names(self):
        triggers = [
            _trigger("t1", "Power Toggle"),
            _trigger("t2", "Stop"),
            _trigger("t3", "Vol Up"),
            _trigger("t4", "Direction Up"),
        ]
        store = MagicMock()
        store.get_triggers_for_remote = MagicMock(return_value=triggers)
        store.get_device = MagicMock(return_value=None)
        plan = plan_fill(store, _remote(None), DeviceType.MEDIA_PLAYER)
        assert plan.source == FILL_NAMES
        # Direction Up maps on a Device, but a Remote tracks only what
        # its entity can follow from presses alone.
        assert plan.mapping == {
            "power_toggle": "t1", "stop": "t2", "volume_up": "t3",
        }


class TestLocalizedTable:
    def test_no_collisions(self, caplog):
        caplog.set_level(logging.INFO, logger="custom_components.hair.vocabulary")
        table = _build(dict(AUTO_MAP_RULES))
        assert not [r for r in caplog.records if "collision" in r.getMessage()]
        # English always wins: no localized synonym points a new name
        # at a different key.
        for name, key in NEW.items():
            assert table.get(name, key) == key

    def test_translations_join_for_names_with_a_vocab_label(self):
        table = localized_auto_map(AUTO_MAP_RULES)
        assert table["ein/aus"] == "power_toggle"
        assert table["stopp"] == "stop"


class TestKnownGap:
    def test_a_screens_stop_maps_to_the_media_players_stop(self):
        """Pinned on purpose. One key per name: Stop is ``stop`` on a media
        player and ``stop_cover`` on a screen, so a screen's Stop lands on
        ``stop``, which its type does not offer and the cover does not
        read. A later round that maps only keys a type offers or its
        entity reads flips this test."""
        mapping = _map(DeviceType.SCREEN, ["Open", "Close", "Stop"])
        assert mapping == {
            "open_cover": "Open", "close_cover": "Close", "stop": "Stop",
        }
        offered = {k for k, _ in ACTION_OPTIONS[DeviceType.SCREEN]}
        assert set(mapping) - offered == {"stop"}
