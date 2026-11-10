"""N18, frontend: the receiver list names each receiver's medium, and a
trigger's list offers only its own.

An Athom's infrared and radio receivers share one device name, so the
picker's chips looked the same and the owner's radio "Doorbell" trigger
was saved with the infrared one. Every receiver chip now shows "IR" or
"RF" beside its name, the trigger dialog lists only the trigger's medium
(any receiver stays the default), and a stored receiver of the other
medium is dropped when the dialog opens, so Save repairs it. Remotes keep
every receiver, labeled.

The rules run under node with the repo's TypeScript (skipped without the
toolchain); the source pins run everywhere.
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

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

DRIVER = r"""
import {
    keepMedium, receiverIdMedium, receiverMedium, receiversOf, triggerMedium,
} from "./receiver-medium.js";

const IR = "infrared.athom_rx";
const RF = "radio_frequency.office_athom_ir_rf_433mhz_rf_receiver";
const RM4 = "radio_frequency.rm4_pro_rf_receiver";
const all = [
    { entity_id: IR, name: "Athom", medium: "ir" },
    { entity_id: RF, name: "Athom", medium: "rf" },
    { entity_id: RM4, name: "RM4 Pro" },
    { entity_id: "infrared.den", name: "Den" },
];
const ids = (rs) => rs.map((r) => r.entity_id);

console.log(JSON.stringify({
    media: all.map(receiverMedium),
    idMedia: [IR, RF, "sensor.legacy_rx"].map(receiverIdMedium),
    rf: ids(receiversOf(all, "rf")),
    ir: ids(receiversOf(all, "ir")),
    any: ids(receiversOf(all, null)),
    trigger: [
        triggerMedium({ medium: "rf", protocol: "RF_RAW" }, null),
        triggerMedium({ protocol: "RF_RAW" }, null),
        triggerMedium({ protocol: "NEC" }, "RF_RAW"),
        triggerMedium(null, "RF_RAW"),
        triggerMedium(null, "NEC"),
        triggerMedium(null, null),
    ],
    keep: {
        doorbell: keepMedium([IR], "rf"),
        mixed: keepMedium([IR, RF, "sensor.legacy_rx"], "rf"),
        infrared: keepMedium([IR, RF], "ir"),
        unknown: keepMedium([IR, RF], null),
    },
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("rxmediumjs")
    subprocess.run(
        [
            str(TSC), "src/receiver-medium.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--resolveJsonModule",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


IR = "infrared.athom_rx"
RF = "radio_frequency.office_athom_ir_rf_433mhz_rf_receiver"
RM4 = "radio_frequency.rm4_pro_rf_receiver"


class TestTheRules:
    def test_a_receivers_medium_is_the_servers_word_else_its_domain(self, run):
        assert run["media"] == ["ir", "rf", "rf", "ir"]
        assert run["idMedia"] == ["ir", "rf", None]

    def test_a_list_of_one_medium_and_of_any(self, run):
        assert run["rf"] == [RF, RM4]
        assert run["ir"] == [IR, "infrared.den"]
        assert run["any"] == [IR, RF, RM4, "infrared.den"]

    def test_a_triggers_medium(self, run):
        # Editing reads the trigger; creating reads the protocol, and a
        # create door with no protocol yet lists every receiver.
        assert run["trigger"] == ["rf", "rf", "ir", "rf", "ir", None]

    def test_a_stored_scope_keeps_its_own_medium(self, run):
        assert run["keep"]["doorbell"] == []
        assert run["keep"]["mixed"] == [RF, "sensor.legacy_rx"]
        assert run["keep"]["infrared"] == [IR]
        assert run["keep"]["unknown"] == [IR, RF]


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


class TestThePicker:
    def test_it_lists_one_medium_when_asked(self):
        flat = _flat("ir-receiver-picker.ts")
        assert "@property({ attribute: false }) public medium: Medium | null = null;" in flat
        assert "return receiversOf(this._receivers, this.medium);" in flat
        assert "this._receivers.map(" not in flat
        assert "this._listed().map((r) => this._renderChip(r))" in flat

    def test_every_chip_names_its_medium(self):
        flat = _flat("ir-receiver-picker.ts")
        assert 'const medium = t(receiverMedium(r) === "rf" ? "proto.rf" : "proto.ir");' in flat
        name = '<span class="rx-name">${r.name}</span>'
        assert f'{name} <span class="rx-medium">${{medium}}</span>' in flat
        assert 'aria-label="${r.name} ${medium}, ${word}"' in flat


class TestTheDialog:
    def test_the_trigger_dialog_passes_its_medium(self):
        flat = _flat("ir-trigger-dialog.ts")
        picker = flat.split("<ir-receiver-picker", 1)[1].split("></ir-receiver-picker>", 1)[0]
        assert ".medium=${triggerMedium(this.trigger, this.protocol)}" in picker

    def test_opening_drops_the_other_mediums_receivers(self):
        flat = _flat("ir-trigger-dialog.ts")
        assert (
            "this._receiverIds = keepMedium( this.trigger.receiver_entity_ids ?? [], "
            "triggerMedium(this.trigger, null), );"
        ) in flat

    @pytest.mark.parametrize(
        "name",
        [
            "ir-add-trigger-remote-dialog.ts",
            "ir-duplicate-trigger-remote-dialog.ts",
            "ir-promote-remote-dialog.ts",
        ],
    )
    def test_remotes_keep_every_receiver(self, name):
        flat = _flat(name)
        if "<ir-receiver-picker" not in flat:
            pytest.skip(f"{name} has no receiver picker")
        picker = flat.split("<ir-receiver-picker", 1)[1].split("></ir-receiver-picker>", 1)[0]
        assert ".medium=" not in picker
