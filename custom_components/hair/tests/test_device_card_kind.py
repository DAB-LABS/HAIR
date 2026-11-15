"""A device card of type Other names its kind of hardware (owner, 2026-11-14).

The card said "IR Device" for every device of type Other, a radio one
too. It now says "Radio Device" when the device's codes are all radio,
"IR Device" when they are all infrared, and "Device" when it holds both
kinds or no codes yet. The other types and the dialogs' "Other" are
unchanged, and a Remote is never of type Other. Pinned in the source, the house style for
panel wiring; ``soleKind`` itself runs under node in
``test_picker_kinds.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

COMPONENT = Path(__file__).parent.parent
SRC = COMPONENT / "frontend" / "src"
LOCALES = SRC / "locales"
KEYS = ("device_type.other_card_radio", "device_type.other_card_both")


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


def _locale(lang: str) -> dict[str, str]:
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


class TestTheCard:
    def test_other_takes_the_kind(self):
        flat = _flat("ir-device-list.ts")
        rule = flat.split("function deviceCardTypeKey(", 1)[1].split("/**", 1)[0]
        assert 'if (type !== "other") return DEVICE_TYPE_LABEL_KEYS[type];' in rule
        assert "const kind = soleKind(media);" in rule
        assert 'if (kind === "rf") return "device_type.other_card_radio";' in rule
        assert 'if (kind === "ir") return "device_type.other_card";' in rule
        assert 'return "device_type.other_card_both";' in rule

    def test_the_device_card_uses_it(self):
        flat = _flat("ir-device-list.ts")
        assert flat.count("deviceCardTypeKey(") == 2
        assert "t(deviceCardTypeKey(device.device_type, device.media))," in flat
        assert "t(DEVICE_TYPE_LABEL_KEYS[device.device_type])" not in flat

    def test_a_remote_is_never_of_type_other(self):
        # So the Remote card and the Remote-type message keep the plain
        # labels: the server refuses Other for a Remote.
        from custom_components.hair.const import DeviceType
        from custom_components.hair.remote_state import REMOTE_TYPES

        assert DeviceType.OTHER not in REMOTE_TYPES
        types = " ".join((SRC / "types.ts").read_text(encoding="utf-8").split())
        remote_types = types.split("export type RemoteTypeId =", 1)[1].split(";", 1)[0]
        assert '"other"' not in remote_types
        flat = _flat("ir-device-list.ts")
        assert "t(DEVICE_TYPE_LABEL_KEYS[remote.device_type])" in flat


class TestTheWords:
    def test_the_english(self):
        en = _locale("en")
        assert en["device_type.other_card"] == "IR Device"
        assert en["device_type.other_card_radio"] == "Radio Device"
        assert en["device_type.other_card_both"] == "Device"
        assert en["device_type.other"] == "Other"

    def test_every_language_has_its_own(self):
        langs = sorted(p.stem for p in LOCALES.glob("*.json") if p.stem != "xx")
        assert len(langs) == 11
        en = _locale("en")
        for lang in langs:
            d = _locale(lang)
            for key in KEYS:
                assert d.get(key), (lang, key)
                if lang != "en":
                    assert d[key] != en[key], (lang, key)
            # Three different words on the card in every language.
            words = {d["device_type.other_card"], *(d[k] for k in KEYS)}
            assert len(words) == 3, lang
