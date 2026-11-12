"""N15, N19 and N20 in the panel (Sniffer follow-ups, 2026-11-11).

- N15: a radio hit carries its row's carrier, and the Sniffer updates
  the row's band cell, and the remote's band, in place.
- N19: a device command's refused send names the code, its medium and
  the device.
- N20: under a radio code's send count, the Assign dialog and the radio
  editor say what the count starts at and why.

The rules run under node with the repo's TypeScript and a stub
localizer (skipped without the toolchain); the source and locale pins
run everywhere.
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
LOCALES = SRC / "locales"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

LOCALIZE_STUB = """
export function t(key, params) {
    return JSON.stringify(params ? [key, params] : [key]);
}
"""

DRIVER = r"""
import { deviceRefusal, deviceRefusalKey } from "./rf-errors.js";
import { sendTimesHint } from "./rf-send-count.js";

const err = (code) => ({ code });
const plug = { device: "Bench Plug", command: "Power" };

console.log(JSON.stringify({
    refusal: {
        radio: deviceRefusalKey(err("no_emitter_for_medium"), { ...plug, medium: "rf" }),
        infrared: deviceRefusalKey(err("no_emitter_for_medium"), { ...plug, medium: "ir" }),
        noMedium: deviceRefusalKey(err("no_emitter_for_medium"), plug),
        noNames: deviceRefusalKey(err("no_emitter_for_medium"), { medium: "rf" }),
        band: deviceRefusalKey(
            err("rf_frequency_unsupported"), { ...plug, medium: "rf", band: "315" },
        ),
        noBand: deviceRefusalKey(
            err("rf_frequency_unsupported"), { ...plug, medium: "rf", band: null },
        ),
        other: deviceRefusalKey(err("rf_no_frequency"), { ...plug, medium: "rf" }),
        notRefusal: deviceRefusalKey(new Error("boom"), plug),
        oneDown: deviceRefusalKey(
            {
                code: "rf_frequency_unsupported",
                message: "Bench Plug has no radio transmitter that is up and can send "
                    + "315 MHz (radio_frequency.rm4 unavailable)",
            },
            { ...plug, medium: "rf", band: "315" },
        ),
        yaml: deviceRefusalKey(
            {
                code: "rf_frequency_unsupported",
                message: "The radio transmitter on Bench Plug declares no frequency; "
                    + "add frequency: to its YAML",
            },
            { ...plug, medium: "rf", band: "433.92" },
        ),
        sentence: deviceRefusal(err("no_emitter_for_medium"), { ...plug, medium: "rf" }),
    },
    hint: {
        measured: sendTimesHint("rf", 6, 6),
        clampedHigh: sendTimesHint("rf", 40, 10),
        clampedLow: sendTimesHint("rf", 1, 2),
        unmeasured: sendTimesHint("rf", null, 4),
        zero: sendTimesHint("rf", 0, 4),
        storedOne: sendTimesHint("rf", 6, 1),
        chosen: sendTimesHint("rf", 6, 3),
        pasteField: sendTimesHint("rf", null, 1),
        infrared: sendTimesHint("ir", 6, 6),
        noMedium: sendTimesHint(undefined, 6, 6),
    },
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("snifferfollowupsjs")
    subprocess.run(
        [
            str(TSC), "src/rf-errors.ts", "src/rf-send-count.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--resolveJsonModule",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "localize.js").write_text(LOCALIZE_STUB, encoding="utf-8")
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


PLUG = {"command": "Power", "device": "Bench Plug"}


class TestN19TheRefusal:
    def test_a_radio_code_with_no_radio_transmitter(self, run):
        assert run["refusal"]["radio"] == {"key": "errors.no_radio_transmitter", "params": PLUG}

    def test_an_infrared_code_with_no_infrared_emitter(self, run):
        assert run["refusal"]["infrared"] == {"key": "errors.no_infrared_emitter", "params": PLUG}
        assert run["refusal"]["noMedium"] == run["refusal"]["infrared"]

    def test_no_transmitter_for_the_band(self, run):
        assert run["refusal"]["band"] == {
            "key": "errors.no_transmitter_for_band",
            "params": {"device": "Bench Plug", "band": "315"},
        }

    def test_without_names_or_band_the_general_sentence(self, run):
        assert run["refusal"]["noNames"] == {"key": "errors.no_emitter_for_medium"}
        assert run["refusal"]["noBand"] == {"key": "errors.rf_frequency_unsupported"}
        assert run["refusal"]["other"] == {"key": "errors.rf_no_frequency"}
        assert run["refusal"]["notRefusal"] is None

    def test_no_band_sentence_when_it_would_not_be_true(self, run):
        # A transmitter that is down, or transmitters that declare no
        # frequency: the server's own message says which (review 5, 6).
        assert run["refusal"]["oneDown"] is None
        assert run["refusal"]["yaml"] is None

    def test_the_sentence_carries_the_names(self, run):
        assert json.loads(run["refusal"]["sentence"]) == ["errors.no_radio_transmitter", PLUG]

    def test_the_device_page_uses_it(self):
        flat = _flat("ir-device-detail.ts")
        assert (
            "deviceRefusal(err, { device: this.device.name, command: command.name, "
            'medium: command.medium ?? "ir", band: command.rf_frequency_hz ? '
            "bandLabel(command.rf_frequency_hz) : null, })"
        ) in flat
        assert "rfRefusal(err)" not in flat


class TestN20TheCountLine:
    def test_a_measured_press(self, run):
        assert run["hint"]["measured"] == {"key": "rfedit.send_times_measured", "count": 6}

    def test_a_clamped_count_is_not_what_the_remote_sent(self, run):
        assert run["hint"]["clampedHigh"] == {"key": "rfedit.send_times_usual", "count": 10}
        assert run["hint"]["clampedLow"] == {"key": "rfedit.send_times_usual", "count": 2}

    def test_no_line_unless_the_field_holds_the_seed(self, run):
        # A minted Sniffer row's stored 1, a count the user chose, a
        # paste's 1: the line would describe a number the field does not
        # show (review 1 to 3).
        assert run["hint"]["storedOne"] is None
        assert run["hint"]["chosen"] is None
        assert run["hint"]["pasteField"] is None

    def test_an_unmeasured_press(self, run):
        assert run["hint"]["unmeasured"] == {"key": "rfedit.send_times_usual", "count": 4}
        assert run["hint"]["zero"] == run["hint"]["unmeasured"]

    def test_infrared_keeps_its_sentence(self, run):
        assert run["hint"]["infrared"] is None
        assert run["hint"]["noMedium"] is None

    def test_the_assign_dialog(self):
        flat = _flat("ir-assign-signal-dialog.ts")
        assert '<div class="hint">${this._sendTimesHint()}</div>' in flat
        assert (
            'const hint = sendTimesHint("rf", this.signal.rf_repeats_observed, this._sendCount);'
        ) in flat
        assert 'if (this.signal?.medium !== "rf") return t("assign.send_times_hint");' in flat

    def test_the_radio_editor(self):
        flat = _flat("ir-rf-editor.ts")
        assert (
            "@property({ attribute: false }) public repeatsObserved: number | null = null;"
        ) in flat
        assert 'const hint = sendTimesHint("rf", this.repeatsObserved, this._sendCount);' in flat
        assert "/> ${this._countHint()} </div>" in flat

    @pytest.mark.parametrize(
        ("name", "expr"),
        [
            ("ir-clips.ts", "assignSendCount(this._editSignal.signal)"),
            ("ir-signal-monitor.ts", "assignSendCount(this._editSignal.signal)"),
            ("ir-mirror.ts", "assignSendCount(this._editSignal)"),
            ("ir-device-detail.ts", "this._editCommand.send_count ?? 1"),
        ],
    )
    def test_the_editor_starts_where_the_assign_dialog_does(self, name, expr):
        # A captured row's stored 1 starts at what the press carried, as
        # in the Assign dialog, so the count line shows (owner,
        # 2026-11-12). A device's command keeps the count it was saved
        # with.
        text = (SRC / name).read_text(encoding="utf-8")
        starts = [
            m.group(1)
            for m in re.finditer(r"\.initialSendCount=\$\{([^}]*\)?[^}]*)\}", text)
            if text.rfind("<ir-", 0, m.start()) == text.rfind("<ir-rf-editor", 0, m.start())
        ]
        assert starts and set(starts) == {expr}

    @pytest.mark.parametrize(
        ("name", "count"),
        [
            ("ir-clips.ts", 1),
            ("ir-device-detail.ts", 1),
            ("ir-signal-monitor.ts", 1),
            ("ir-mirror.ts", 1),
        ],
    )
    def test_every_editor_host_passes_the_repeats(self, name, count):
        text = (SRC / name).read_text(encoding="utf-8")
        editors = text.count("<ir-rf-editor")
        passes = len(re.findall(
            r"\.repeatsObserved=\$\{this\._edit\w+(\.signal)?\.rf_repeats_observed \?\? null\}",
            text,
        ))
        assert passes == count
        # Every radio editor that edits a stored code gets them; the
        # Clipper's create editor (a paste) has none, and no other
        # element is handed them.
        assert passes == editors - (1 if name == "ir-clips.ts" else 0)
        # Each binding sits on a radio editor, not the infrared one.
        for at in [m.start() for m in re.finditer(r"\.repeatsObserved=", text)]:
            assert text.rfind("<ir-", 0, at) == text.rfind("<ir-rf-editor", 0, at)


class TestN15TheBandCell:
    def test_the_row_takes_the_hits_carrier(self):
        flat = _flat("ir-signal-monitor.ts")
        assert (
            'if (ev.medium === "rf" && ev.rf_frequency_hz !== undefined) { '
            "updatedSig.rf_frequency_hz = ev.rf_frequency_hz; "
            "updatedSig.rf_frequency_source = ev.rf_frequency_source ?? null; }"
        ) in flat

    def test_the_remote_takes_it_only_when_there_is_one(self):
        flat = _flat("ir-signal-monitor.ts")
        assert (
            'if (ev.medium === "rf" && typeof ev.rf_frequency_hz === "number") { '
            "updated.rf_frequency_hz = ev.rf_frequency_hz; }"
        ) in flat


KEYS = {
    "errors.no_radio_transmitter": ("{command}", "{device}"),
    "errors.no_infrared_emitter": ("{command}", "{device}"),
    "errors.no_transmitter_for_band": ("{device}", "{band}"),
    "rfedit.send_times_measured": ("{count}",),
    "rfedit.send_times_usual": ("{count}",),
}


class TestTheSentences:
    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["errors.no_radio_transmitter"] == (
            "{command} is a radio code and {device} has no radio transmitter. "
            "Add one in the device's settings."
        )
        assert en["errors.no_infrared_emitter"] == (
            "{command} is an infrared code and {device} has no infrared emitter. "
            "Add one in the device's settings."
        )
        assert en["errors.no_transmitter_for_band"] == (
            "{device} has no radio transmitter that can send {band} MHz."
        )
        assert en["rfedit.send_times_measured"] == (
            "{count}, as the remote sent it when captured. Change it if the device needs more."
        )
        assert en["rfedit.send_times_usual"] == (
            "{count}, a usual count for a remote like this. Change it if the device needs more."
        )

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_locale_has_them_with_their_values(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, slots in KEYS.items():
            assert data.get(key), key
            for slot in slots:
                assert slot in data[key], (key, slot)
            assert "—" not in data[key], key
