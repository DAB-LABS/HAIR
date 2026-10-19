"""The panel side of capture devices: the chips, the switch pill, Listen.

The decisions that matter here are timing, placement and choice: when a
Listen chip blooms, how its fill drains, which receiver the editor's
Listen uses, what the switch picker offers, and which one row carries
the "last heard" tint. Those live as plain functions in
``ir-listen-state.ts``, and this module transpiles that file with the
repo's own TypeScript and runs them under node, the way
``test_landed_notice_js.py`` does for its helpers.

The node-driven tests are SKIPPED when the frontend toolchain is not
installed (CI runs pytest without node_modules). The skip lives on the
``run`` fixture, so the source-level tests below, which pin the wiring
a run cannot see from outside the components, run everywhere.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from custom_components.hair.receiver_window import (
    ARM_FAILED_CODE,
    NO_CAPTURE_SWITCH_CODE,
    RECEIVER_UNAVAILABLE_CODE,
)

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
REPO = COMPONENT.parent.parent

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

NOW = "2026-10-19T12:00:00.000Z"

DRIVER = """
import {
    arrivalBloomKey, captureSignature, chipBlock, lastHeardTarget, listenBlooms,
    listenChoices, listenLive, listenOnline, newestSeen, pickReceiver, pickerEntities,
    pickerMenu, planFill, rxCaptureMatch, MAX_FILL_MS,
} from "./ir-listen-state.js";
import { onArrival } from "./ir-arrivals.js";
import { cardGlyph } from "./entity-health.js";
import { cardIconPath, CARD_ICONS } from "./card-icons.js";

const NOW = Date.parse("__NOW__");
const at = (s) => new Date(NOW + s * 1000).toISOString();
const live = (on, endsAt) => ({ on, endsAt });
const rx = (attributes) => ({ "infrared.r": { state: "on", attributes } });
const named = (friendly_name) => ({ state: "off", attributes: { friendly_name } });

const row = {
    receiver_entity_id: "infrared.r", name: "RM4", ha_device_id: "dev",
    available: true, switch_entity_id: "switch.ir", source: "device",
    device_switches: [
        { entity_id: "switch.ir", name: "RM4 IR capture" },
        { entity_id: "switch.rf", name: "RM4 RF capture" },
    ],
};

const out = {
    fill: {
        five_left: planFill(at(5), NOW),
        past: planFill(at(-3), NOW),
        garbage: planFill("not a time", NOW),
        clock_far_ahead: planFill(at(MAX_FILL_MS / 1000 + 60), NOW),
    },
    live: {
        open: listenLive(rx({ capturing: true, window_ends_at: at(4) }), row),
        open_without_deadline: listenLive(rx({ capturing: true }), row),
        closed_keeps_no_deadline: listenLive(rx({ capturing: false, window_ends_at: at(4) }), row),
        a_switch_that_is_on_means_nothing: listenLive({
            "infrared.r": { state: "on", attributes: { capturing: false } },
            "switch.ir": { state: "on", attributes: { window_ends_at: at(4) } },
        }, row),
    },
    online: {
        both: listenOnline({ "infrared.r": { state: "on" }, "switch.ir": { state: "off" } }, row),
        receiver_unknown: listenOnline(
            { "infrared.r": { state: "unknown" }, "switch.ir": { state: "off" } }, row,
        ),
        receiver_unavailable: listenOnline(
            { "infrared.r": { state: "unavailable" }, "switch.ir": { state: "off" } }, row,
        ),
        switch_unavailable: listenOnline(
            { "infrared.r": { state: "on" }, "switch.ir": { state: "unavailable" } }, row,
        ),
        helper_chosen_missing: listenOnline(
            { "infrared.r": { state: "on" } }, { ...row, switch_entity_id: "input_boolean.x" },
        ),
        no_switch_yet: listenOnline(
            { "infrared.r": { state: "on" } }, { ...row, switch_entity_id: null, source: null },
        ),
        not_loaded: listenOnline({}, { ...row, available: false }),
    },
    bloom: {
        first_sight_on: listenBlooms(undefined, live(true, at(9))),
        opened: listenBlooms(live(false, null), live(true, at(10))),
        new_deadline: listenBlooms(live(true, at(3)), live(true, at(10))),
        plain_refresh: listenBlooms(live(true, at(6)), live(true, at(6))),
        closed: listenBlooms(live(true, at(1)), live(false, null)),
    },
    block: {
        ready: chipBlock(row, true),
        no_switch: chipBlock({ ...row, switch_entity_id: null, source: null }, true),
        offline: chipBlock(row, false),
        offline_without_switch: chipBlock({ ...row, switch_entity_id: null, source: null }, false),
    },
    signature: {
        some: captureSignature({
            "infrared.b": { state: "on", attributes: { capturing: false } },
            "infrared.a": { state: "on", attributes: { capturing: true } },
            "infrared.athom": { state: "on", attributes: {} },
            "switch.x": { state: "on", attributes: { capturing: true } },
            "infrared.bad": { state: "on", attributes: { capturing: "yes" } },
        }),
        window_opening_changes_nothing: captureSignature({
            "infrared.a": { state: "on", attributes: { capturing: false } },
        }) === captureSignature({
            "infrared.a": { state: "on", attributes: { capturing: true, window_ends_at: at(9) } },
        }),
        none: captureSignature(undefined),
    },
    choices: (() => {
        const receivers = [
            { entity_id: "infrared.office", name: "Office RM mini" },
            { entity_id: "infrared.living", name: "Living Room RM4" },
            { entity_id: "infrared.athom", name: "Athom IR Proxy" },
        ];
        const rows = [
            { ...row, receiver_entity_id: "infrared.office", name: "Office RM mini" },
            {
                ...row, receiver_entity_id: "infrared.living", name: "Living Room RM4",
                available: false,
            },
        ];
        const choices = listenChoices(receivers, rows);
        const offline = new Set(["infrared.office"]);
        const online = (id) => !offline.has(id);
        return {
            choices,
            last_used: pickReceiver(choices, "infrared.athom")?.entityId,
            last_used_gone: pickReceiver(choices, "infrared.gone")?.entityId,
            first_visit: pickReceiver(choices, null)?.entityId,
            bridge_only: pickReceiver(listenChoices([], []), "infrared.athom"),
            last_used_offline: pickReceiver(choices, "infrared.office", online)?.entityId,
            first_offline: pickReceiver(choices, null, online)?.entityId,
            all_offline: pickReceiver(choices, "infrared.living", () => false)?.entityId,
        };
    })(),
    picker: {
        all: pickerEntities({
            "switch.b_switch": { state: "off", attributes: { friendly_name: "Beta" } },
            "input_boolean.learn": named("Alpha learn mode"),
            "light.lamp": { state: "on", attributes: { friendly_name: "Aaa lamp" } },
            "switch.no_name": { state: "off", attributes: {} },
            "infrared.r": { state: "on", attributes: { friendly_name: "RM4" } },
        }, ""),
        by_name: pickerEntities({
            "switch.b_switch": { state: "off", attributes: { friendly_name: "Beta" } },
            "input_boolean.learn": named("Alpha learn mode"),
        }, "  LEARN "),
        by_id: pickerEntities({
            "switch.b_switch": { state: "off", attributes: { friendly_name: "Beta" } },
            "input_boolean.learn": { state: "off", attributes: { friendly_name: "Alpha" } },
        }, "b_sw"),
        menu: pickerMenu(row),
        menu_none_chosen: pickerMenu({ ...row, switch_entity_id: null, source: null }),
        menu_helper_chosen: pickerMenu(
            { ...row, switch_entity_id: "input_boolean.learn", source: "user" }, "Learn mode",
        ),
        // Owner ruling 2026-10-20, item 11: the four cases.
        menu_declared: pickerMenu({ ...row, source: "declared" }),
        menu_one_switch: pickerMenu({
            ...row, source: "device", device_switches: [row.device_switches[0]],
        }),
    },
    newest: {
        mixed_spellings: newestSeen([
            { id: "z", last_seen: "2026-10-19T11:59:59.000Z" },
            { id: "offset", last_seen: "2026-10-19T12:00:00+00:00" },
            { id: "local", last_seen: "2026-10-19T13:59:58+02:00" },
        ])?.id,
        tie_keeps_first: newestSeen([
            { id: "a", last_seen: at(-5) }, { id: "b", last_seen: at(-5) },
        ])?.id,
        skips_garbage: newestSeen([
            { id: "bad", last_seen: "" }, { id: "good", last_seen: at(-60) },
        ])?.id,
        empty: newestSeen([]),
    },
    heard: (() => {
        const devices = [
            { id: "tv", last_seen: at(-5) },
            { id: "bar", last_seen: at(-900) },
        ];
        const tv = { id: "tv", signals: [
            { id: "power", last_seen: at(-5) },
            { id: "vol", last_seen: at(-200) },
        ] };
        const bar = { id: "bar", signals: [{ id: "input", last_seen: at(-900) }] };
        return {
            all_collapsed: lastHeardTarget(devices, null, null),
            newest_open: lastHeardTarget(devices, "tv", tv),
            other_open: lastHeardTarget(devices, "bar", bar),
            open_still_loading: lastHeardTarget(devices, "tv", null),
            open_with_no_signals: lastHeardTarget(devices, "tv", { id: "tv", signals: [] }),
            nothing_heard: lastHeardTarget([], null, null),
        };
    })(),
    arrival: {
        open: arrivalBloomKey("tv", "power", true),
        collapsed: arrivalBloomKey("tv", "power", false),
        open_without_signal: arrivalBloomKey("tv", "", true),
    },
    capture: {
        attribute_and_row: rxCaptureMatch({ capturing: false, friendly_name: "x" }, true),
        attribute_listening: rxCaptureMatch({ capturing: true }, true),
        attribute_only: rxCaptureMatch({ capturing: false }, false),
        row_only_unavailable: rxCaptureMatch(undefined, true),
        neither: rxCaptureMatch({ friendly_name: "Athom RX" }, false),
        no_state: rxCaptureMatch(undefined, false),
        not_a_boolean: rxCaptureMatch({ capturing: "yes" }, false),
    },
};
// The arrivals hub, against a fake api: one subscription for every
// chip, a delivery per receiver, closed with its last listener.
const fake = { subscribed: 0, closed: 0, cb: null };
const api = {
    subscribeUnknownSignals: async (cb) => {
        fake.subscribed += 1; fake.cb = cb;
        return async () => { fake.closed += 1; };
    },
};
const heard = { office: 0, office2: 0, living: 0 };
const stopOffice = onArrival(api, "infrared.office", () => heard.office++);
const stopOffice2 = onArrival(api, "infrared.office", () => heard.office2++);
const stopLiving = onArrival(api, "infrared.living", () => heard.living++);
await Promise.resolve();
fake.cb({ device_id: "d", receiver_entity_id: "infrared.office" });
fake.cb({ device_id: "d", receiver_entity_id: "infrared.office" });
fake.cb({ device_id: "d", receiver_entity_id: "infrared.athom" });
fake.cb({ device_id: "d", receiver_entity_id: null });
fake.cb({ device_id: "d" });
stopOffice();
fake.cb({ device_id: "d", receiver_entity_id: "infrared.office" });
stopOffice2();
stopLiving();
await new Promise((r) => setTimeout(r, 0));
out.arrivals = { heard, subscribed: fake.subscribed, closed: fake.closed };

// The capture card's glyph (owner, 2026-10-20), built as
// ir-device-list.ts's _captureGlyphState builds it: grey while no switch
// is resolved, gold once one is, ember offline whatever the switch.
const glyphOf = (states, r) => {
    const online = listenOnline(states, r);
    const state = {
        online,
        listening: online && listenLive(states, r).on,
        waiting: r.switch_entity_id === null,
    };
    const glyph = cardGlyph("online", state);
    const path = cardIconPath("capture", glyph);
    return { glyph, icon: path === CARD_ICONS.capture.solid ? "solid" : "outline" };
};
const up = { "infrared.r": { state: "on", attributes: { capturing: false } },
             "switch.ir": { state: "off", attributes: {} } };
const down = { "infrared.r": { state: "unavailable", attributes: {} } };
const noSwitch = { ...row, switch_entity_id: null, source: null };
const chosen = { ...row, switch_entity_id: "switch.ir", source: "user" };
out.glyph = {
    no_switch: glyphOf(up, noSwitch),
    after_a_choice: glyphOf(up, chosen),
    declared: glyphOf(up, { ...row, source: "declared" }),
    listening: glyphOf({ ...up, "infrared.r": rx({ capturing: true })["infrared.r"] }, chosen),
    offline_no_switch: glyphOf(down, noSwitch),
    offline_with_switch: glyphOf(down, chosen),
};

console.log(JSON.stringify(out));
""".replace("__NOW__", NOW)


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("listenjs")
    subprocess.run(
        [
            str(TSC), "src/ir-listen-state.ts", "src/ir-arrivals.ts",
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


def _src(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _en() -> dict:
    return json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))


def _block(source: str, start: str, end: str) -> str:
    tail = source[source.index(start):]
    return tail[: tail.index(end)]


# ---------------------------------------------------------------------------
# Run under node
# ---------------------------------------------------------------------------


class TestTheFill:
    """The fill is the receiver's own window, drawn from its deadline."""

    def test_it_starts_full_and_drains_to_the_deadline(self, run):
        assert run["fill"]["five_left"] == {
            "endsAt": "2026-10-19T12:00:05.000Z", "start": 1, "durationMs": 5000,
        }

    def test_a_deadline_already_past_is_an_empty_drain(self, run):
        assert run["fill"]["past"]["durationMs"] == 0

    def test_an_unbelievable_deadline_gives_no_fill(self, run):
        assert run["fill"]["garbage"] is None
        assert run["fill"]["clock_far_ahead"] is None


class TestTheChip:
    def test_it_follows_the_receivers_capturing(self, run):
        assert run["live"]["open"] == {"on": True, "endsAt": "2026-10-19T12:00:04.000Z"}
        assert run["live"]["open_without_deadline"] == {"on": True, "endsAt": None}
        assert run["live"]["closed_keeps_no_deadline"] == {"on": False, "endsAt": None}

    def test_never_the_switchs_state(self, run):
        assert run["live"]["a_switch_that_is_on_means_nothing"]["on"] is False

    def test_it_is_online_while_ha_reaches_the_receiver_and_its_switch(self, run):
        """Ember's rule (entity-health.ts): unavailable or missing is
        offline, unknown is online. Any chosen entity counts, not only a
        switch; with none chosen yet it is setup, not health."""
        assert run["online"] == {
            "both": True,
            "receiver_unknown": True,
            "receiver_unavailable": False,
            "switch_unavailable": False,
            "helper_chosen_missing": False,
            "no_switch_yet": True,
            "not_loaded": False,
        }

    def test_a_page_load_is_not_an_event(self, run):
        assert run["bloom"]["first_sight_on"] is False

    def test_it_blooms_on_open_and_on_a_new_deadline(self, run):
        assert run["bloom"]["opened"] is True
        assert run["bloom"]["new_deadline"] is True

    def test_nothing_else_in_the_state_blooms_it(self, run):
        assert run["bloom"]["plain_refresh"] is False
        assert run["bloom"]["closed"] is False

    def test_it_is_blocked_while_offline_or_without_a_switch(self, run):
        assert run["block"] == {
            "ready": None, "no_switch": "no_switch", "offline": "offline",
            "offline_without_switch": "offline",
        }

    def test_the_rows_are_reread_when_capture_devices_come_and_go(self, run):
        assert run["signature"]["some"] == "infrared.a,infrared.b"
        assert run["signature"]["window_opening_changes_nothing"] is True
        assert run["signature"]["none"] == ""


class TestListenPicksAReceiver:
    def test_capture_devices_are_marked_and_offline_ones_still_listed(self, run):
        """Their health is on their dot (ember, 2026-10-19), so the menu
        says what is down instead of hiding it."""
        assert run["choices"]["choices"] == [
            {"entityId": "infrared.office", "name": "Office RM mini", "capture": True},
            {"entityId": "infrared.living", "name": "Living Room RM4", "capture": True},
            {"entityId": "infrared.athom", "name": "Athom IR Proxy", "capture": False},
        ]

    def test_an_online_receiver_is_preferred(self, run):
        assert run["choices"]["last_used_offline"] == "infrared.living"
        assert run["choices"]["first_offline"] == "infrared.living"
        assert run["choices"]["all_offline"] == "infrared.living"

    def test_the_last_receiver_used_comes_back(self, run):
        assert run["choices"]["last_used"] == "infrared.athom"

    def test_otherwise_the_first(self, run):
        assert run["choices"]["last_used_gone"] == "infrared.office"
        assert run["choices"]["first_visit"] == "infrared.office"

    def test_with_only_bridges_there_is_no_receiver_to_name(self, run):
        assert run["choices"]["bridge_only"] is None


class TestThePicker:
    def test_choose_another_lists_switches_and_helpers_only(self, run):
        assert run["picker"]["all"] == [
            {"entityId": "input_boolean.learn", "name": "Alpha learn mode"},
            {"entityId": "switch.b_switch", "name": "Beta"},
            {"entityId": "switch.no_name", "name": "switch.no_name"},
        ]

    def test_it_searches_the_name_and_the_entity_id(self, run):
        assert [e["entityId"] for e in run["picker"]["by_name"]] == ["input_boolean.learn"]
        assert [e["entityId"] for e in run["picker"]["by_id"]] == ["switch.b_switch"]

    def test_the_menu_is_the_devices_switches_then_choose_another(self, run):
        """Nothing else: no Remove, no Always listening (owner)."""
        assert run["picker"]["menu"] == [
            {"kind": "switch", "entityId": "switch.ir", "name": "RM4 IR capture",
             "current": True},
            {"kind": "switch", "entityId": "switch.rf", "name": "RM4 RF capture",
             "current": False},
            {"kind": "other"},
        ]
        assert [i.get("current") for i in run["picker"]["menu_none_chosen"]] == [
            False, False, None,
        ]

    def test_the_four_menu_cases(self, run):
        """Item 11: every capture device has the caret, even with one option."""
        ir = {"kind": "switch", "entityId": "switch.ir", "name": "RM4 IR capture"}
        # Declares its switch (RM4 Pro, Mock A): that switch alone, checked;
        # the RF switch on the same device never appears.
        assert run["picker"]["menu_declared"] == [{**ir, "current": True}]
        # One switch, nothing declared (Mock C): picked, checked.
        assert run["picker"]["menu_one_switch"] == [{**ir, "current": True}, {"kind": "other"}]
        # Several, nothing declared (Mock B): all of them, none checked.
        assert [i.get("entityId") for i in run["picker"]["menu_none_chosen"]] == [
            "switch.ir", "switch.rf", None,
        ]
        assert not any(i.get("current") for i in run["picker"]["menu_none_chosen"])

    def test_a_choice_from_elsewhere_is_shown_as_current(self, run):
        first = run["picker"]["menu_helper_chosen"][0]
        assert first == {
            "kind": "switch", "entityId": "input_boolean.learn",
            "name": "Learn mode", "current": True,
        }
        assert len(run["picker"]["menu_helper_chosen"]) == 4

    def test_each_receivers_listeners_hear_only_its_codes(self, run):
        assert run["arrivals"]["heard"] == {"office": 2, "office2": 3, "living": 0}

    def test_one_subscription_for_every_chip_closed_with_the_last(self, run):
        assert run["arrivals"]["subscribed"] == 1
        assert run["arrivals"]["closed"] == 1


class TestLastHeard:
    def test_times_are_compared_as_times(self, run):
        assert run["newest"]["mixed_spellings"] == "offset"
        assert run["newest"]["tie_keeps_first"] == "a"
        assert run["newest"]["skips_garbage"] == "good"
        assert run["newest"]["empty"] is None

    def test_collapsed_it_is_the_newest_remotes_card(self, run):
        assert run["heard"]["all_collapsed"] == {"deviceId": "tv", "signalId": None}

    def test_open_it_moves_to_the_newest_signal_row(self, run):
        assert run["heard"]["newest_open"] == {"deviceId": None, "signalId": "power"}

    def test_opening_another_remote_does_not_move_it(self, run):
        assert run["heard"]["other_open"] == {"deviceId": "tv", "signalId": None}

    def test_it_stays_on_the_card_until_the_rows_are_there(self, run):
        assert run["heard"]["open_still_loading"] == {"deviceId": "tv", "signalId": None}
        assert run["heard"]["open_with_no_signals"] == {"deviceId": "tv", "signalId": None}

    def test_an_empty_sniffer_has_no_tint(self, run):
        assert run["heard"]["nothing_heard"] == {"deviceId": None, "signalId": None}


class TestTheReceiverCardMatch:
    def test_a_capture_device_gets_the_chip(self, run):
        assert run["capture"]["attribute_and_row"] == {"kind": "chip", "by": "attribute"}
        assert run["capture"]["attribute_listening"] == {"kind": "chip", "by": "attribute"}

    def test_before_its_row_arrives_it_gets_the_static_badge(self, run):
        assert run["capture"]["attribute_only"] == {"kind": "static", "by": "attribute"}

    def test_the_row_alone_covers_an_unavailable_receiver(self, run):
        """No attributes while unavailable; the remembered row decides."""
        assert run["capture"]["row_only_unavailable"] == {"kind": "chip", "by": "row"}

    def test_an_ordinary_receiver_is_left_alone(self, run):
        assert run["capture"]["neither"] == {"kind": None, "by": None}
        assert run["capture"]["no_state"] == {"kind": None, "by": None}
        assert run["capture"]["not_a_boolean"] == {"kind": None, "by": None}


class TestTheArrivalBloom:
    def test_it_lands_on_the_row_the_signal_belongs_to(self, run):
        assert run["arrival"]["open"] == "sig:power"
        assert run["arrival"]["collapsed"] == "dev:tv"
        assert run["arrival"]["open_without_signal"] == "dev:tv"


# ---------------------------------------------------------------------------
# Source wiring (runs everywhere)
# ---------------------------------------------------------------------------


class TestTheContractIsGeneric:
    def test_no_integration_is_named_in_the_listen_code(self):
        for name in (
            "ir-listen-state.ts", "ir-listen-chip.ts", "ir-listen-row.ts",
            "ir-arrivals.ts", "ir-capture-switch-menu.ts",
        ):
            code = re.sub(r"/\*.*?\*/|//[^\n]*", "", _src(name), flags=re.S)
            assert "broadsniff" not in code.lower(), name
        api = _src("api.ts")
        assert "broadsniff" not in api.lower()
        assert 'type: "hair/receivers/capture"' in api
        assert 'type: "hair/receivers/listen"' in api
        assert 'type: "hair/receivers/capture_switch"' in api
        assert 'type: "hair/receivers/hardware"' in api

    def test_the_chip_reads_the_receivers_own_attributes(self):
        state = _src("ir-listen-state.ts")
        assert "st?.attributes?.capturing === true" in state
        assert "st?.attributes?.window_ends_at" in state
        assert 'typeof receiverAttributes?.capturing === "boolean"' in state
        for gone in ("codes_entity_id", "window_entity_id", "mode_entity_id", "windowMs"):
            assert gone not in state

    def test_the_panel_row_shape_matches_the_server(self):
        from custom_components.hair import receiver_window

        source = Path(receiver_window.__file__).read_text(encoding="utf-8")
        rows = source[source.index("rows.append({"):]
        rows = rows[: rows.index("})")]
        server = set(re.findall(r'^            "(\w+)":', rows, re.M))
        block = re.search(
            r"export interface CaptureReceiverRow \{(.*?)\n\}", _src("types.ts"), re.S
        ).group(1)
        panel = set(re.findall(r"^\s*(\w+):", block, re.M))
        assert panel == server

    def test_the_error_codes_are_the_servers(self):
        types = _src("types.ts")
        assert f'RECEIVER_ARM_FAILED = "{ARM_FAILED_CODE}"' in types
        assert f'NO_CAPTURE_SWITCH = "{NO_CAPTURE_SWITCH_CODE}"' in types
        assert f'RECEIVER_UNAVAILABLE = "{RECEIVER_UNAVAILABLE_CODE}"' in types
        assert "BROADSNIFF_ARM_FAILED" not in types


class TestTheChipWiring:
    def test_the_row_is_there_only_with_capture_devices(self):
        monitor = _src("ir-signal-monitor.ts")
        assert re.search(
            r"this\._listenRows\.length > 0\s*\?\s*html`<ir-listen-row", monitor
        )
        assert "this._listenRows = await this.api.captureReceivers();" in monitor
        assert re.search(r"catch \{\s*this\._listenRows = \[\];", monitor)
        assert "if (this.rows.length === 0) return nothing;" in _src("ir-listen-row.ts")
        assert re.search(
            r"this\.rows\.map\(\s*\(row\) => html`<ir-listen-chip", _src("ir-listen-row.ts")
        )

    def test_the_rows_are_reread_on_registry_change_or_signature(self):
        monitor = _src("ir-signal-monitor.ts")
        assert re.search(
            r"before !== now\) \|\| sigMoved\)\s*\{\s*void this\._loadListenRows\(\);",
            monitor,
        )
        devlist = _src("ir-device-list.ts")
        assert re.search(
            r"this\.hass\?\.entities !== this\._listenRowsFor \|\| sig !== this\._listenRowsSig\)",
            devlist,
        )

    def test_the_fill_is_keyed_on_the_deadline_never_a_timer(self):
        chip = _src("ir-listen-chip.ts")
        assert re.search(r"keyed\(\s*fill\.endsAt,", chip)
        assert "planFill(now.endsAt, Date.now())" in chip
        for name in ("ir-listen-chip.ts", "ir-listen-row.ts", "ir-arrivals.ts"):
            assert "setTimeout" not in _src(name) and "setInterval" not in _src(name)
        assert "listenBlooms(before, now)" in chip

    def test_it_blooms_on_hairs_own_arrival(self):
        chip = _src("ir-listen-chip.ts")
        assert "onArrival(this.api, key, () => this._bloomChip())" in chip
        assert "this._arrivals?.stop();" in chip
        hub = _src("ir-arrivals.ts")
        assert "api.subscribeUnknownSignals((event) => deliver(hub, event))" in hub
        assert "const receiver = event.receiver_entity_id;" in hub
        # One subscription shared by every chip; closed with the last one.
        assert "if (hub.unsubscribe === null)" in hub
        assert "hub.listeners.size === 0 && hub.unsubscribe !== null" in hub

    def test_a_tap_goes_through_the_receiver_door(self):
        chip = _src("ir-listen-chip.ts")
        assert "await this.api.receiverListen(this.row.receiver_entity_id, !on);" in chip
        assert 'role=${waiting ? "button" : "switch"}' in chip

    def test_it_is_disabled_while_blocked(self):
        chip = _src("ir-listen-chip.ts")
        assert "const online = listenOnline(this.hass?.states, row);" in chip
        assert "const block = chipBlock(row, online);" in chip
        assert (
            'const disabled = this._busy || (this.compact ? block === "offline" : block !== null);'
        ) in chip
        assert "?disabled=${disabled}" in chip
        assert 't("listen.offline_title", { name: row.name })' in chip
        assert 't("listen.no_switch_title")' in chip
        # Waiting for a switch is setup: dimmed in the Sniffer, grey on the
        # card; offline is ember.
        assert '${block === "no_switch" && !this.compact ? "blocked" : ""}' in chip

    def test_gold_idle_green_listening(self):
        chip = _src("ir-listen-chip.ts")
        assert 'LISTEN_GOLD = "#f5a623"' in chip
        assert 'LISTEN_GREEN = "#43a047"' in chip
        tone = "const tone = waiting ? WAITING_TONE : live.on ? LISTEN_GREEN : LISTEN_GOLD;"
        assert tone in chip
        assert 'style="--tone:${tone}"' in chip

    def test_the_glyph_opens_the_receivers_device_page(self):
        chip = _src("ir-listen-chip.ts")
        assert re.search(r"\$\{this\.compact \|\| !row\.ha_device_id\s*\?\s*nothing", chip)
        assert re.search(
            r"renderExitToEntityBtn\(\s*`/config/devices/device/\$\{row\.ha_device_id\}`", chip
        )

    def test_the_glyph_sits_inside_the_pill(self):
        chip = _src("ir-listen-chip.ts")
        assert re.search(
            r"\.chip\.listen \.exit-to-entity-btn ha-svg-icon \{\s*--mdc-icon-size: 11px;", chip
        )
        assert "--mdc-icon-size: 14px;" in _src("ir-icons.ts")

    def test_the_label_sits_hard_left(self):
        row = _src("ir-listen-row.ts")
        assert "labelWidth" not in row
        assert re.search(r"\.listen-label \{\s*width: auto;\s*text-align: left;", row)

    def test_no_listen_component_keeps_browser_storage(self):
        for name in (
            "ir-signal-monitor.ts", "ir-listen-row.ts", "ir-listen-chip.ts",
            "ir-listen-state.ts", "ir-arrivals.ts", "ir-capture-switch-menu.ts",
        ):
            assert "localStorage" not in _src(name), name


class TestTheReceiverCard:
    def test_the_card_shows_one_split_chip(self):
        """Owner ruling 2026-10-20: the separate switch pill is gone."""
        devlist = _src("ir-device-list.ts")
        badge = _block(devlist, "private _renderNativeBadge", "/** Render TX/RX-NATIVE")
        chip = badge.index("<ir-listen-chip")
        assert chip < badge.index('class="badge rx-capture ${online ? "" : "offline"}"')
        assert re.search(r"<ir-listen-chip\s+compact\s+\.hass=", badge)
        assert "@capture-switch-changed=${() => void this._loadListenRows()}" in badge
        for name in ("ir-device-list.ts", "ir-listen-chip.ts", "ir-capture-switch-menu.ts"):
            assert "ir-capture-switch-pill" not in _src(name), name
        assert not (SRC / "ir-capture-switch-pill.ts").exists()

    def test_rx_capture_replaces_rx_native_and_native_cards_get_no_caret(self):
        devlist = _src("ir-device-list.ts")
        badge = _block(devlist, "private _renderNativeBadge", "/** Render TX/RX-NATIVE")
        native = badge.index('class="badge rx-native ${online ? "" : "offline"}"')
        assert badge.index("<ir-listen-chip") < native
        assert badge.count("<ir-listen-chip") == 1
        assert badge.count("return html`") == 3
        # Proxies and Receivers cards share the badge renderer.
        assert devlist.count("${this._renderRxBadges(entry)}") >= 2

    def test_the_match_is_by_receiver_then_device(self):
        devlist = _src("ir-device-list.ts")
        assert (
            "this._listenRows.find((r) => r.receiver_entity_id === entry.native_entity_id)"
            in devlist
        )
        assert "rxCaptureMatch(attributes, row !== undefined)" in devlist

    def test_a_remembered_receiver_not_loaded_keeps_its_card(self):
        devlist = _src("ir-device-list.ts")
        classify = _block(devlist, "private _classifyHardware", "const merged = Array.from")
        assert "for (const row of this._listenRows)" in classify
        assert "if (shown.has(row.receiver_entity_id)) continue;" in classify

    def test_the_proxy_card_keeps_its_pair_and_the_receivers_card_the_finger(self):
        # Ember's icon pairs (card-icons.ts): a capture device draws the
        # finger online and record-circle-outline offline.
        devlist = _src("ir-device-list.ts")
        assert re.search(
            r"\.path=\$\{cardIconPath\(\s*this\._rxCapture\(entry\)\.kind !== null\s*"
            r"\?\s*\"capture\"\s*:\s*\"receiver\",\s*glyph,?\s*\)\}",
            devlist,
        )
        assert '<ha-svg-icon .path=${cardIconPath("proxy", glyph)}></ha-svg-icon>' in devlist

    def test_the_hardware_list_is_renamed(self):
        devlist = _src("ir-device-list.ts")
        assert "this._receiverHardware = await this.api.listReceiverHardware();" in devlist
        assert "CaptureProviderInfo" not in devlist and "listCaptureProviders" not in devlist

    def test_the_broadlink_hint_stays(self):
        devlist = _src("ir-device-list.ts")
        assert '!components.includes("broadsniff")' in devlist
        assert 'BROADSNIFF_URL = "https://github.com/DAB-LABS/broadsniff"' in _src("types.ts")


class TestTheCaptureGlyph:
    """Owner, 2026-10-20: grey with no switch, gold once one resolves."""

    def test_grey_with_no_switch_then_gold_after_a_choice(self, run):
        assert run["glyph"]["no_switch"] == {"glyph": "waiting", "icon": "solid"}
        assert run["glyph"]["after_a_choice"] == {"glyph": "ready", "icon": "solid"}
        assert run["glyph"]["declared"] == {"glyph": "ready", "icon": "solid"}
        assert run["glyph"]["listening"] == {"glyph": "listening", "icon": "solid"}

    def test_offline_is_ember_whatever_the_switch(self, run):
        for case in ("offline_no_switch", "offline_with_switch"):
            assert run["glyph"][case] == {"glyph": "offline", "icon": "outline"}, case

    def test_the_card_passes_waiting_and_draws_it_grey(self):
        devlist = _src("ir-device-list.ts")
        state = _block(devlist, "private _captureGlyphState(", "private _renderOfflineCorner")
        assert "waiting: capture.row.switch_entity_id === null," in state
        assert re.search(
            r"\.hw-card\.hw-glyph-waiting \.card-header ha-svg-icon \{\s*"
            r"color: var\(--secondary-text-color\);",
            devlist,
        )
        health = _src("entity-health.ts")
        assert "if (capture.waiting) return \"waiting\";" in health


class TestTheSplitChip:
    """Owner ruling 2026-10-20, items 9 to 14: RX-CAPTURE is one split chip."""

    def _chip(self):
        return _src("ir-listen-chip.ts")

    def _compact(self):
        render = _block(self._chip(), "    render() {", "    static styles")
        return render.split("if (!this.compact) return chip;", 1)[1]

    def test_the_main_part_captures_and_the_caret_is_the_menu(self):
        compact = self._compact()
        assert '<span\n                class="split ' in compact
        assert compact.index("${chip}") < compact.index("<ir-capture-switch-menu")
        chip = self._chip()
        assert "@click=${() => this._onMain(live.on, waiting)}" in chip
        main = _block(chip, "private _onMain(", "private _switchName(")
        assert "if (waiting) {" in main
        assert "void this._toggle(on);" in main
        menu = _src("ir-capture-switch-menu.ts")
        caret = _block(menu, "    render() {", "private _renderMenu")
        assert '<button\n                    class="caret-btn' in caret
        assert "@click=${this._toggleMenu}" in caret
        assert 'aria-label=${t("capswitch.choose")}' in caret
        assert 'aria-haspopup="menu"' in caret

    def test_the_caret_is_a_thumb_wide_focus_stop_behind_a_divider(self):
        """Owner bench 2026-10-21: small to look at, 24 by 24px to hit."""
        menu = _src("ir-capture-switch-menu.ts")
        rule = re.search(r"\n            \.caret-btn \{([^}]*)\}", menu).group(1)
        assert "padding: 0 2px;" in rule and "position: relative;" in rule
        assert "min-width" not in rule
        hit = re.search(r"\n            \.caret-btn::before \{([^}]*)\}", menu).group(1)
        for prop in ('content: "";', "position: absolute;", "width: 24px;", "height: 24px;",
                     "transform: translate(-50%, -50%);"):
            assert prop in hit, prop
        assert "background" not in hit
        assert "border-left: 1px solid" in rule
        assert "color: var(--split-fg" in rule and "background: var(--split-bg" in rule
        # Two buttons, so two focus stops: the chip's toggle and the caret.
        assert "tabindex" not in _block(menu, "    render() {", "private _renderMenu")

    def test_nothing_picked_is_grey_and_a_click_opens_the_menu(self):
        chip = self._chip()
        assert 'const WAITING_TONE = "var(--secondary-text-color)";' in chip
        assert 'const waiting = this.compact && block === "no_switch";' in chip
        main = _block(chip, "private _onMain(", "private _switchName(")
        opens = 'menu?.open(this.renderRoot.querySelector<HTMLElement>(".split") ?? undefined);'
        assert opens in main
        assert 'aria-haspopup=${ifDefined(waiting ? "menu" : undefined)}' in chip
        # Not disabled on the card while waiting; only offline is.
        assert 'this.compact ? block === "offline" : block !== null' in chip

    def test_offline_disables_both_parts(self):
        chip = self._chip()
        assert "?disabled=${!online}" in self._compact()
        assert re.search(
            r"\.split\.offline \{\s*--split-fg: \$\{EMBER_VAR\};\s*"
            r"--split-bg: color-mix\(in srgb, \$\{EMBER_VAR\} 13%, transparent\);",
            chip,
        )
        menu = _src("ir-capture-switch-menu.ts")
        assert "?disabled=${this.disabled || this._busy}" in menu
        opener = _block(menu, "public open(", "private _toggleMenu")
        assert "if (this.disabled || this._menu) return;" in opener

    def test_the_tooltip_names_the_switch_and_its_source(self):
        chip = self._chip()
        line = 'current ? t("listen.capture_with", { name: this._switchName(current) }) : "",'
        assert line in chip
        assert "current && row.source ? t(SOURCE_KEYS[row.source]) : \"\"," in chip
        assert 'declared: "capswitch.source_declared"' in chip
        assert _en()["listen.capture_with"] == "Capture with {name}"

    def test_the_sniffer_chip_is_unchanged(self):
        """Item 15: the split is the compact form only."""
        chip = self._chip()
        assert "if (!this.compact) return chip;" in chip
        sniffer = _block(chip, "const chip = html`", "if (!this.compact)")
        assert "<ir-capture-switch-menu" not in sniffer

    def test_it_stops_click_and_keydown(self):
        menu = _src("ir-capture-switch-menu.ts")
        assert '<span class="wrap" @click=${this._stop} @keydown=${this._onKey}>' in menu
        assert "e.stopPropagation();" in _block(menu, "private _onKey", "render()")
        assert "@click=${this._stop}\n                @keydown=${this._stop}" in self._compact()

    def test_choose_another_is_the_house_search_not_has_pickers(self):
        pill = _src("ir-capture-switch-menu.ts")
        assert "ha-entity-picker" not in re.sub(r"/\*.*?\*/", "", pill, flags=re.S)
        assert "<ha-textfield" not in pill
        assert re.search(r'<input\s+class="pick-search"\s+type="text"', pill)
        assert "pickerEntities(this.hass?.states, this._query)" in pill
        result = _block(pill, 'class="result ', "</button>")
        assert '<span class="iname">${e.name}</span>' in result
        assert '<span class="iid">${e.entityId}</span>' in result
        assert "${this._dot(e.entityId)}" in result

    def test_choosing_saves_through_the_door(self):
        pill = _src("ir-capture-switch-menu.ts")
        assert "await this.api.setCaptureSwitch(this.row.receiver_entity_id, entityId);" in pill
        assert '"capture-switch-changed"' in pill
        # The declared switch, picked again, changes nothing.
        pick = _block(pill, "private async _pickFromMenu", "private _openPicker")
        assert "if (entityId !== this.row.switch_entity_id) await this._choose(entityId);" in pick

    def test_no_remove_and_no_always_listening(self):
        pill = _src("ir-capture-switch-menu.ts")
        menu = _block(pill, "private _renderMenu", "private _renderPicker")
        assert "remove" not in menu.lower()
        assert "always" not in menu.lower()
        assert 't("capswitch.choose_other")' in menu
        assert '<svg class="check"' in menu


class TestHealthUsesEmbersPieces:
    """Owner, 2026-10-19: the unavailable capture device, the receiver
    menu and the switch picker use Ember's shared dot classes and colour
    tokens, never a colour of their own."""

    LITERAL = re.compile(r"#e65100|230,\s*81,\s*0|#6cbf78|108,\s*191,\s*120|#f5a623|#8a8f94", re.I)

    def test_the_switch_menu_shows_health(self):
        pill = _src("ir-capture-switch-menu.ts")
        assert "healthDotStyles," in pill
        assert 'class="dot ${healthDotClass(this._online(entityId))}"' in pill
        assert "isEntityOnline(this.hass?.states, entityId)" in pill
        menu = _block(pill, "private _renderMenu", "private _renderPicker")
        assert "${this._dot(item.entityId!)}" in menu

    def test_the_receiver_menu_dots_are_health(self):
        editor = _src("ir-signal-editor.ts")
        assert 'class="dot rx-dot ${healthDotClass(this._rxOnline(entityId))}"' in editor
        split = _block(editor, "private _renderListenSplit", "private _renderTangleStatus")
        assert split.count("this._rxDot(") == 2
        assert "--tone" not in split
        assert "TONE_CAPTURE" not in editor and "TONE_ALWAYS" not in editor
        assert "        healthDotStyles,\n    ];" in editor
        assert "isEntityOnline(this.hass?.states, entityId)" in editor

    def test_the_offline_chip_is_embers(self):
        chip = _src("ir-listen-chip.ts")
        assert "const online = listenOnline(this.hass?.states, row);" in chip
        assert "unavailable_title" not in chip
        for path in (SRC / "locales").glob("*.json"):
            keys = json.loads(path.read_text(encoding="utf-8"))
            assert "listen.unavailable_title" not in keys, path.name

    def test_no_colour_literals_in_round_three_code(self):
        for name in ("ir-capture-switch-menu.ts", "ir-listen-state.ts", "ir-arrivals.ts"):
            assert not self.LITERAL.search(_src(name)), name
        split = _block(_src("ir-signal-editor.ts"), "private _renderListenSplit",
                       "private _renderTangleStatus")
        assert not self.LITERAL.search(split)


class TestTheEditor:
    def test_listen_precedes_the_code_box_in_the_command_editor(self):
        editor = _src("ir-signal-editor.ts")
        assert re.search(
            r"this\._isCommand\s*\?\s*html`\$\{this\._renderReplace\(\)\} "
            r"\$\{this\._renderCodeBox\(\)\}`",
            editor,
        )

    def test_the_repairs_order_is_unchanged(self):
        editor = _src("ir-signal-editor.ts")
        assert re.search(
            r"\$\{this\._renderTangleIntro\(\)\}\s*\$\{this\._renderTangleStatus\(\)\} "
            r"\$\{this\._renderCodeBox\(\)\}",
            editor,
        )
        footer = _block(editor, '<div class="dialog-actions">', "</ha-dialog>")
        assert footer.index("${this._renderTangleListenButton()}") < footer.index('class="spacer"')

    def test_the_label_hint_and_placeholder(self):
        en = _en()
        assert en["editor.pronto_code"] == "Code: Pronto, Broadlink or Tuya (saved as Pronto)"
        assert en["editor.code_placeholder"] == "0000 006D ... or a Broadlink or Tuya base64 code"
        assert en["editor.replace_hint"] == (
            "Point the remote at a receiver and listen, or paste a code below."
        )
        editor = _src("ir-signal-editor.ts")
        assert 'placeholder=${t("editor.code_placeholder")}' in editor
        assert 'placeholder="0000 006D ..."' not in editor

    def test_listen_is_split_with_its_receiver_in_both_places(self):
        editor = _src("ir-signal-editor.ts")
        replace = _block(editor, "private _renderReplace", "private _renderRepeatNotice")
        assert 'this._renderListenSplit(\n                        "down",' in replace
        tangle = _block(editor, "private _renderTangleListenButton", "private _renderDrain")
        assert 'this._renderListenSplit(\n            "up",' in tangle
        split = _block(editor, "private _renderListenSplit", "private _renderTangleStatus")
        assert "if (!current) return button;" in split
        assert 't("listen.opens_window")' in split and 't("listen.always")' in split

    def test_each_listen_names_its_receiver(self):
        editor = _src("ir-signal-editor.ts")
        assert "}, this._rxActive ?? undefined);" in editor
        assert re.search(
            r"this\.tangleTarget as string,\s*this\._rxActive \?\? undefined,", editor
        )
        api = _src("api.ts")
        spread = "...(receiverEntityId ? { receiver_entity_id: receiverEntityId } : {}),"
        assert api.count(spread) == 2

    def test_the_last_receiver_is_remembered_safely(self):
        editor = _src("ir-signal-editor.ts")
        read = _block(editor, "function readLastReceiver", "function writeLastReceiver")
        write = _block(editor, "function writeLastReceiver", "@customElement")
        for body in (read, write):
            assert "try {" in body and "catch" in body
        assert 'LAST_RECEIVER_KEY = "hair.listen.receiver"' in _src("ir-listen-state.ts")

    def test_the_drain_comes_from_the_receivers_deadline(self):
        editor = _src("ir-signal-editor.ts")
        will = _block(editor, "protected willUpdate", "private _receiverError")
        assert "st?.attributes?.capturing === true ? st.attributes.window_ends_at : null" in will
        assert "planFill(ends, Date.now())" in will
        assert "keyed(\n            d.endsAt," in editor

    def test_a_refused_window_is_said_in_the_users_words(self):
        editor = _src("ir-signal-editor.ts")
        assert (
            'if (code === RECEIVER_ARM_FAILED) return t("listen.arm_failed", { name });'
            in editor
        )
        assert 'event.type === "receiver_arm_failed"' in editor

    def test_the_fix_footer_wraps_on_a_phone(self):
        editor = _src("ir-signal-editor.ts")
        assert re.search(
            r"@media \(max-width: 500px\) \{\s*\.dialog-actions \.split \{\s*flex: 1 0 100%;",
            editor,
        )

    def test_the_device_page_gives_the_editor_hass(self):
        detail = _src("ir-device-detail.ts")
        editor = _block(detail, "<ir-signal-editor", "</ir-signal-editor>")
        assert ".hass=${this.hass}" in editor


class TestTheLearnDialogIsGone:
    def test_the_dialog_and_its_wiring_are_gone(self):
        assert not (SRC / "ir-capture-dialog.ts").exists()
        for name in ("ir-device-detail.ts", "api.ts", "types.ts"):
            src = _src(name)
            for gone in (
                "ir-capture-dialog", "_captureName", "startCapture", "cancelCapture",
                "saveCapturedCommand", "CaptureEvent", "CaptureStartResponse",
            ):
                assert not re.search(rf"\b{gone}\b", src), (name, gone)
        add = _src("ir-add-controlled-device-dialog.ts")
        assert "capture_device_id" not in add and "capture_provider_type" not in add

    def test_its_doors_are_unregistered(self):
        ws = (COMPONENT / "websocket_api.py").read_text(encoding="utf-8")
        for gone in ("/capture/start", "/capture/cancel", "/capture/save", "/capture/providers",
                     "/broadsniff/"):
            assert gone not in ws, gone
        for gone in ("capture.py", "capture_orchestrator.py", "broadsniff.py"):
            assert not (COMPONENT / gone).exists(), gone

    def test_it_is_gone_from_the_bundle(self):
        dist = (FRONTEND / "dist" / "ha-panel-ir-devices.js").read_text(encoding="utf-8")
        assert "ir-capture-dialog" not in dist
        assert "ir-capture-switch-menu" in dist
        assert "ir-capture-switch-pill" not in dist

    def test_its_strings_are_gone_from_every_dictionary(self):
        for path in (SRC / "locales").glob("*.json"):
            keys = json.loads(path.read_text(encoding="utf-8"))
            assert not [k for k in keys if k.startswith("capture.")], path.name


class TestTheStrings:
    NEW = (
        "editor.code_placeholder", "editor.listen_on",
        "listen.arm_failed", "listen.no_switch_error",
        "listen.no_switch_title", "listen.pick_receiver", "listen.opens_window", "listen.always",
        "capswitch.choose", "capswitch.choose_title", "capswitch.choose_other",
        "capswitch.source_declared", "capswitch.source_user", "capswitch.source_device",
        "capswitch.dialog_title", "capswitch.dialog_intro", "capswitch.search_placeholder",
        "capswitch.no_match", "capswitch.save_failed",
    )

    def test_every_new_key_is_in_every_dictionary(self):
        for path in (SRC / "locales").glob("*.json"):
            keys = json.loads(path.read_text(encoding="utf-8"))
            for key in self.NEW:
                assert key in keys, (path.name, key)

    def test_the_wording_the_owner_asked_for(self):
        en = _en()
        assert en["listen.arm_failed"] == "{name} could not start listening."
        assert en["capswitch.source_declared"] == "Set by the integration"
        assert en["capswitch.source_user"] == "Chosen by you"
        assert en["capswitch.source_device"] == "Found on this device"
        assert en["capswitch.choose_other"] == "Choose another..."
        assert en["listen.opens_window"] == "Opens its capture window"
        assert en["listen.always"] == "Always listening"

    def test_no_em_dashes(self):
        for path in (SRC / "locales").glob("*.json"):
            keys = json.loads(path.read_text(encoding="utf-8"))
            for key in (*self.NEW, "editor.pronto_code", "editor.replace_hint"):
                assert "\u2014" not in keys[key], (path.name, key)

    def test_every_key_the_new_code_asks_for_exists(self):
        en = _en()
        for name in (
            "ir-listen-row.ts", "ir-listen-chip.ts", "ir-capture-switch-menu.ts",
            "ir-device-list.ts", "ir-signal-editor.ts",
        ):
            for key in re.findall(
                r'\bt\("((?:listen|capswitch|devlist|editor)\.[\w.]+)"', _src(name)
            ):
                assert key in en, (name, key)
