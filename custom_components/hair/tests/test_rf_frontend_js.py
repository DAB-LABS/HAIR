"""RF hear round 1, the frontend: the rules behind what the panel draws.

The homepage's hardware rows (``ir-hardware-rows.ts``), the Sniffer's
Listen pill and its pickers (``ir-listen-state.ts``), and the SHOW chips
and carrier column (``sniffer-filter.ts``) are plain functions. This
module transpiles them with the repo's own TypeScript and runs them
under node, the way ``test_receiver_window_js.py`` does, against the
cases the design pages draw (``agent-exchange/rf-hear/design/``).

Skipped when the frontend toolchain is not installed (CI runs pytest
without node_modules); the source pins at the bottom run everywhere.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

NOW = "2026-11-06T20:00:00.000Z"

DRIVER = Path(__file__).parent / "fixtures" / "rf_frontend_driver.mjs"
BAND_CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "rf" / "band_cases.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("rffrontjs")
    subprocess.run(
        [
            str(TSC),
            "src/ir-hardware-rows.ts", "src/ir-listen-state.ts", "src/sniffer-filter.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    band_hz = [c["hz"] for c in BAND_CASES["cases"]]
    driver = (
        DRIVER.read_text(encoding="utf-8")
        .replace("__NOW__", NOW)
        .replace("__BAND_HZ__", json.dumps(band_hz))
    )
    (out / "driver.mjs").write_text(driver, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _src(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


class TestTheHardwareRows:
    """Design homepage-hardware-cards.html: one row per capability."""

    def test_the_rm4_pro_has_four_rows_in_order(self, run):
        assert [r[0] for r in run["rows"]] == ["IR-TX", "IR-RX", "RF-TX", "RF-RX"]
        assert [r[1] for r in run["rows"]] == [
            "infrared.wi_fi_universal_remote_ir_emitter",
            "infrared.rm4_pro_ir_receiver",
            "radio_frequency.wi_fi_universal_remote_rf_transmitter",
            "radio_frequency.rm4_pro_rf_receiver",
        ]

    def test_the_infrared_receiver_keeps_its_row_beside_the_radio_one(self, run):
        """The defect: the RF receiver, arriving last, took the IR one's slot."""
        ids = [r[1] for r in run["rows"]]
        assert "infrared.rm4_pro_ir_receiver" in ids
        assert "radio_frequency.rm4_pro_rf_receiver" in ids

    def test_the_facts_at_the_right(self, run):
        facts = {r[1]: r[3] for r in run["rows"]}
        assert facts["infrared.wi_fi_universal_remote_ir_emitter"]["kind"] == "sent"
        assert facts["radio_frequency.rm4_pro_rf_receiver"]["kind"] == "heard"
        # Nothing known since HAIR started: blank, never "never".
        assert facts["infrared.rm4_pro_ir_receiver"] == {"kind": "none"}
        assert facts["radio_frequency.wi_fi_universal_remote_rf_transmitter"] == {"kind": "none"}

    def test_the_dashed_rule_sits_between_the_media(self, run):
        assert run["rm4_break"] == 2
        assert run["blaster_break"] == -1

    def test_an_all_down_card_is_ember_and_says_unavailable(self, run):
        assert run["rm4_offline"] is False
        assert run["ember_offline"] is True
        assert run["ember_facts"] == ["unavailable"] * 4

    def test_the_sections_as_before(self, run):
        assert run["sections"] == {
            "emitters": ["dev-rm4", "dev-blaster"],
            "receivers": ["dev-rm4"],
            "proxies": ["dev-rm4"],
        }

    def test_what_is_never_a_row(self, run):
        ids = run["all_ids"]
        assert "infrared.hair_tweezer" not in ids  # HAIR's own observer
        assert "infrared.gh72_rf_proxy" not in ids  # a receiver not listed
        assert "light.kitchen" not in ids
        assert "dev-bridge" not in ids  # the event bridge left with 2026.6

    def test_a_remembered_capture_device_keeps_its_row(self, run):
        assert run["remembered"] == [["dev-garage", [["IR-RX", False]]]]

    def test_the_capture_device_flag_only_drives_the_icon(self, run):
        assert run["capture_flag"] == ["radio_frequency.rm4_pro_rf_receiver"]

    def test_the_ages(self, run):
        assert run["ago"] == [
            {"n": 5, "unit": "s"}, {"n": 59, "unit": "s"}, {"n": 1, "unit": "m"},
            {"n": 59, "unit": "m"}, {"n": 1, "unit": "h"}, {"n": 23, "unit": "h"},
            {"n": 3, "unit": "d"},
        ]
        assert run["ago_bad"] is None


class TestTheListenPill:
    """Design sniffer-listen-pills.html: five looks, plus waiting."""

    def test_the_looks(self, run):
        pill = run["pill"]
        assert pill["idle"] == "idle"
        assert pill["open"] == "open"
        assert pill["sweep"] == "sweep"
        assert pill["locked"] == "open"
        assert pill["hearing"] == "hearing"
        assert pill["software_open"] == "open"
        assert pill["offline"] == "offline"
        assert pill["waiting"] == "waiting"

    def test_a_software_window_reads_the_subscription_never_hass(self, run):
        assert run["pill"]["software_closed_by_item"] == "hearing"
        assert run["pill"]["software_ignores_hass"] == "hearing"

    def test_the_badge(self, run):
        # Every pill is a receiver: the badge is the medium alone (fix
        # round 1, item 7). The homepage rows keep IR-TX / RF-RX.
        assert (run["pill"]["ir_badge"], run["pill"]["rf_badge"]) == ("IR", "RF")

    def test_an_always_on_infrared_receiver_is_a_status_pill(self, run):
        assert run["pill"]["status"] == "status"
        assert run["pressable"] == {
            "idle": True, "hearing": True, "status": False, "open": True,
            "sweep": True, "offline": False, "waiting": False,
        }

    def test_the_pickers_are_inactive_while_open_or_down(self, run):
        assert run["active"] == {
            "idle": True, "hearing": True, "waiting": True,
            "open": False, "sweep": False, "offline": False,
        }


class TestThePickers:
    def test_lengths_stay_inside_the_declared_number(self, run):
        p = run["pickers"]
        assert p["bs_lengths"] == [10, 30, 60]  # BroadSniff 0.3.0: 1 to 60 s
        assert p["bs_lengths_300"] == [10, 30, 60, 120, 300]  # 0.3.1: up to 300 s
        assert p["sw_lengths"] == [10, 30, 60, 120, 300]
        assert p["undeclared_lengths"] == []
        assert (p["bs_length"], p["sw_length"]) == (10, 120)

    def test_modes_in_the_pickers_order(self, run):
        p = run["pickers"]
        assert p["bs_modes"] == ["single", "sliding", "multiple"]
        assert p["sw_modes"] == ["single", "sliding", "multiple"]
        assert (p["bs_mode"], p["sw_mode"]) == ("sliding", "single")

    def test_frequency_only_from_the_map_and_only_with_two_or_more(self, run):
        p = run["pickers"]
        assert p["freqs"] == ["mhz_433_92", "mhz_315", "sweep"]
        assert p["fixed_band"] == []
        assert p["no_select"] == []

    def test_what_the_frequency_picker_reads(self, run):
        p = run["pickers"]
        assert p["freq_433"] == {"hz": 433920000, "sweep": False}
        assert p["freq_sweep"] == {"hz": None, "sweep": True}
        # After a sweep locks, the band found.
        assert p["freq_found"] == {"hz": 433920000, "sweep": False}
        # An option not in the map (custom) shows the carrier, not offered.
        assert p["freq_custom"] == {"hz": 303900000, "sweep": False}

    def test_bands(self, run):
        assert run["pickers"]["bands"] == ["433.92", "315", "433.42", "868.3"]


class TestTheShowChips:
    def test_each_glyph_is_its_own_toggle(self, run):
        # Remotes: infrared, radio, a hidden infrared one, one with no
        # medium. Hidden adds the hidden remotes of the lit media; the
        # list can be reordered only with the defaults.
        assert run["shows"] == {
            "default": {"rows": [True, True, False, True], "everything": True},
            "ir_only": {"rows": [True, False, False, True], "everything": False},
            "rf_only": {"rows": [False, True, False, False], "everything": False},
            "with_hidden": {"rows": [True, True, True, True], "everything": False},
            "rf_and_hidden": {"rows": [False, True, False, False], "everything": False},
            "none": {"rows": [False, False, False, False], "everything": False},
        }

    def test_the_carrier_column(self, run):
        assert run["carriers"] == [
            {"band": "433.92"}, None, {"khz": 38}, None, {"band": "433.92"},
        ]

    def test_the_band_rule_is_the_backends(self, run):
        """Item 8: the panel's bands are rf_band.py's, case for case."""
        assert run["band_cases"] == BAND_CASES["cases"]


class TestTheSources:
    """Pins that run without node."""

    def test_the_hidden_chip_replaces_the_bottom_button(self):
        monitor = _src("ir-signal-monitor.ts")
        assert "_toggleDismissed" not in monitor and "_showDismissed" not in monitor
        assert "include_dismissed: this._show.hidden," in monitor
        assert '${g.kind === "hidden" && this._hiddenDot' in monitor
        assert 'class="show-glyph ${this._show[g.kind] ? "on" : ""}' in monitor

    def test_reordering_only_with_every_remote_shown(self):
        monitor = _src("ir-signal-monitor.ts")
        assert (
            'this._remotesSortable?.option("disabled", !snifferShowsEverything(this._show));'
        ) in monitor
        assert 'handle: ".remote-handle",' in monitor

    def test_the_handle_is_a_button_with_the_glyph_then_the_grip(self):
        monitor = " ".join(_src("ir-signal-monitor.ts").split())
        assert '<button class="remote-handle"' in monitor
        assert 'renderProtoGlyph(d.medium ?? "ir", 18, remoteBand(d))' in monitor
        assert re.search(r"@media \(prefers-reduced-motion: reduce\) \{ \.remote-handle", monitor)

    def test_glyphs_only_where_the_ruling_puts_them(self):
        for name in ("ir-device-list.ts", "ir-signal-monitor.ts"):
            assert "renderProtoGlyph(" in _src(name), name
        for name in ("ir-listen-chip.ts", "ir-clips.ts", "ir-pluck.ts", "ir-hardware-rows.ts"):
            assert "renderProtoGlyph" not in _src(name), name
        glyph = _src("ir-proto-glyph.ts")
        assert 'PROTO_SOURCE = "#8b8f96"' in glyph and 'PROTO_SIGNAL = "#03a9f4"' in glyph
        assert "primary-color" not in glyph

    def test_hardware_cards_are_wider_than_device_cards(self):
        """A row holds a badge, a name and a fact; at the device cards'
        200px the name collapsed to its first letter (the 1280 render)."""
        devlist = _src("ir-device-list.ts")
        assert '<div class="grid hw-grid">' in devlist
        grid = "grid-template-columns: repeat(auto-fill, minmax(min(320px, 100%), 1fr));"
        assert grid in devlist

    def test_the_radio_refusals_are_said(self):
        errors = _src("rf-errors.ts")
        assert 'RF_SEND_UNSUPPORTED = "rf_send_unsupported"' in errors
        assert 'RF_EDIT_UNSUPPORTED = "rf_edit_unsupported"' in errors
        for name in ("ir-signal-editor.ts", "ir-device-detail.ts", "ir-signal-monitor.ts"):
            assert "rfRefusal(" in _src(name), name

    def test_the_server_codes_match(self):
        from custom_components.hair.const import RF_EDIT_UNSUPPORTED, RF_SEND_UNSUPPORTED

        errors = _src("rf-errors.ts")
        assert f'"{RF_SEND_UNSUPPORTED}"' in errors and f'"{RF_EDIT_UNSUPPORTED}"' in errors

    def test_the_locales_say_it_in_every_language(self):
        keys = (
            "hw.sent", "hw.heard", "listen.hearing", "listen.hold_button",
            "sniffer.filter.radio", "errors.rf_send_unsupported", "proto.unknown",
        )
        for path in (SRC / "locales").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in keys:
                assert key in data, (path.name, key)
