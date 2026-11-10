"""Chip health, actually executed (ember, 2026-10-19).

Every emitter and receiver chip shows selection on the pill and health
on the dot: solid green when Home Assistant can reach the hardware, a
hollow ember ring when it cannot, and the one alarm, an ember edge and
wash, when it is selected and offline. One rule decides online for
every surface (``entity-health.ts``): ``unavailable`` and a missing
state are offline, ``unknown`` is online (GH #83).

This transpiles the pure modules (``entity-health.ts``,
``emitter-options.ts`` and ``ir-listen-state.ts``) with the repo's own
TypeScript and runs them under node, in the house pattern of
``test_pluck_helpers_js.py``: the rule, each chip's class across the
four states plus ``unknown`` and a missing state, the Listen chip's
online rule and the hardware card's "at least one infrared entity"
rule. The surfaces are lit components, which node cannot render, so
each one is checked the house way, by reading its source for the path
it takes to the rule. The CSS pins and the colour tokens are read the
same way.

The node half is SKIPPED when the frontend toolchain is not installed,
like its model; the source half always runs.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

toolchain = pytest.mark.skipif(
    not TSC.exists() or shutil.which("node") is None,
    reason="frontend toolchain not installed (node_modules / node)",
)

DRIVER = """
import {
    cardGlyph, cardHealth, healthChipClass, healthDotClass, healthPhrase,
    infraredEntitiesOf, isEntityOnline, partsHealth,
} from "./entity-health.js";
import { getEmitterOptions } from "./emitter-options.js";
import { listenOnline } from "./ir-listen-state.js";
import { CARD_ICONS, cardIconPath } from "./card-icons.js";

const states = {
    "infrared.live": { state: "2026-10-19T02:00:00+00:00" },
    "infrared.dead": { state: "unavailable" },
    "infrared.fresh": { state: "unknown" },
    "infrared.blank": {},
    "switch.bs_live": { state: "off" },
    "switch.bs_dead": { state: "unavailable" },
};
const KINDS = {
    online: "infrared.live",
    offline: "infrared.dead",
    unknown: "infrared.fresh",
    missing: "infrared.gone",
};
const online = {};
const chips = {};
for (const [kind, id] of Object.entries(KINDS)) {
    const on = isEntityOnline(states, id);
    online[kind] = on;
    for (const selected of [false, true]) {
        chips[`${kind}/${selected ? "selected" : "not_selected"}`] = {
            chip: healthChipClass(selected, on),
            dot: healthDotClass(on),
        };
    }
}
online.no_state_field = isEntityOnline(states, "infrared.blank");
online.no_states = isEntityOnline(undefined, "infrared.live");

const t = (key) => `<${key}>`;
const phrases = {
    online_selected: healthPhrase(true, true, t),
    offline_not_selected: healthPhrase(false, false, t),
};

const entities = {
    // An ESPHome proxy: one emitter, one receiver.
    "infrared.proxy_tx": { device_id: "dev-proxy" },
    "infrared.proxy_rx": { device_id: "dev-proxy" },
    // The same proxy's other entities do not count.
    "sensor.proxy_wifi": { device_id: "dev-proxy" },
    // An ESPHome event bridge: no infrared entity at all.
    "event.bridge_ir": { device_id: "dev-bridge" },
    "infrared.solo": { device_id: "dev-solo" },
};
const cardStates = (over) => ({
    "infrared.proxy_tx": { state: "2026-10-19T02:00:00+00:00" },
    "infrared.proxy_rx": { state: "2026-10-19T02:00:00+00:00" },
    "sensor.proxy_wifi": { state: "-60" },
    "event.bridge_ir": { state: "unavailable" },
    "infrared.solo": { state: "unknown" },
    ...over,
});
const hass = (over) => ({ states: cardStates(over), entities });
const dead = { state: "unavailable" };
const cards = {
    all_online: cardHealth(hass({}), "dev-proxy"),
    one_down: cardHealth(hass({ "infrared.proxy_tx": dead }), "dev-proxy"),
    all_down: cardHealth(
        hass({ "infrared.proxy_tx": dead, "infrared.proxy_rx": dead }), "dev-proxy"),
    all_down_but_sensor_up: cardHealth(
        hass({ "infrared.proxy_tx": dead, "infrared.proxy_rx": dead }), "dev-proxy"),
    one_missing_one_down: cardHealth(
        { states: { "infrared.proxy_rx": dead }, entities }, "dev-proxy"),
    bridge: cardHealth(hass({}), "dev-bridge"),
    bridge_with_fallback: cardHealth(hass({}), "dev-bridge", ["event.bridge_ir"]),
    unknown_is_online: cardHealth(hass({}), "dev-solo"),
    no_device_fallback_down: cardHealth(
        { states: { "infrared.orphan": dead }, entities }, undefined, ["infrared.orphan"]),
    no_device_no_ids: cardHealth(hass({}), undefined),
    no_hass: cardHealth(undefined, "dev-proxy"),
    of_proxy: infraredEntitiesOf(entities, "dev-proxy"),
};

const row = (sw) => ({
    receiver_entity_id: "infrared.live", switch_entity_id: sw,
    mode_entity_id: null, window_entity_id: null, codes_entity_id: null,
    ha_device_id: "dev", name: "Den RM4",
});
const listen = {
    both_online: listenOnline(states, row("switch.bs_live")),
    switch_down: listenOnline(states, row("switch.bs_dead")),
    switch_missing: listenOnline(states, row("switch.bs_gone")),
    receiver_down: listenOnline(
        states, { ...row("switch.bs_live"), receiver_entity_id: "infrared.dead" }),
    receiver_unknown: listenOnline(
        states, { ...row("switch.bs_live"), receiver_entity_id: "infrared.fresh" }),
    no_states: listenOnline(undefined, row("switch.bs_live")),
};

const emitters = Object.fromEntries(
    getEmitterOptions({ states: {
        "infrared.live": { entity_id: "infrared.live", state: "x", attributes: {} },
        "infrared.dead": { entity_id: "infrared.dead", state: "unavailable", attributes: {} },
        "infrared.fresh": { entity_id: "infrared.fresh", state: "unknown", attributes: {} },
    } }, new Set()).map((o) => [o.entity_id, o.available]),
);

const cap = (online, listening) => ({ online, listening });
const glyphs = {
    bridge: cardGlyph("none", null),
    bridge_capture: cardGlyph("none", cap(true, true)),
    online: cardGlyph("online", null),
    offline: cardGlyph("offline", null),
    ready: cardGlyph("online", cap(true, false)),
    listening: cardGlyph("online", cap(true, true)),
    chip_offline: cardGlyph("online", cap(false, false)),
    all_offline_capture: cardGlyph("offline", cap(true, true)),
};

const partStates = {
    "infrared.tx": { state: "2026-10-19T02:00:00+00:00" },
    "infrared.rx": { state: "2026-10-19T02:00:00+00:00" },
    "infrared.tx_dead": { state: "unavailable" },
    "infrared.rx_dead": { state: "unavailable" },
    "infrared.fresh": { state: "unknown" },
};
const parts = {
    emitter_online: partsHealth(partStates, ["infrared.tx"]),
    emitter_down: partsHealth(partStates, ["infrared.tx_dead"]),
    receiver_online: partsHealth(partStates, ["infrared.rx"]),
    receiver_down: partsHealth(partStates, ["infrared.rx_dead"]),
    receiver_unknown: partsHealth(partStates, ["infrared.fresh"]),
    receiver_missing: partsHealth(partStates, ["infrared.gone"]),
    bridge: partsHealth(partStates, [undefined]),
    nothing: partsHealth(partStates, []),
    proxy_all_up: partsHealth(partStates, ["infrared.rx", "infrared.tx"]),
    proxy_rx_down: partsHealth(partStates, ["infrared.rx_dead", "infrared.tx"]),
    proxy_tx_down: partsHealth(partStates, ["infrared.rx", "infrared.tx_dead"]),
    proxy_all_down: partsHealth(partStates, ["infrared.rx_dead", "infrared.tx_dead"]),
    proxy_no_rx_entity: partsHealth(partStates, [undefined, "infrared.tx"]),
};

const icons = {};
for (const kind of Object.keys(CARD_ICONS)) {
    for (const glyph of ["plain", "online", "ready", "listening", "offline"]) {
        const path = cardIconPath(kind, glyph);
        icons[`${kind}/${glyph}`] =
            path === CARD_ICONS[kind].solid ? "solid"
            : path === CARD_ICONS[kind].outline ? "outline" : "neither";
    }
}
const iconPaths = CARD_ICONS;

console.log(JSON.stringify({
    online, chips, phrases, cards, listen, emitters, glyphs, icons, iconPaths, parts,
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("entityhealthjs")
    subprocess.run(
        [
            str(TSC),
            "src/entity-health.ts", "src/emitter-options.ts", "src/ir-listen-state.ts",
            "src/card-icons.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
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


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _flat(name: str) -> str:
    return " ".join(_read(name).split())


# A CSS rule as these files write it: the selector, an opening brace at
# the end of its line, and the closing brace alone on a later line. The
# body can hold `${EMBER_VAR}` interpolations, so it is not [^}]*.
_RULE = re.compile(r"(?ms)^[ \t]*([^\n{}]+?)[ \t]*\{[ \t]*\n(.*?)\n[ \t]*\}")


def _rules(text: str) -> list[tuple[str, str]]:
    return [(sel.strip(), body) for sel, body in _RULE.findall(text)]


def _block(text: str, selector: str) -> str:
    """The declarations of the first CSS rule with exactly this
    selector."""
    for sel, body in _rules(text):
        if sel == selector:
            return body
    raise AssertionError(selector)


# --------------------------------------------------------------------------
# The rule, executed
# --------------------------------------------------------------------------


@toolchain
class TestTheRule:
    def test_online_and_offline(self, run):
        assert run["online"]["online"] is True
        assert run["online"]["offline"] is False

    def test_unknown_is_online(self, run):
        """GH #83: an emitter's state is its last-send time, unknown
        until the first send. Unproven is not down."""
        assert run["online"]["unknown"] is True

    def test_a_missing_state_is_offline(self, run):
        assert run["online"]["missing"] is False
        assert run["online"]["no_states"] is False

    def test_a_state_object_without_a_state_is_online(self, run):
        # Only "unavailable" says HA cannot reach it.
        assert run["online"]["no_state_field"] is True

    def test_the_emitter_list_uses_the_rule(self, run):
        assert run["emitters"] == {
            "infrared.live": True,
            "infrared.dead": False,
            "infrared.fresh": True,
        }


@toolchain
class TestEachChipsClass:
    """The four states, plus unknown and a missing state."""

    @pytest.mark.parametrize(
        "case,chip,dot",
        [
            ("online/not_selected", "", "online"),
            ("offline/not_selected", "", "offline"),
            ("online/selected", "on", "online"),
            ("offline/selected", "on down", "offline"),
            ("unknown/not_selected", "", "online"),
            ("unknown/selected", "on", "online"),
            ("missing/not_selected", "", "offline"),
            ("missing/selected", "on down", "offline"),
        ],
    )
    def test_the_class(self, run, case, chip, dot):
        assert run["chips"][case] == {"chip": chip, "dot": dot}

    def test_the_phrase_says_health_then_selection(self, run):
        assert run["phrases"]["online_selected"] == "<common.online>, <common.selected>"
        assert (
            run["phrases"]["offline_not_selected"]
            == "<common.offline>, <common.not_selected>"
        )


@toolchain
class TestTheCardRule:
    """OFFLINE only when the card's device has at least one infrared
    entity and every one of them is unavailable."""

    def test_all_online(self, run):
        assert run["cards"]["all_online"] == "online"

    def test_one_down_is_not_offline(self, run):
        assert run["cards"]["one_down"] == "online"

    def test_all_down_is_offline(self, run):
        assert run["cards"]["all_down"] == "offline"

    def test_other_entities_on_the_device_do_not_count(self, run):
        # The proxy's Wi-Fi sensor still reports; its IR is gone.
        assert run["cards"]["all_down_but_sensor_up"] == "offline"
        assert run["cards"]["of_proxy"] == ["infrared.proxy_tx", "infrared.proxy_rx"]

    def test_a_missing_state_counts_as_down(self, run):
        assert run["cards"]["one_missing_one_down"] == "offline"

    def test_a_card_with_no_infrared_entity_never_shows_offline(self, run):
        """The ESPHome event bridges (RX-BRIDGE) have no infrared
        entity. Their event entity being unavailable says nothing."""
        assert run["cards"]["bridge"] == "none"
        assert run["cards"]["bridge_with_fallback"] == "none"

    def test_unknown_is_online_on_a_card_too(self, run):
        assert run["cards"]["unknown_is_online"] == "online"

    def test_an_entity_with_no_device_stands_in_for_its_card(self, run):
        assert run["cards"]["no_device_fallback_down"] == "offline"
        assert run["cards"]["no_device_no_ids"] == "none"

    def test_no_hass_is_no_health(self, run):
        assert run["cards"]["no_hass"] == "none"


@toolchain
class TestTheListenRule:
    """Offline when either the receiver or BroadSniff's switch is
    unavailable or missing (owner, 2026-10-19)."""

    def test_both_online(self, run):
        assert run["listen"]["both_online"] is True

    @pytest.mark.parametrize(
        "case", ["switch_down", "switch_missing", "receiver_down", "no_states"]
    )
    def test_either_down_is_offline(self, run, case):
        assert run["listen"][case] is False

    def test_an_unknown_receiver_is_online(self, run):
        assert run["listen"]["receiver_unknown"] is True


@toolchain
class TestTheIconsPart:
    """Owner ruling, 2026-10-19: an Emitters card's icon follows its
    emitter, a Receivers card's its receiver, a Proxies card's every
    part, ember if any one is down."""

    @pytest.mark.parametrize(
        "case,health",
        [
            ("emitter_online", "online"),
            ("emitter_down", "offline"),
            ("receiver_online", "online"),
            ("receiver_down", "offline"),
            ("receiver_unknown", "online"),
            ("receiver_missing", "offline"),
            ("bridge", "none"),
            ("nothing", "none"),
            ("proxy_all_up", "online"),
            ("proxy_rx_down", "offline"),
            ("proxy_tx_down", "offline"),
            ("proxy_all_down", "offline"),
            ("proxy_no_rx_entity", "online"),
        ],
    )
    def test_the_part(self, run, case, health):
        assert run["parts"][case] == health


@toolchain
class TestTheCardGlyph:
    """Owner bench, 2026-10-19: the glyph is the card's health signal."""

    @pytest.mark.parametrize(
        "case,glyph",
        [
            ("bridge", "plain"),
            ("bridge_capture", "plain"),
            ("online", "online"),
            ("offline", "offline"),
            ("ready", "ready"),
            ("listening", "listening"),
            # A capture device follows its chip, and a chip that cannot
            # listen is offline.
            ("chip_offline", "offline"),
            ("all_offline_capture", "offline"),
        ],
    )
    def test_the_glyph(self, run, case, glyph):
        assert run["glyphs"][case] == glyph


# @mdi/js 7.4.47, byte for byte: sha256 of each path, first 16 hex digits.
MDI_PAIRS = {
    "emitter": ("f6367945638e1cce", "afecae5c0dac4120"),  # upload / upload-outline
    "receiver": ("0de005fc9dbf8704", "ab114e29a6c8de15"),  # download / download-outline
    # swap-vertical-circle / -outline (radio-tower has no outline twin)
    "proxy": ("9f62fddb597943d2", "ba9d29b6ece0076b"),
    # gesture-tap-button / record-circle-outline (owner ruling): the
    # finger has no outline twin, so offline the shape changes too.
    "capture": ("ea407a88028af208", "d73f87f0b2747eec"),
}


@toolchain
class TestTheCardIcons:
    """Owner bench on VM999 (real HA icons), 2026-10-19: the solid icon
    online, its outline twin offline, no stroke added. Full against
    empty reads without colour."""

    @pytest.mark.parametrize("kind", list(MDI_PAIRS))
    @pytest.mark.parametrize(
        "glyph,form",
        [
            ("online", "solid"),
            ("ready", "solid"),
            ("listening", "solid"),
            ("offline", "outline"),
            # No infrared entity: the outline it always had, in grey.
            ("plain", "outline"),
        ],
    )
    def test_solid_while_it_answers_outline_while_offline(self, run, kind, glyph, form):
        assert run["icons"][f"{kind}/{glyph}"] == form

    @pytest.mark.parametrize("kind", list(MDI_PAIRS))
    def test_each_pair_is_mdi_byte_for_byte(self, run, kind):
        import hashlib

        pair = run["iconPaths"][kind]
        solid, outline = MDI_PAIRS[kind]
        assert hashlib.sha256(pair["solid"].encode()).hexdigest()[:16] == solid
        assert hashlib.sha256(pair["outline"].encode()).hexdigest()[:16] == outline

    def test_there_are_four_pairs(self, run):
        assert sorted(run["iconPaths"]) == sorted(MDI_PAIRS)


# --------------------------------------------------------------------------
# Every surface takes the rule
# --------------------------------------------------------------------------


class TestTheHeaderRows:
    def test_the_device_emitters_row_sets_health(self):
        rows = _flat("ir-device-detail.ts").split(
            "private _emitterRows(): HeaderChipRow[] {", 1
        )[1]
        rows = rows.split("private _pinRows", 1)[0]
        assert "online: em.available," in rows
        assert "down:" not in rows

    def test_the_remote_receivers_row_sets_health_live(self):
        rows = _flat("ir-device-list.ts").split(
            "private _receiverRows(remote: TriggerRemoteInfo): HeaderChipRow[] {", 1
        )[1].split("private _pinRows", 1)[0]
        assert "online: isEntityOnline(this.hass?.states, r.entity_id)," in rows

    @pytest.mark.parametrize("name", ["ir-device-detail.ts", "ir-device-list.ts"])
    def test_pin_rows_carry_no_health(self, name):
        pins = _flat(name).split("private _pinRows(", 1)[1].split("}));", 1)[0]
        assert "online" not in pins

    def test_the_group_draws_both_channels(self):
        text = _flat("ir-header-chip-group.ts")
        assert "online?: boolean;" in text
        assert "down?: boolean;" not in text
        assert 'healthChipClass(row.on, row.online === true) || "off"' in text
        assert (
            "const dot = health ? `dot ${healthDotClass(row.online === true)}` : \"dot\";"
        ) in text
        assert "<span class=${dot}></span>" in text
        assert "healthPhrase(row.online === true, row.on, t)" in text
        assert 'title="${row.title ?? row.name}, ${words}"' in text
        assert 'aria-label="${row.name}, ${words}"' in text


# The receiver picker's users, and where each is mounted.
RECEIVER_PICKER_DIALOGS = {
    "Add Remote": "ir-add-trigger-remote-dialog.ts",
    "Duplicate Remote": "ir-duplicate-trigger-remote-dialog.ts",
    "Make a Remote": "ir-promote-remote-dialog.ts",
    "Trigger dialog": "ir-trigger-dialog.ts",
}
DIALOG_MOUNTS = [
    ("ir-clips.ts", "ir-trigger-dialog", 2),
    ("ir-clips.ts", "ir-promote-remote-dialog", 1),
    ("ir-device-detail.ts", "ir-trigger-dialog", 2),
    ("ir-device-list.ts", "ir-trigger-dialog", 2),
    ("ir-device-list.ts", "ir-duplicate-trigger-remote-dialog", 1),
    ("ir-device-list.ts", "ir-promote-remote-dialog", 1),
    ("ir-trigger-dialog.ts", "ir-add-trigger-remote-dialog", 1),
    ("ha-panel-ir-devices.ts", "ir-add-trigger-remote-dialog", 1),
]


class TestThePickers:
    def test_the_emitter_picker(self):
        text = _flat("ir-emitter-picker.ts")
        assert "const cls = healthChipClass(on, em.available);" in text
        assert '<span class="dot ${healthDotClass(em.available)}"></span>' in text
        assert "const word = healthPhrase(em.available, on, t);" in text
        assert '.em.down' not in text
        assert "`, healthDotStyles];" in text

    def test_the_receiver_picker(self):
        text = _flat("ir-receiver-picker.ts")
        assert "@property({ attribute: false }) public hass?: any;" in text
        assert "const online = health && isEntityOnline(this.hass.states, r.entity_id);" in text
        assert 'const cls = health ? healthChipClass(on, online) : on ? "on" : "";' in text
        assert '<span class="dot ${health ? healthDotClass(online) : ""}"></span>' in text
        assert 'title="${r.name} ${medium}, ${word} · ${r.entity_id}"' in text
        assert "`, healthDotStyles];" in text

    def test_no_hass_is_no_false_offline(self):
        """A consumer that forgot .hass would otherwise show every
        receiver as offline."""
        assert "const health = this.hass !== undefined;" in _flat("ir-receiver-picker.ts")

    @pytest.mark.parametrize(
        "surface", list(RECEIVER_PICKER_DIALOGS), ids=list(RECEIVER_PICKER_DIALOGS)
    )
    def test_each_receiver_picker_gets_hass(self, surface):
        text = _read(RECEIVER_PICKER_DIALOGS[surface])
        picker = text.split("<ir-receiver-picker", 1)[1].split("</ir-receiver-picker>", 1)[0]
        assert ".hass=${this.hass}" in picker
        assert "public hass" in text

    @pytest.mark.parametrize(
        "name,tag,count", DIALOG_MOUNTS, ids=[f"{n}:{t}" for n, t, _ in DIALOG_MOUNTS]
    )
    def test_each_mount_passes_hass(self, name, tag, count):
        text = _read(name)
        mounts = re.findall(r"<" + re.escape(tag) + r"\n(.*?)>", text, re.S)
        assert len(mounts) == count
        for body in mounts:
            assert ".hass=${this.hass}" in body


class TestTheListenChip:
    """The Sniffer's Listen pill offline (RF hear round 1): ember border
    and badge, pickers greyed, no press, no window shown."""

    def test_offline_disables_and_goes_ember(self):
        text = _flat("ir-listen-chip.ts")
        assert "const online = pillOnline(this.hass?.states, row);" in text
        assert 'const tone = look === "offline" ? EMBER_VAR.cssText' in text
        assert "const pressable = pillPressable(look) && !this._busy;" in text
        state = _flat("ir-listen-state.ts")
        assert 'return look !== "offline" && look !== "waiting" && look !== "status";' in state
        assert "?disabled=${!pressable}" in text
        assert 'if (look === "offline") return t("listen.offline_title", { name });' in text

    def test_offline_shows_no_window(self):
        text = _flat("ir-listen-chip.ts")
        assert (
            "const live = online ? this._live() : "
            "{ on: false, endsAt: null, phase: null, frequencyHz: null };"
        ) in text

    def test_the_pickers_grey_while_down_or_open(self):
        state = _flat("ir-listen-state.ts")
        assert (
            'return look === "idle" || look === "hearing" || look === "waiting";'
        ) in state
        chip = _flat("ir-listen-chip.ts")
        assert "const active = pickersActive(look) && !this._busy;" in chip
        assert chip.count("?inactive=${!active}") == 3


class TestTheHardwareCards:
    """Owner bench, 2026-10-19, and RF hear round 1 (one row per
    capability): each row's badge carries its own entity's health, no
    dot; a card whose every entity is unavailable gets an ember edge,
    the outline icon and "Offline" in its top-right corner."""

    def _card(self) -> str:
        return _flat("ir-device-list.ts").split("private _renderHardwareCard(", 1)[1].split(
            "private _renderHardwareSection(", 1
        )[0]

    def test_no_dot_by_the_name(self):
        card = self._card()
        assert "_renderHwDot" not in card and "hw-dot" not in card
        assert "offline-badge" not in card

    def test_an_all_offline_card_gets_the_edge_and_the_corner(self):
        card = self._card()
        assert "const offline = cardOffline(card);" in card
        assert '${offline ? "is-offline" : ""}' in card
        assert '> ${this._renderOfflineCorner(health)} <div class="card-header">' in card
        rows = _read("ir-hardware-rows.ts")
        assert "return card.rows.length > 0 && card.rows.every((r) => !r.available);" in rows

    def test_the_glyph_class_comes_from_the_rule(self):
        card = self._card()
        assert 'class="card hw-card hw-glyph-${glyph} ' in card
        assert (
            "const glyph = cardGlyph( partsHealth( this.hass?.states, "
            "part.map((r) => r.entity_id), ), null, );"
        ) in card
        # Its part: an emitter card its transmitters, a receiver card its
        # receivers, a proxy card every row.
        assert (
            'kind === "emitters" ? r.direction === "tx" : kind === "receivers" '
            '? r.direction === "rx" : true,'
        ) in card

    def test_each_row_badge_follows_its_own_entity_and_says_its_health(self):
        text = _flat("ir-device-list.ts")
        row = text.split("private _renderCapabilityRow(", 1)[1].split("private ", 1)[0]
        # Radio rows wear the light badge (owner, 2026-11-06 18:34).
        assert (
            'class="badge cap-badge ${row.medium === "rf" ? "rf" : ""} '
            '${row.available ? "" : "offline"}"'
        ) in row
        assert 'role="img" aria-label=${title} title=${title}' in row
        title = text.split("private _badgeTitle(", 1)[1].split("private ", 1)[0]
        assert 't(row.available ? "common.online" : "common.offline")' in title
        rows = _read("ir-hardware-rows.ts")
        assert 'return st !== undefined && st.state !== "unavailable";' in rows

    def test_the_corner_shows_only_when_offline(self):
        text = _flat("ir-device-list.ts")
        corner = text.split("private _renderOfflineCorner(", 1)[1].split("private ", 1)[0]
        assert 'if (health !== "offline") return nothing;' in corner
        assert 't("devlist.offline_label")' in corner
        assert 'class="hw-offline"' in corner

    def test_the_right_column_is_blank_until_hair_knows(self):
        """Ruling Q8: after a restart HAIR cannot tell "never" from "not
        since the restart", so the column stays blank."""
        rows = _read("ir-hardware-rows.ts")
        assert 'if (!at) return { kind: "none" };' in rows
        text = _flat("ir-device-list.ts")
        fact = text.split("private _factText(", 1)[1].split("private ", 1)[0]
        assert 'if (fact.kind === "none") return "";' in fact
        assert "never" not in fact

    def test_blasters_carry_no_health(self):
        section = _read("ir-device-list.ts").split("<!-- Blasters", 1)[1].split(
            "<!-- Hardware:", 1
        )[0]
        assert "_hwHealth" not in section and "offline" not in section


# --------------------------------------------------------------------------
# CSS pins and tokens
# --------------------------------------------------------------------------


class TestTheStyles:
    def _health(self) -> str:
        text = _read("ir-header-chip-styles.ts")
        return text.split("export const healthDotStyles = css`", 1)[1].split("`;", 1)[0]

    def test_the_offline_dot_is_a_ring(self):
        ring = _block(self._health(), ".dot.offline")
        assert "background: transparent;" in ring
        assert "border: 1.6px solid ${EMBER_VAR};" in ring
        assert "box-sizing: border-box;" in ring
        assert "box-shadow: none;" in ring

    def test_nothing_offline_glows(self):
        css = self._health()
        assert "box-shadow: none;" in _block(css, ".on .dot.offline")
        for selector, body in _rules(css):
            if "offline" in selector:
                assert "0 0 5px" not in body, selector

    def test_only_selected_and_online_glows(self):
        css = self._health()
        assert "0 0 5px" in _block(css, ".on .dot.online")
        assert "box-shadow: none;" in _block(css, ".dot.online")

    def test_the_alarm_is_ember(self):
        alarm = _block(self._health(), ".on.down")
        assert "color-mix(in srgb, ${EMBER_VAR} 60%, transparent)" in alarm
        assert "color-mix(in srgb, ${EMBER_VAR} 9%, transparent)" in alarm
        assert "217, 164, 65" not in alarm

    def test_the_card_badges_edge_glyph_and_corner_are_ember(self):
        text = _read("ir-device-list.ts")
        badge = _block(text, ".badge.cap-badge.offline")
        assert "color: ${EMBER_VAR};" in badge
        assert "color-mix(in srgb, ${EMBER_VAR} 13%, transparent)" in badge
        edge = _block(text, ".hw-card.is-offline")
        assert "color-mix(in srgb, ${EMBER_VAR} 40%, transparent)" in edge
        corner = _block(text, ".hw-offline")
        assert "color: ${EMBER_VAR};" in corner
        # Tucked into the corner, out of the name row's flow.
        assert "position: absolute;" in corner
        assert "position: relative;" in _block(text, ".hw-card")
        # Capitals, about 20 percent under the 0.75rem it was, tracked.
        assert "text-transform: uppercase;" in corner
        assert "font-size: 0.6rem;" in corner
        assert "letter-spacing: 0.06em;" in corner
        # Plain text: no ground, no border.
        assert "background" not in corner and "border" not in corner

    def test_the_offline_glyph_is_the_outline_in_ember_with_no_stroke(self):
        """The hollow comes from the outline twin's own path. A stroke on
        top read heavy and blurry in HA's ha-svg-icon (owner bench)."""
        text = _read("ir-device-list.ts")
        glyph = _block(text, ".hw-card.hw-glyph-offline .card-header ha-svg-icon")
        assert "color: ${EMBER_VAR};" in glyph
        styles = text.split("static styles", 1)[1]
        for sel, body in _rules(styles):
            if "hw-card" in sel and "ha-svg-icon" in sel:
                assert not re.search(r"(?m)^\s*(stroke[\w-]*|fill)\s*:", body), sel

    def test_the_glyph_colours(self):
        text = _read("ir-device-list.ts")
        # The card is information only since RF hear round 1: no capture
        # gold or green on its icon, only health.
        for glyph in ("ready", "listening", "waiting"):
            assert f"hw-glyph-{glyph}" not in text, glyph
        for glyph, colour in (("online", "${ONLINE_VAR}"),):
            body = _block(text, f".hw-card.hw-glyph-{glyph} .card-header ha-svg-icon")
            assert f"color: {colour};" in body, glyph
            assert "fill:" not in body and "stroke" not in body, glyph
        # The plain glyph (no infrared entity) keeps today's colour: no
        # rule names it.
        assert "hw-glyph-plain" not in text.split("static styles", 1)[1]
        assert "color: var(--secondary-text-color);" in _block(text, ".card-header ha-svg-icon")

    def test_each_surface_keeps_its_dot_size_and_rings_one_wider(self):
        styles = _read("ir-header-chip-styles.ts")
        assert "width: 6px;" in _block(styles, ".dot")
        assert "width: var(--hair-ring, 7px);" in _block(self._health(), ".dot.offline")
        for name in ("ir-emitter-picker.ts", "ir-receiver-picker.ts"):
            text = _read(name)
            assert "width: 7px;" in _block(text, ".dot"), name
            assert "--hair-ring: 8px;" in text, name
        # The Devices tab cards carry no dot since the owner's bench.
        assert ".hw-dot" not in _read("ir-device-list.ts")

    def test_the_tokens_live_on_the_panel_host(self):
        assert "static styles = [hairHealthTokens, css`" in _read("ha-panel-ir-devices.ts")
        tokens = _read("ir-header-chip-styles.ts").split(
            "export const hairHealthTokens = css`", 1
        )[1].split("`;", 1)[0]
        for prop in ("--hair-ember:", "--hair-ember-rgb:", "--hair-online:"):
            assert prop in tokens


LITERALS = re.compile(r"#e65100|230,\s*81,\s*0|#6cbf78|108,\s*191,\s*120", re.I)
EMBER = re.compile(r"#e65100|230,\s*81,\s*0", re.I)

# Surfaces that carry no colour literal at all.
CLEAN_SURFACES = [
    "ir-header-chip-styles.ts",
    "ir-header-chip-group.ts",
    "ir-emitter-picker.ts",
    "emitter-options.ts",
    "ir-receiver-picker.ts",
    "ir-listen-chip.ts",
    "ir-listen-row.ts",
    "ir-listen-state.ts",
    "ir-device-detail.ts",
    "ha-panel-ir-devices.ts",
]

# Ember copies as of this round, per file (owner, 2026-10-19). Leave
# them; the light and dark pass moves them onto the token and lowers
# these numbers. A count may only go down, and a file not listed may
# not start one.
EMBER_COPIES = {
    "entity-health.ts": 2,  # the token's own definition
    "ir-action-chip-styles.ts": 3,
    "ir-clips.ts": 2,
    "ir-command-row.ts": 3,
    "ir-confirm-dialog.ts": 2,
    "ir-device-list.ts": 3,
    "ir-device-settings-dialog.ts": 4,
    "ir-icons.ts": 3,
    "ir-matrix-card.ts": 10,
    "ir-mirror.ts": 2,
    "ir-pluck-add-remote-dialog.ts": 1,
    "ir-pluck.ts": 2,
    "ir-save-perfect-dialog.ts": 1,
    "ir-signal-alias.ts": 2,
    "ir-signal-editor.ts": 4,
    "ir-signal-monitor.ts": 2,
    "ir-tangle-decide.ts": 3,
    "ir-tangle-fix.ts": 1,
    "ir-tangle-unusual.ts": 1,
    "ir-trigger-dialog.ts": 4,
    "ir-trigger-remote-settings-dialog.ts": 4,
    "ir-wigs.ts": 8,
}


class TestTheTokens:
    def test_the_literals_live_once(self):
        text = _read("entity-health.ts")
        assert 'export const EMBER = "#e65100";' in text
        assert 'export const EMBER_RGB = "230, 81, 0";' in text
        assert 'export const ONLINE_GREEN = "#6cbf78";' in text

    @pytest.mark.parametrize("name", CLEAN_SURFACES)
    def test_no_surface_carries_a_literal(self, name):
        assert not LITERALS.search(_read(name)), name

    def test_the_device_lists_health_code_carries_none(self):
        """ir-device-list.ts holds three older ember copies (the trigger
        OFF badge and the delete hover), pinned below; its health code
        uses the token only."""
        text = _read("ir-device-list.ts")
        helpers = text.split("private _renderOfflineCorner(", 1)[1].split(
            "private _renderHardwareSection(", 1
        )[0]
        assert not LITERALS.search(helpers)
        assert not LITERALS.search(_read("ir-hardware-rows.ts"))
        for selector in (
            ".badge.cap-badge.offline",
            ".hw-card.is-offline",
            ".hw-card.hw-glyph-offline .card-header ha-svg-icon",
            ".hw-card.hw-glyph-online .card-header ha-svg-icon",
            ".hw-offline",
        ):
            assert not LITERALS.search(_block(text, selector)), selector
        assert not re.search(r"#6cbf78|108,\s*191,\s*120", text, re.I)

    def test_no_file_adds_an_ember_copy(self):
        grown = {}
        for path in sorted(SRC.glob("*.ts")):
            count = len(EMBER.findall(path.read_text(encoding="utf-8")))
            if count > EMBER_COPIES.get(path.name, 0):
                grown[path.name] = count
        assert not grown, f"ember copies added (use the --hair-ember token): {grown}"
