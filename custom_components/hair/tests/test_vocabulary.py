"""Tests for the localized auto-map synonyms table (vocabulary.py).

The table lets a command named with a localized template string ("the
user's data is the user's language") still hit assign-time auto-mapping.
English bridges vocab slugs to AUTO_MAP_RULES actions; every shipped
locale's rendering of a bridged slug joins the table.
"""
from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock

import pytest

from custom_components.hair import vocabulary
from custom_components.hair.const import DeviceType
from custom_components.hair.device_manager import (
    AUTO_MAP_RULES,
    DeviceManager,
)
from custom_components.hair.models import IRCommand, IRDevice


@pytest.fixture(autouse=True)
def _fresh_cache():
    vocabulary.reset_cache()
    yield
    vocabulary.reset_cache()


def _write_locales(tmp_path, files: dict[str, dict]) -> None:
    for stem, data in files.items():
        (tmp_path / f"{stem}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )


_EN = {
    "vocab.power_on": "Power On",
    "vocab.power_off": "Power Off",
    "vocab.on": "On",
    "panel.not_vocab": "ignored",
}


class TestTableBuild:
    def test_english_bridge(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        _write_locales(tmp_path, {"en": _EN})
        table = vocabulary.localized_auto_map(AUTO_MAP_RULES)
        assert table["power on"] == "turn_on"
        assert table["power off"] == "turn_off"
        assert "ignored" not in table

    def test_localized_names_join_table(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        _write_locales(
            tmp_path,
            {
                "en": _EN,
                "fr": {
                    "vocab.power_on": "Allumer",
                    "vocab.power_off": "Éteindre",
                    "vocab.on": "Marche",
                    "panel.not_vocab": "ignoré",
                },
            },
        )
        table = vocabulary.localized_auto_map(AUTO_MAP_RULES)
        assert table["allumer"] == "turn_on"
        assert table["éteindre"] == "turn_off"
        assert table["power on"] == "turn_on"

    def test_collision_keeps_first_and_logs(
        self, tmp_path, monkeypatch, caplog
    ):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        # zz renders "Power Off" with the same string en uses for
        # "Power On": one name, two actions. English wins (it sorts
        # first) and the collision is logged.
        _write_locales(
            tmp_path,
            {"en": _EN, "zz": {"vocab.power_off": "Power On"}},
        )
        with caplog.at_level(logging.INFO, logger=vocabulary.__name__):
            table = vocabulary.localized_auto_map(AUTO_MAP_RULES)
        assert table["power on"] == "turn_on"
        assert any("collision" in r.message.lower() for r in caplog.records)

    def test_missing_english_disables(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        _write_locales(tmp_path, {"fr": {"vocab.power_on": "Allumer"}})
        assert vocabulary.localized_auto_map(AUTO_MAP_RULES) == {}

    def test_unreadable_locale_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        _write_locales(tmp_path, {"en": _EN})
        (tmp_path / "zz.json").write_text("{not json", encoding="utf-8")
        table = vocabulary.localized_auto_map(AUTO_MAP_RULES)
        assert table["power on"] == "turn_on"

    def test_real_locales_build(self):
        """The shipped locale files produce a working table."""
        table = vocabulary.localized_auto_map(AUTO_MAP_RULES)
        assert table["power on"] == "turn_on"
        assert table["color temp warmer"] == "color_temp_warmer"


class TestAutoMapIntegration:
    def _manager(self) -> DeviceManager:
        return DeviceManager(MagicMock(), MagicMock(), MagicMock(), "entry")

    def test_localized_command_name_auto_maps(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        _write_locales(
            tmp_path,
            {"en": _EN, "fr": {"vocab.on": "Marche"}},
        )
        device = IRDevice(
            name="Lampe",
            emitter_entity_ids=["infrared.e"],
            device_type=DeviceType.LIGHT,
        )
        command = IRCommand(id="c1", name="Marche", protocol=None, code=None)
        self._manager()._auto_map_command(device, command)
        assert device.entity_config.command_mapping["turn_on"] == "Marche"

    def test_english_rules_still_first(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        _write_locales(tmp_path, {"en": _EN})
        device = IRDevice(
            name="Lamp",
            emitter_entity_ids=["infrared.e"],
            device_type=DeviceType.LIGHT,
        )
        command = IRCommand(id="c1", name="On", protocol=None, code=None)
        self._manager()._auto_map_command(device, command)
        assert device.entity_config.command_mapping["turn_on"] == "On"

    def test_unknown_name_stays_unmapped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vocabulary, "LOCALES_DIR", tmp_path)
        _write_locales(tmp_path, {"en": _EN})
        device = IRDevice(
            name="Lamp",
            emitter_entity_ids=["infrared.e"],
            device_type=DeviceType.LIGHT,
        )
        command = IRCommand(
            id="c1", name="Disco Mode", protocol=None, code=None
        )
        self._manager()._auto_map_command(device, command)
        assert not device.entity_config.command_mapping
