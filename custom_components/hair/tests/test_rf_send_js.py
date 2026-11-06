"""RF send round, frontend: the emitter picker by medium, Test by medium,
and the refusals said in a sentence.

The rules run under node, transpiled with the repo's TypeScript, as
``test_rf_frontend_js.py`` does; the wiring is pinned in the source.
Skipped where the frontend toolchain is not installed; the pins run
everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
DRIVER = Path(__file__).parent / "fixtures" / "rf_send_driver.mjs"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("rfsendjs")
    subprocess.run(
        [
            str(TSC), "src/emitter-options.ts", "src/rf-code.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER.read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    lines = result.stdout.strip().splitlines()
    out = json.loads(lines[0])
    for line in lines[1:]:
        out.update(json.loads(line))
    return out


def _src(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _flat(name: str) -> str:
    return " ".join(_src(name).split())


class TestTheEmitterOptions:
    def test_infrared_first_then_radio_transmitters(self, run):
        assert run["options"] == [
            ["infrared.living_room_blaster", "ir", True],
            ["radio_frequency.athom_rf_transmitter", "rf", True],
            ["radio_frequency.rm4_pro_rf_transmitter", "rf", False],
        ]

    def test_the_medium_is_the_domain(self, run):
        assert run["media"] == ["ir", "rf", None, None]

    def test_groups_by_what_the_target_takes(self, run):
        assert run["groups_all"] == [["ir", 1], ["rf", 2]]
        assert run["groups_rf"] == [["rf", 2]]
        assert run["groups_ir"] == [["ir", 1]]
        assert run["groups_none"] == []


class TestThePicker:
    def test_it_takes_media_and_a_frequency(self):
        picker = _src("ir-emitter-picker.ts")
        assert "public media: Medium[] | null = null;" in picker
        assert "public rfFrequencyHz: number | null = null;" in picker
        assert "this.api.rfTransmitters(asked)" in picker

    def test_a_transmitter_that_cannot_send_is_never_turned_on(self):
        picker = _flat("ir-emitter-picker.ts")
        assert "if (blocked && !this.value.includes(entityId)) return;" in picker
        assert 'aria-disabled=${blocked && !on ? "true" : "false"}' in picker
        assert (
            'if (fit.code === "no_ranges") return { blocked: true, '
            'note: t("picker.fit_no_ranges") };'
        ) in picker

    def test_both_kinds_split_into_two_groups(self):
        picker = _flat("ir-emitter-picker.ts")
        assert 't(group.medium === "rf" ? "picker.group_rf" : "picker.group_ir")' in picker
        assert 't("picker.both_label")' in picker


class TestTestByMedium:
    def test_the_dialog_defaults_to_infrared_and_drops_the_other_kind(self):
        dialog = _flat("ir-test-emitter-dialog.ts")
        assert 'public media: Medium[] = ["ir"];' in dialog
        assert "return medium !== null && this.media.includes(medium);" in dialog
        assert ".media=${this.media} .rfFrequencyHz=${this.rfFrequencyHz}" in dialog

    @pytest.mark.parametrize(("name", "media"), [
        ("ir-signal-monitor.ts", '.media=${[this._testDialog.signal.medium ?? "ir"]}'),
        ("ir-mirror.ts", '.media=${[this._testDialog.medium ?? "ir"]}'),
        ("ir-assign-signal-dialog.ts", '.media=${[this.signal?.medium ?? "ir"]}'),
    ])
    def test_the_callers_pass_the_rows_medium(self, name, media):
        assert media in _flat(name)

    def test_the_mirror_says_a_refusal(self):
        assert "sendRefusal(r.reason)" in _src("ir-mirror.ts")


class TestTheRefusals:
    def test_every_code_in_the_contract_has_a_sentence(self):
        errors = _src("rf-errors.ts")
        locale = json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))
        for code in ("no_emitter_for_medium", "rf_no_frequency", "rf_frequency_unsupported",
                     "rf_platform_not_loaded", "emitter_wrong_medium", "invalid_emitter"):
            assert f'"{code}"' in errors, code
            assert f"errors.{code}" in locale, code

    def test_the_server_uses_the_same_codes(self):
        from custom_components.hair import emitters

        errors = _src("rf-errors.ts")
        assert f'"{emitters.INVALID_EMITTER}"' in errors
        assert f'"{emitters.EMITTER_WRONG_MEDIUM}"' in errors


class TestTheRadioEditorRules:
    """T3: what the radio code editor shows and accepts."""

    def test_the_sub_text_is_the_servers_byte_for_byte(self, run):
        from custom_components.hair import rf_paste

        frame = [1282, -382, 458, -1221, 458, -1221, 1282]
        long = [500 if i % 2 == 0 else -500 for i in range(401)]
        assert run["t3"]["sub_with_gap"] == rf_paste.to_sub(frame, 433_920_000, 12_909)
        assert run["t3"]["sub_on_space"] == rf_paste.to_sub([*frame, -9000], 315_000_000, 12_909)
        assert run["t3"]["sub_no_freq"] == rf_paste.to_sub(frame, None, None)
        assert run["t3"]["sub_long"] == rf_paste.to_sub(long, 433_920_000, 9000)

    def test_the_frequency_field_reads_mhz(self, run):
        assert run["t3"]["mhz"] == [
            433_920_000, 433_920_000, 315_000_000, 303_875_000, None, None, None, None, None,
        ]
        assert run["t3"]["to_mhz"] == ["433.92", "315", "303.875", "433.42"]
        assert run["t3"]["preset"] == [433_920_000, 315_000_000, None, None]

    def test_every_source_and_refusal_has_a_sentence(self, run):
        locale = json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))
        assert run["t3"]["source"] == [
            "rfedit.source_signal", "rfedit.source_receiver", "rfedit.source_receiver",
            "rfedit.source_user", "rfedit.source_assumed", None, None,
        ]
        refusals = run["t3"]["refusal"]
        assert refusals[-2:] == [None, None]
        for key in [k for k in run["t3"]["source"] + refusals if k]:
            assert key in locale, key


class TestTheRadioEditor:
    def test_a_radio_row_opens_the_radio_editor(self):
        for name, guard in (
            ("ir-device-detail.ts", 'this._editCommand.medium === "rf"'),
            ("ir-signal-monitor.ts", 'this._editSignal.signal.medium === "rf"'),
            ("ir-mirror.ts", 'this._editSignal.medium === "rf"'),
        ):
            text = _flat(name)
            assert guard + " ? html`<ir-rf-editor" in text, name
            assert 'import "./ir-rf-editor.js";' in text, name

    def test_it_sends_the_code_only_when_it_changed(self):
        editor = _flat("ir-rf-editor.ts")
        assert "const rfCode = this._codeChanged ? this._code : undefined;" in editor
        assert "if (this._codeChanged && !this._validation?.ok) return false;" in editor
        assert "this.api.rfValidate(" in editor

    def test_a_paste_brings_its_frequency_unless_the_user_set_one(self):
        editor = _flat("ir-rf-editor.ts")
        assert "if (result.ok && result.frequency_hz && !this._frequencyChanged) {" in editor

    def test_it_fires_the_infrared_editors_events(self):
        editor = _src("ir-rf-editor.ts")
        assert 'this._fire("command-edited", result);' in editor
        assert 'this._fire("signal-edited", result);' in editor


class TestTheMirrorForRadio:
    """T4: the Mirror shows HAIR's radio sends and acts on them."""

    def test_a_radio_row_is_actionable_without_code_text(self):
        mirror = _flat("ir-mirror.ts")
        assert 'const actionable = !!sig.code || sig.medium === "rf";' in mirror
        # Edit follows the same rule as Assign, Test and Trigger.
        assert "${actionable ? renderEditBtn((e: Event) => {" in mirror

    def test_the_sniffer_edits_a_radio_row_too(self):
        sniffer = _flat("ir-signal-monitor.ts")
        assert '${sig.code || sig.medium === "rf" ? renderEditBtn(' in sniffer

    def test_each_row_wears_its_glyph_with_the_band(self):
        mirror = _flat("ir-mirror.ts")
        assert (
            'renderProtoGlyph( sig.medium ?? "ir", 16, sig.medium === "rf" && sig.rf_frequency_hz '
            "? bandLabel(sig.rf_frequency_hz) : null, )"
        ) in mirror

    def test_the_medium_chips_appear_only_with_a_radio_row(self):
        mirror = _flat("ir-mirror.ts")
        assert (
            '${rows.some((r) => r.sig.medium === "rf") ? (["ir", "rf"] as Medium[]).map('
        ) in mirror
        assert 'out = out.filter((r) => (r.sig.medium ?? "ir") === this._medium);' in mirror
        # Clicking the chip that is on shows both again.
        assert "@click=${() => (this._medium = this._medium === m ? null : m)}" in mirror

    def test_a_substituted_send_says_where_it_went(self):
        errors = _flat("rf-errors.ts")
        assert (
            "if (r.status === \"fulfilled\" && r.value.substituted && r.value.frequency_hz) {"
        ) in errors
        for name in ("ir-mirror.ts", "ir-signal-monitor.ts"):
            text = _flat(name)
            assert "const at = substitutedHz(results);" in text, name
            assert 't("mirror.sent_at", { band: bandNumber(at) })' in text, name
        locale = json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))
        assert locale["mirror.sent_at"] == "Sent at {band} MHz"

    def test_the_mirror_words_name_radio_in_every_language(self):
        locales = {
            p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in (SRC / "locales").glob("*.json")
        }
        assert len(locales) == 11
        en = locales["en"]
        assert en["panel.tagline.mirror"] == (
            "See your live Home Assistant infrared and radio transmissions"
        )
        assert "infrared or radio frequency platforms" in en["mirror.empty_sub"]
        for lang, d in locales.items():
            for key in ("panel.tagline.mirror", "mirror.empty_sub"):
                assert "—" not in d[key], (lang, key)
