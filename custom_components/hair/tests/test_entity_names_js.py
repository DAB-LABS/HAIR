"""An emitter named once in the panel, actually executed.

The Mirror's labels are built server-side and went through
``entity_names.py`` in the mobile pass. The panel names emitters from
``hass.states`` on its own: the device header's Emitters chips, the
emitter picker in Add Device, Assign, Promote and Test emitter, and the
Devices tab's Emitters cards. All of them showed "KinCony AGv3 1 KinCony
AGv3 1 TX". ``entity-names.ts`` is the panel's twin of the Python rule,
and ``emitter-options.ts`` is the one place the picker and the header
build their emitter list.

So this transpiles ``emitter-options.ts`` (which pulls in
``entity-names.ts``) with the repo's own TypeScript and runs both under
node, in the house pattern of ``test_pluck_helpers_js.py``. Every
collapse case also goes through the Python rule, so the two cannot
drift. The surfaces themselves are lit components, which node cannot
render, so each is checked the house way: by reading its source for the
path it takes to the shared builder and for the tooltip keeping HA's
full name.

SKIPPED when the frontend toolchain is not installed, like its model.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from custom_components.hair.entity_names import collapse_doubled_device_name

FRONTEND = Path(__file__).parent.parent / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

toolchain = pytest.mark.skipif(
    not TSC.exists() or shutil.which("node") is None,
    reason="frontend toolchain not installed (node_modules / node)",
)

DOUBLED = "KinCony AGv3 1 KinCony AGv3 1 TX"
KIN = "infrared.kincony_agv3_1_kincony_agv3_1_tx"
BROADLINK = "infrared.broadlink_rm4_pro"

# The same table as test_entity_names.py, plus the non-string cases the
# panel can meet in a registry entry.
COLLAPSE_CASES = [
    (DOUBLED, "KinCony AGv3 1", "KinCony AGv3 1 TX"),
    (
        "Garage Workbench IR Puck Garage Workbench IR Puck TX",
        "Garage Workbench IR Puck",
        "Garage Workbench IR Puck TX",
    ),
    ("Den Den", "Den", "Den"),
    ("Den Den TX", "  Den  ", "Den TX"),
    ("KinCony AGv3 1 TX", "KinCony AGv3 1", "KinCony AGv3 1 TX"),
    ("Broadlink RM4 Pro", "Broadlink RM4 Pro", "Broadlink RM4 Pro"),
    ("Bora Bora Lamp", "Lamp", "Bora Bora Lamp"),
    ("Bora Bora Lamp IR", "Bora Bora Lamp", "Bora Bora Lamp IR"),
    ("Den Denon TX", "Den", "Den Denon TX"),
    ("Kitchen TX", None, "Kitchen TX"),
    ("Kitchen TX", "", "Kitchen TX"),
    ("Kitchen TX", "   ", "Kitchen TX"),
    ("", "Kitchen", ""),
    (None, "Kitchen", None),
]

DRIVER = """
import { readFileSync } from "node:fs";
import { collapseDoubledDeviceName, entityDisplayName, entityFullName }
    from "./entity-names.js";
import { getEmitterOptions } from "./emitter-options.js";

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const collapse = cases.map(([f, d]) => collapseDoubledDeviceName(f, d));

const KIN = "infrared.kincony_agv3_1_kincony_agv3_1_tx";
const hass = (over = {}) => ({
    states: {
        [KIN]: {
            entity_id: KIN,
            state: "2026-10-17T20:00:00+00:00",
            attributes: { friendly_name: "KinCony AGv3 1 KinCony AGv3 1 TX" },
        },
        "infrared.broadlink_rm4_pro": {
            entity_id: "infrared.broadlink_rm4_pro",
            state: "unavailable",
            attributes: { friendly_name: "Broadlink RM4 Pro" },
        },
        "infrared.no_name": {
            entity_id: "infrared.no_name",
            state: "unknown",
            attributes: {},
        },
        "infrared.rx_only": {
            entity_id: "infrared.rx_only",
            attributes: { friendly_name: "RX RX TX" },
        },
        "infrared.observer": {
            entity_id: "infrared.observer",
            attributes: { friendly_name: "Obs Obs TX", hair_observer: true },
        },
        "light.den": { entity_id: "light.den", attributes: { friendly_name: "Den Den" } },
    },
    entities: {
        [KIN]: { entity_id: KIN, device_id: "dev-kin" },
        "infrared.broadlink_rm4_pro": { device_id: "dev-bl" },
    },
    devices: {
        "dev-kin": { id: "dev-kin", name: "KinCony AGv3 1", name_by_user: null },
        "dev-bl": { id: "dev-bl", name: "Broadlink RM4 Pro", name_by_user: null },
    },
    ...over,
});

const h = hass();
const renamed = hass();
renamed.devices["dev-kin"] = { name: "Stale Name", name_by_user: "KinCony AGv3 1" };
const userNameMisses = hass();
userNameMisses.devices["dev-kin"] = { name: "KinCony AGv3 1", name_by_user: "Office Blaster" };
const noEntity = hass({ entities: {} });
const noDevice = hass({ devices: {} });
const noRegistries = hass({ entities: undefined, devices: undefined });

const out = {
    collapse,
    display: {
        plain: entityDisplayName(h, KIN),
        name_by_user: entityDisplayName(renamed, KIN),
        name_by_user_misses: entityDisplayName(userNameMisses, KIN),
        no_entity: entityDisplayName(noEntity, KIN),
        no_device: entityDisplayName(noDevice, KIN),
        no_registries: entityDisplayName(noRegistries, KIN),
        no_state: entityDisplayName(h, "infrared.gone"),
        no_hass: entityDisplayName(undefined, KIN),
        said_once: entityDisplayName(h, "infrared.broadlink_rm4_pro"),
        unnamed: entityDisplayName(h, "infrared.no_name"),
    },
    full: {
        kin: entityFullName(h, KIN),
        unnamed: entityFullName(h, "infrared.no_name"),
    },
    options: getEmitterOptions(h, new Set(["infrared.rx_only"])),
    optionsExcluding: getEmitterOptions(
        h, new Set(["infrared.rx_only"]), ["infrared.broadlink_rm4_pro"],
    ),
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("entitynamesjs")
    subprocess.run(
        [
            str(TSC), "src/emitter-options.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    cases = out / "cases.json"
    cases.write_text(
        json.dumps([[f, d] for f, d, _ in COLLAPSE_CASES]), encoding="utf-8"
    )
    result = subprocess.run(
        ["node", str(out / "driver.mjs"), str(cases)],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _flat(name: str) -> str:
    return " ".join(_read(name).split())


@toolchain
class TestTheRule:
    @pytest.mark.parametrize(
        "index,case", list(enumerate(COLLAPSE_CASES)), ids=lambda v: repr(v)
    )
    def test_collapse_matches_the_table(self, run, index, case):
        assert run["collapse"][index] == case[2]

    @pytest.mark.parametrize(
        "index,case", list(enumerate(COLLAPSE_CASES)), ids=lambda v: repr(v)
    )
    def test_collapse_matches_python(self, run, index, case):
        friendly, device, _ = case
        assert run["collapse"][index] == collapse_doubled_device_name(
            friendly, device
        )


@toolchain
class TestTheLookup:
    def test_the_owners_emitter_is_named_once(self, run):
        assert run["display"]["plain"] == "KinCony AGv3 1 TX"

    def test_a_user_rename_is_tried_first(self, run):
        assert run["display"]["name_by_user"] == "KinCony AGv3 1 TX"

    def test_the_registry_name_is_tried_when_the_rename_does_not_match(self, run):
        # entity_display_name tries both and keeps the first that
        # collapses; a rename that does not match must not stop it.
        assert run["display"]["name_by_user_misses"] == "KinCony AGv3 1 TX"

    @pytest.mark.parametrize(
        "key", ["no_entity", "no_device", "no_registries"]
    )
    def test_missing_registry_data_falls_back_to_the_full_name(self, run, key):
        assert run["display"][key] == DOUBLED

    def test_no_state_falls_back_to_the_entity_id(self, run):
        assert run["display"]["no_state"] == "infrared.gone"

    def test_no_hass_falls_back_to_the_entity_id(self, run):
        assert run["display"]["no_hass"] == KIN

    def test_a_name_said_once_is_untouched(self, run):
        assert run["display"]["said_once"] == "Broadlink RM4 Pro"

    def test_an_unnamed_entity_is_its_id(self, run):
        assert run["display"]["unnamed"] == "infrared.no_name"
        assert run["full"]["unnamed"] == "infrared.no_name"

    def test_the_full_name_is_what_ha_composed(self, run):
        assert run["full"]["kin"] == DOUBLED


@toolchain
class TestTheEmitterList:
    """getEmitterOptions builds the one list behind the picker and the
    device header."""

    def _by_id(self, options):
        return {o["entity_id"]: o for o in options}

    def test_the_filter_is_unchanged(self, run):
        ids = [o["entity_id"] for o in run["options"]]
        assert ids == [KIN, BROADLINK, "infrared.no_name"]
        assert BROADLINK not in self._by_id(run["optionsExcluding"])

    def test_each_option_says_the_name_once_and_keeps_the_full_one(self, run):
        kin = self._by_id(run["options"])[KIN]
        assert kin["name"] == "KinCony AGv3 1 TX"
        assert kin["fullName"] == DOUBLED

    def test_untouched_names_are_the_same_in_both(self, run):
        bl = self._by_id(run["options"])[BROADLINK]
        assert bl["name"] == bl["fullName"] == "Broadlink RM4 Pro"

    def test_availability_is_unchanged(self, run):
        by_id = self._by_id(run["options"])
        assert by_id[KIN]["available"] is True
        assert by_id[BROADLINK]["available"] is False
        # GH #83: unknown is unproven, not down.
        assert by_id["infrared.no_name"]["available"] is True


# Every picker mounts the same component, which builds its chips from
# getEmitterOptions. One case per picker, as the owner asked.
PICKERS = {
    "Add Device": "ir-add-controlled-device-dialog.ts",
    "Assign": "ir-assign-signal-dialog.ts",
    "Promote": "ir-promote-dialog.ts",
    "Test emitter": "ir-test-emitter-dialog.ts",
}


class TestEverySurfaceNamesOnce:
    @pytest.mark.parametrize("surface", list(PICKERS), ids=list(PICKERS))
    def test_each_picker_uses_the_shared_picker(self, surface):
        text = _read(PICKERS[surface])
        assert 'import "./ir-emitter-picker.js";' in text
        assert "<ir-emitter-picker" in text
        picker = text.split("<ir-emitter-picker", 1)[1].split(
            "</ir-emitter-picker>", 1
        )[0]
        # The names come from hass; a picker without it names nothing.
        assert ".hass=${this.hass}" in picker
        # And nothing in the dialog builds its own emitter names.
        assert "friendly_name" not in text

    def test_the_picker_builds_its_chips_from_the_shared_list(self):
        text = _flat("ir-emitter-picker.ts")
        assert (
            'import { getEmitterOptions, type EmitterInfo } from "./emitter-options.js";'
            in text
        )
        assert (
            "return getEmitterOptions(this.hass, this._receiverIds, "
            "this.excludeEntityIds);"
        ) in text
        assert "friendly_name" not in _read("ir-emitter-picker.ts").split("*/", 1)[1]

    def test_the_picker_chip_says_the_short_name(self):
        text = _flat("ir-emitter-picker.ts")
        assert '<span class="em-name">${em.name}</span>' in text
        assert 'aria-label="${em.name}, ${word}"' in text

    def test_the_picker_tooltip_keeps_the_full_name(self):
        # Since chip health (ember): "{full name}, online, selected ·
        # {entity id}", still leading with HA's full name.
        text = _flat("ir-emitter-picker.ts")
        assert (
            'title="${em.fullName}, ${word}${em.fullName === em.entity_id '
            '? "" : ` · ${em.entity_id}`}"'
        ) in text

    def test_the_shared_list_names_through_the_rule(self):
        text = _flat("emitter-options.ts")
        assert "name: entityDisplayName(hass, entityId)," in text
        assert "fullName: entityFullName(hass, entityId)," in text

    def test_the_device_header_names_once_and_keeps_the_full_name(self):
        text = _flat("ir-device-detail.ts")
        rows = text.split("private _emitterRows(): HeaderChipRow[] {", 1)[1]
        rows = rows.split("private _pinRows", 1)[0]
        assert "getEmitterOptions(this.hass, receiverIds)" in rows
        assert "name: em.name," in rows
        assert "title: em.fullName," in rows

    def test_the_header_chip_tooltip_prefers_the_row_title(self):
        text = _flat("ir-header-chip-group.ts")
        assert "title?: string;" in text
        assert 'title="${row.title ?? row.name}, ${words}"' in text
        assert '<span class="chip-name">${row.name}</span>' in text

    def test_the_devices_tab_cards_name_once(self):
        text = _flat("ir-device-list.ts")
        assert "name: entityDisplayName(this.hass, entityId)," in text
        assert "fullName: entityFullName(this.hass, entityId)," in text
        assert (
            '<div class="card-name" title=${em.fullName}>${em.name}</div>'
            in text
        )
