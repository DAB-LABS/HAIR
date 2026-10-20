"""The panel side of BroadSniff Listen: the Listen row and the Sniffer.

The decisions that matter here are timing and placement: when a Listen
chip blooms, how much of a window its fill shows, which one row carries
the "last heard" stroke, and which row an arriving signal blooms. Those
live as plain functions in ``ir-listen-state.ts``, and this module
transpiles that file with the repo's own TypeScript and runs them under
node, the way ``test_landed_notice_js.py`` does for its helpers.

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

from custom_components.hair.broadsniff import ARM_FAILED_CODE

from .test_broadsniff_listen import (
    _Hass,
    _receivers_and_tracking,
    _registry,
    _registry_entries,
)

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

NOW = "2026-10-17T12:00:00.000Z"

DRIVER = """
import {
    arrivalBloomKey, lastHeardTarget, listenBlooms, listenLive, newestSeen,
    planFill, rxCaptureMatch, windowMs,
} from "./ir-listen-state.js";

const NOW = Date.parse("__NOW__");
const at = (s) => new Date(NOW + s * 1000).toISOString();
const live = (on, endsAt, codes) => ({ on, endsAt, codes });

const row = {
    receiver_entity_id: "infrared.r", switch_entity_id: "switch.s",
    mode_entity_id: null, window_entity_id: "number.w",
    codes_entity_id: "sensor.c", ha_device_id: "dev", name: "RM4",
};
const bare = { ...row, window_entity_id: null, codes_entity_id: null };

const out = {
    fill: {
        half_left: planFill(at(5), 10000, NOW),
        all_left: planFill(at(10), 10000, NOW),
        clock_ahead: planFill(at(40), 10000, NOW),
        clock_slightly_ahead: planFill(at(11), 10000, NOW),
        past: planFill(at(-3), 10000, NOW),
        garbage: planFill("not a time", 10000, NOW),
    },
    window: {
        set: windowMs({ "number.w": { state: "30" } }, row),
        unknown: windowMs({ "number.w": { state: "unknown" } }, row),
        no_entity: windowMs({}, bare),
    },
    live: {
        on: listenLive({ "switch.s": { state: "on", attributes: { window_ends_at: at(4) } },
                         "sensor.c": { state: "3" } }, row),
        off_keeps_no_deadline: listenLive({
            "switch.s": { state: "off", attributes: { window_ends_at: at(4) } },
            "sensor.c": { state: "unavailable" },
        }, row),
        missing: listenLive({}, bare),
    },
    bloom: {
        first_sight_on: listenBlooms(undefined, live(true, at(9), 0)),
        opened: listenBlooms(live(false, null, 0), live(true, at(10), 0)),
        sliding_restart: listenBlooms(live(true, at(3), 1), live(true, at(10), 2)),
        multiple_code_same_deadline: listenBlooms(live(true, at(6), 1), live(true, at(6), 2)),
        single_code_as_it_closes: listenBlooms(live(true, at(6), 0), live(false, null, 1)),
        plain_refresh: listenBlooms(live(true, at(6), 1), live(true, at(6), 1)),
        closed_empty: listenBlooms(live(true, at(1), 1), live(false, null, 1)),
        count_reset_by_restart: listenBlooms(live(false, null, 7), live(false, null, 0)),
        unreadable_count: listenBlooms(live(true, at(6), null), live(true, at(6), 4)),
    },
    newest: {
        mixed_spellings: newestSeen([
            { id: "z", last_seen: "2026-10-17T11:59:59.000Z" },
            { id: "offset", last_seen: "2026-10-17T12:00:00+00:00" },
            { id: "local", last_seen: "2026-10-17T13:59:58+02:00" },
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
        row_only: rxCaptureMatch(undefined, true),
        neither: rxCaptureMatch({ friendly_name: "Athom RX" }, false),
        no_state: rxCaptureMatch(undefined, false),
        not_a_boolean: rxCaptureMatch({ capturing: "yes" }, false),
    },
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
            str(TSC), "src/ir-listen-state.ts",
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


# ---------------------------------------------------------------------------
# Run under node
# ---------------------------------------------------------------------------


class TestTheFill:
    """The fill is BroadSniff's window, drawn from its own deadline."""

    def test_it_starts_at_what_is_left_of_the_window(self, run):
        assert run["fill"]["half_left"] == {
            "endsAt": "2026-10-17T12:00:05.000Z", "start": 0.5, "durationMs": 5000,
        }
        assert run["fill"]["all_left"]["start"] == 1

    def test_a_browser_clock_behind_the_server_starts_it_full(self, run):
        assert run["fill"]["clock_ahead"]["start"] == 1
        assert run["fill"]["clock_ahead"]["durationMs"] == 10000
        # Within the slack the drain is capped at the window, not refused.
        assert run["fill"]["clock_slightly_ahead"]["start"] == 1

    def test_a_deadline_already_past_is_empty(self, run):
        assert run["fill"]["past"]["start"] == 0
        assert run["fill"]["past"]["durationMs"] == 0

    def test_an_unreadable_deadline_does_not_break_it(self, run):
        assert run["fill"]["garbage"]["start"] == 1

    def test_the_window_length_is_broadsniffs(self, run):
        assert run["window"]["set"] == 30000
        assert run["window"]["unknown"] == 10000
        assert run["window"]["no_entity"] == 10000


class TestTheChip:
    def test_it_follows_the_real_switch(self, run):
        assert run["live"]["on"] == {
            "on": True, "endsAt": "2026-10-17T12:00:04.000Z", "codes": 3,
        }
        assert run["live"]["off_keeps_no_deadline"] == {
            "on": False, "endsAt": None, "codes": None,
        }
        assert run["live"]["missing"] == {"on": False, "endsAt": None, "codes": None}

    def test_a_page_load_is_not_an_event(self, run):
        assert run["bloom"]["first_sight_on"] is False

    def test_it_blooms_on_start_and_on_every_restart(self, run):
        assert run["bloom"]["opened"] is True
        assert run["bloom"]["sliding_restart"] is True

    def test_multiple_mode_blooms_on_each_code_while_it_drains(self, run):
        """Owner ruling 2026-10-17: the deadline never moves in
        ``multiple``, so the code count is what blooms it."""
        assert run["bloom"]["multiple_code_same_deadline"] is True

    def test_single_mode_blooms_on_its_code_as_it_goes_gold(self, run):
        """Owner, 2026-10-17: "it's heard, it glows, and then it goes
        yellow". The code and the close can land in one update."""
        assert run["bloom"]["single_code_as_it_closes"] is True

    def test_nothing_else_blooms_it(self, run):
        assert run["bloom"]["plain_refresh"] is False
        assert run["bloom"]["closed_empty"] is False
        assert run["bloom"]["count_reset_by_restart"] is False
        assert run["bloom"]["unreadable_count"] is False


class TestLastHeard:
    def test_times_are_compared_as_times(self, run):
        # 13:59:58+02:00 is 11:59:58Z: the +00:00 spelling is newest.
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
    """Round 2: which hardware cards say RX-CAPTURE, and whether as the
    Listen chip or as a static badge."""

    def test_a_broadsniff_receiver_gets_the_chip_keyed_on_its_attribute(self, run):
        assert run["capture"]["attribute_and_row"] == {"kind": "chip", "by": "attribute"}
        assert run["capture"]["attribute_listening"] == {"kind": "chip", "by": "attribute"}

    def test_a_windowed_receiver_hair_cannot_open_gets_the_static_badge(self, run):
        assert run["capture"]["attribute_only"] == {"kind": "static", "by": "attribute"}

    def test_the_row_alone_covers_a_receiver_whose_state_has_not_arrived(self, run):
        assert run["capture"]["row_only"] == {"kind": "chip", "by": "row"}

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


class TestTheListenRowWiring:
    def test_the_row_is_there_only_with_broadsniff_remotes(self):
        monitor = _src("ir-signal-monitor.ts")
        assert re.search(
            r"this\._listenRows\.length > 0\s*\?\s*html`<ir-listen-row", monitor
        )
        assert "this._listenRows = await this.api.broadsniffReceivers();" in monitor
        # A failed read leaves the row out rather than breaking the Sniffer.
        assert re.search(
            r"catch \{\s*this\._listenRows = \[\];", monitor
        )
        assert "if (this.rows.length === 0) return nothing;" in _src("ir-listen-row.ts")
        # One chip element per remote, the same element the Devices card uses.
        assert re.search(
            r"this\.rows\.map\(\s*\(row\) => html`<ir-listen-chip", _src("ir-listen-row.ts")
        )

    def test_the_rows_are_reread_when_the_registry_changes(self):
        monitor = _src("ir-signal-monitor.ts")
        assert re.search(
            r'changed\.get\("hass"\) as any\)\?\.entities;.*?before !== now\)\s*\{\s*'
            r"void this\._loadListenRows\(\);",
            monitor, re.S,
        )

    def test_the_fill_is_keyed_on_broadsniffs_deadline_never_a_timer(self):
        chip = _src("ir-listen-chip.ts")
        assert re.search(r"keyed\(\s*fill\.endsAt,", chip)
        assert "attributes?.window_ends_at" in _src("ir-listen-state.ts")
        for name in ("ir-listen-chip.ts", "ir-listen-row.ts"):
            assert "setTimeout" not in _src(name) and "setInterval" not in _src(name)
        assert "listenBlooms(before, now)" in chip

    def test_a_tap_toggles_the_real_switch(self):
        chip = _src("ir-listen-chip.ts")
        assert "await this.api.broadsniffListen(this.row.receiver_entity_id, !on);" in chip
        assert 'role="switch"' in chip
        api = _src("api.ts")
        assert 'type: "hair/broadsniff/listen"' in api
        assert 'type: "hair/broadsniff/receivers"' in api

    def test_gold_idle_green_listening(self):
        chip = _src("ir-listen-chip.ts")
        assert 'LISTEN_GOLD = "#f5a623"' in chip
        assert 'LISTEN_GREEN = "#43a047"' in chip
        assert "--tone:${live.on ? LISTEN_GREEN : LISTEN_GOLD}" in chip

    def test_the_glyph_opens_the_broadsniff_device_page(self):
        assert re.search(
            r"renderExitToEntityBtn\(\s*`/config/devices/device/\$\{row\.ha_device_id\}`",
            _src("ir-listen-chip.ts"),
        )

    def test_the_glyph_sits_inside_the_pill(self):
        """Round 2: the chip's text size, secondary colour, brighter on
        hover, and only inside the Listen chip."""
        chip = _src("ir-listen-chip.ts")
        assert re.search(
            r"\.chip\.listen \.exit-to-entity-btn ha-svg-icon \{\s*--mdc-icon-size: 11px;", chip
        )
        assert re.search(
            r"\.chip\.listen \.exit-to-entity-btn \{[^}]*color: var\(--secondary-text-color\);",
            chip,
        )
        assert re.search(
            r"\.chip\.listen \.exit-to-entity-btn:hover \{"
            r"[^}]*color: var\(--primary-text-color\);",
            chip,
        )
        # The shared button elsewhere keeps its own size.
        assert "--mdc-icon-size: 14px;" in _src("ir-icons.ts")

    def test_the_label_sits_hard_left(self):
        """Round 2: no shared label column on the Sniffer."""
        row = _src("ir-listen-row.ts")
        assert "labelWidth" not in row
        assert 'class="hdr-row-label listen-label"' in row
        assert re.search(r"\.listen-label \{\s*width: auto;\s*text-align: left;", row)

    def test_the_row_looks_like_the_header_chip_group(self):
        assert "headerChipStyles" in _src("ir-listen-row.ts")
        assert "headerChipStyles" in _src("ir-listen-chip.ts")
        assert "static styles = headerChipStyles;" in _src("ir-header-chip-group.ts")

    def test_the_panel_row_shape_matches_the_server(self):
        with _registry(_registry_entries()), _receivers_and_tracking():
            from custom_components.hair.broadsniff import list_broadsniff_receivers

            server = set(list_broadsniff_receivers(_Hass())[0])
        block = re.search(
            r"export interface BroadSniffReceiverRow \{(.*?)\}", _src("types.ts"), re.S
        ).group(1)
        panel = set(re.findall(r"^\s*(\w+):", block, re.M))
        assert panel == server


class TestTheSnifferWiring:
    def test_the_header_flash_is_gone(self):
        monitor = _src("ir-signal-monitor.ts")
        for gone in ("_flashIds", "flash-row", "@keyframes row-flash"):
            assert gone not in monitor

    def test_arrival_blooms_the_row_in_blue(self):
        monitor = _src("ir-signal-monitor.ts")
        assert "this._bloomRow(arrivalBloomKey(ev.device_id, ev.signal_id, open));" in monitor
        assert re.search(
            r"\.device-row\.bloom,\s*\.signal-row\.bloom \{\s*"
            r"--bloom-rgb: 3, 169, 244;\s*--bloom-peak: #03a9f4;\s*--bloom-edge: #4fc3f7;",
            monitor,
        )
        assert 'class="signal-row ${blooming ? "bloom" : ""}' in monitor
        assert "this._bloomed.has(`sig:${sig.id}`)" in monitor
        assert "this._bloomed.has(`dev:${d.id}`)" in monitor

    def test_the_assign_glow_stays_on_top(self):
        monitor = _src("ir-signal-monitor.ts")
        assert "this._glowSignalIds = new Set([...this._glowSignalIds, ev.signal_id]);" in monitor

    def test_last_heard_is_derived_from_stored_last_seen(self):
        monitor = _src("ir-signal-monitor.ts")
        assert (
            "this._heard = lastHeardTarget(this._devices, this._expandedId, "
            "this._expandedDevice);" in monitor
        )
        # Worked out before every render, never stored or persisted.
        assert re.search(r"protected willUpdate\(.*?this\._heard = lastHeardTarget", monitor, re.S)
        # The class goes on the one row lastHeardTarget names and on no
        # other: the collapsed remote's header row, or the signal row.
        assert '${this._heard.signalId === sig.id ? "last-heard" : ""}' in monitor
        assert re.search(
            r'class="device-row \$\{blooming \? "bloom" : ""\} '
            r'\$\{this\._heard\.deviceId === d\.id \? "last-heard" : ""\}',
            monitor,
        )
        assert monitor.count('"last-heard"') == 2
        # No new stored state: nothing persisted in the browser either.
        for name in (
            "ir-signal-monitor.ts", "ir-listen-row.ts", "ir-listen-chip.ts", "ir-listen-state.ts",
        ):
            assert "localStorage" not in _src(name)

    def test_last_heard_is_a_faint_tint(self):
        """Round 2, owner: "I like the glow, but I don't like the
        remaining stroke". A wash of the arrival blue, no border, no
        shadow, toned per theme: 7 percent read as near-black on a dark
        card and as nothing on white (owner, on the real box), so the
        host carries ``dark`` from HA's theme and the alpha follows."""
        monitor = _src("ir-signal-monitor.ts")
        device = re.search(r"\.device-row\.last-heard \{([^}]*)\}", monitor).group(1)
        signal = re.search(r"\.signal-row\.last-heard \{([^}]*)\}", monitor).group(1)
        assert "background: rgba(3, 169, 244, var(--heard-alpha));" in device
        assert "rgba(3, 169, 244, var(--heard-alpha))" in signal
        assert re.search(r":host \{\s*--heard-alpha: 0\.14;", monitor)
        assert re.search(r":host\(\[dark\]\) \{\s*--heard-alpha: 0\.12;", monitor)
        assert 'this.toggleAttribute("dark", Boolean(this.hass?.themes?.darkMode));' in monitor
        # Layered over the row's own ground, so the row stays opaque.
        assert "var(--primary-background-color)" in signal
        for rule in (device, signal):
            assert "border" not in rule and "box-shadow" not in rule

    def test_the_stroke_is_gone(self):
        monitor = _src("ir-signal-monitor.ts")
        for gone in ("card-last-heard", "rgba(79, 195, 247"):
            assert gone not in monitor
        # The row's invisible border stays, so the bloom never moves it.
        assert re.search(
            r"\.signal-row \{.*?padding: 5px 7px;\s*border: 1px solid transparent;",
            monitor, re.S,
        )

    def test_hover_still_shows_over_the_tint(self):
        monitor = _src("ir-signal-monitor.ts")
        assert monitor.index(".device-row.last-heard {") < monitor.index(".device-row:hover {")


class TestTheBroadlinkHint:
    def test_it_shows_only_on_a_core_broadlink_without_broadsniff(self):
        devlist = _src("ir-device-list.ts")
        assert 'this.hass?.entities?.[entityId]?.platform !== "broadlink"' in devlist
        assert '!components.includes("broadsniff")' in devlist
        assert "${this._renderBroadSniffHint(em.entity_id)}" in devlist

    def test_it_links_to_the_repo_without_opening_the_card(self):
        devlist = _src("ir-device-list.ts")
        assert 'BROADSNIFF_URL = "https://github.com/DAB-LABS/broadsniff"' in _src("types.ts")
        hint = devlist[devlist.index("private _renderBroadSniffHint"):]
        hint = hint[: hint.index("`;")]
        assert 'target="_blank"' in hint
        assert 'rel="noopener noreferrer"' in hint
        assert "@click=${stop}" in hint and "@keydown=${stop}" in hint


class TestTheReceiverCard:
    """Round 2: the Devices page's hardware card shows the Listen chip."""

    def test_the_card_shows_the_same_chip_compact(self):
        devlist = _src("ir-device-list.ts")
        assert 'import "./ir-listen-chip.js";' in devlist
        badge = devlist[devlist.index("private _renderNativeBadge"):]
        badge = badge[: badge.index("/** Render TX/RX-NATIVE")]
        assert re.search(r"<ir-listen-chip\s+compact\s+\.hass=", badge)
        assert ".row=${capture.row}" in badge
        # Not a fork: no second chip element anywhere.
        assert "customElement(\"ir-listen-chip\")" in _src("ir-listen-chip.ts")
        assert "listen-drain" not in devlist and "broadsniffListen" not in devlist

    def test_rx_capture_replaces_rx_native(self):
        """Owner, 2026-10-17: one receiver badge per card."""
        devlist = _src("ir-device-list.ts")
        badge = devlist[devlist.index("private _renderNativeBadge"):]
        badge = badge[: badge.index("/** Render TX/RX-NATIVE")]
        chip = badge.index("<ir-listen-chip")
        # Since the owner's bench (ember, 2026-10-19) each badge carries
        # its health in its class, tooltip and accessible name.
        static = badge.index('class="badge rx-capture ${online ? "" : "offline"}"')
        native = badge.index('class="badge rx-native ${online ? "" : "offline"}"')
        assert chip < native and static < native
        assert badge.count("return html`") == 3
        assert 'this._badgeName("RX-CAPTURE", online, t("devlist.rx_capture_title"))' in badge
        rx = devlist[devlist.index("private _renderRxBadges"):]
        assert rx.index("${this._renderNativeBadge(entry)}") < rx.index("${entry.has_bridge")

    def test_the_match_is_read_from_the_attribute_then_the_row(self):
        devlist = _src("ir-device-list.ts")
        assert "this._listenRows.find((r) => r.ha_device_id === entry.device_id)" in devlist
        assert "this.hass?.states?.[entry.native_entity_id]?.attributes" in devlist
        assert "rxCaptureMatch(attributes, row !== undefined)" in devlist
        assert 'typeof receiverAttributes?.capturing === "boolean"' in _src("ir-listen-state.ts")

    def test_the_rows_are_read_on_registry_change_not_every_update(self):
        devlist = _src("ir-device-list.ts")
        assert re.search(
            r"this\.hass\?\.entities !== this\._listenRowsFor\) \{\s*"
            r"this\._listenRowsFor = this\.hass\?\.entities;\s*"
            r"void this\._loadListenRows\(\);",
            devlist,
        )
        assert re.search(r"catch \{\s*this\._listenRows = \[\];", devlist)

    def test_the_chip_never_opens_the_card(self):
        chip = _src("ir-listen-chip.ts")
        assert "private _stop = (e: Event) => e.stopPropagation();" in chip
        assert "@click=${this._stop}" in chip and "@keydown=${this._stop}" in chip

    def test_the_compact_form_is_a_badge_without_the_glyph(self):
        chip = _src("ir-listen-chip.ts")
        assert 'RX_CAPTURE_LABEL = "RX-CAPTURE"' in chip
        assert "${this.compact ? RX_CAPTURE_LABEL : row.name}" in chip
        # Owner addendum 2026-10-17: like TX-NATIVE and RX-NATIVE, no dot.
        # The dot stays on the Sniffer's chip.
        # Chip health (ember, 2026-10-19): the full chip's dot turns into
        # the ember ring when offline; the compact form still has none.
        assert re.search(
            r"\$\{this\.compact\s*\?\s*nothing\s*:\s*"
            r'html`<span class="dot \$\{online \? "" : "offline"\}"></span>`\}',
            chip,
        )
        toggle = re.search(r":host\(\[compact\]\) \.listen-toggle \{([^}]*)\}", chip).group(1)
        assert "padding: 2px 4px;" in toggle  # the .badge padding
        assert re.search(r"\$\{this\.compact\s*\?\s*nothing\s*:\s*renderExitToEntityBtn", chip)
        compact = re.search(r":host\(\[compact\]\) \.chip\.listen \{([^}]*)\}", chip).group(1)
        for prop in ("border-radius: 4px;", "font-size: 0.72rem;", "white-space: nowrap;"):
            assert prop in compact
        assert "@property({ type: Boolean, reflect: true }) public compact = false;" in chip

    def test_the_receivers_card_gets_the_finger_and_the_proxy_keeps_the_tower(self):
        devlist = _src("ir-device-list.ts")
        # Since chip health (ember, owner bench 2026-10-19) each card icon
        # is a solid and outline pair (card-icons.ts). The capture card
        # keeps the finger online; offline it draws record-circle-outline
        # (gesture-tap-button has no outline twin; owner ruling).
        assert re.search(
            r"\.path=\$\{cardIconPath\(\s*this\._rxCapture\(entry\)\.kind !== null"
            r"\s*\?\s*\"capture\"\s*:\s*\"receiver\",\s*glyph,\s*\)\}",
            devlist,
        )
        assert '<ha-svg-icon .path=${cardIconPath("proxy", glyph)}></ha-svg-icon>' in devlist

    def test_a_narrow_card_wraps_its_badges_instead_of_breaking_them(self):
        devlist = _src("ir-device-list.ts")
        footer = re.search(r"\.card-footer \{([^}]*)\}", devlist).group(1)
        assert "flex-wrap: wrap;" in footer
        badge = re.search(r"\n        \.badge \{([^}]*)\}", devlist).group(1)
        assert "white-space: nowrap;" in badge


class TestTheLearnDialog:
    def test_the_arm_failed_code_is_the_servers(self):
        assert f'BROADSNIFF_ARM_FAILED = "{ARM_FAILED_CODE}"' in _src("types.ts")

    def test_both_failure_paths_say_it_in_the_users_language(self):
        dialog = _src("ir-capture-dialog.ts")
        assert (
            'if (code === BROADSNIFF_ARM_FAILED) return t("capture.broadsniff_failed");'
            in dialog
        )
        assert "this._error = captureErrorText(event.code, event.error);" in dialog
        assert re.search(
            r"this\._error = captureErrorText\(\s*\(err as \{ code\?: unknown \}\)\.code,",
            dialog,
        )


class TestTheStrings:
    KEYS = (
        "listen.label", "listen.on_title", "listen.off_title", "listen.open_title",
        "listen.failed", "capture.broadsniff_failed", "devlist.broadsniff_hint",
        "devlist.rx_capture_title",
    )

    def test_every_new_key_is_in_english(self):
        en = _en()
        for key in self.KEYS:
            assert key in en, key
        assert en["capture.broadsniff_failed"] == "The Broadlink could not start listening."
        assert en["devlist.rx_capture_title"] == "Hears only while a capture window is open"

    def test_every_key_the_new_code_asks_for_exists(self):
        en = _en()
        for name in (
            "ir-listen-row.ts", "ir-listen-chip.ts", "ir-capture-dialog.ts", "ir-device-list.ts",
        ):
            for key in re.findall(r'\bt\("((?:listen|capture|devlist)\.[\w.]+)"', _src(name)):
                assert key in en, (name, key)
