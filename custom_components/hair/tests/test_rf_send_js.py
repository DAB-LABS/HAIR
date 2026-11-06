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
            str(TSC), "src/emitter-options.ts",
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
    return json.loads(result.stdout)


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
