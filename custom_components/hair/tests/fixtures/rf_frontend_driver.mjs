// Driver for test_rf_frontend_js.py: runs the RF hear round 1 frontend
// rules transpiled to plain JS and prints what they return, as JSON.
// __NOW__ is filled in by the test.
import {
    agoParts, badgeLabel, buildHardwareCards, cardOffline, hardwareSections, mediumBreak,
} from "./ir-hardware-rows.js";
import {
    bandNumber, currentFrequency, currentLength, currentMode, frequencyChoices,
    lengthChoices, modeChoices, pickersActive, pillBadge, pillLive, pillLook, pillPressable,
} from "./ir-listen-state.js";
import { carrierParts, snifferShows, snifferShowsEverything } from "./sniffer-filter.js";
import { bandHz, bandKey, bandLabel } from "./rf-band.js";

const NOW = Date.parse("__NOW__");
const ago = (s) => new Date(NOW - s * 1000).toISOString();
const later = (s) => new Date(NOW + s * 1000).toISOString();
const on = (attrs = {}) => ({ state: "2026-11-06T19:00:00Z", attributes: attrs });
const down = { state: "unavailable", attributes: {} };

// The RM4 Pro as the bench has it: two transmitters, two receivers.
const RM4 = "dev-rm4";
const rm4States = {
    "infrared.wi_fi_universal_remote_ir_emitter": on(),
    "infrared.rm4_pro_ir_receiver": on({ capturing: false }),
    "radio_frequency.wi_fi_universal_remote_rf_transmitter": on({ device_class: "transmitter" }),
    "radio_frequency.rm4_pro_rf_receiver": on({ device_class: "receiver", capturing: false }),
    "infrared.living_room_blaster": on(),
    "infrared.hair_tweezer": on({ hair_observer: true }),
    "infrared.gh72_rf_proxy": on(),
    "light.kitchen": on(),
};
const rm4Entities = {
    "infrared.wi_fi_universal_remote_ir_emitter": { device_id: RM4 },
    "infrared.rm4_pro_ir_receiver": { device_id: RM4 },
    "radio_frequency.wi_fi_universal_remote_rf_transmitter": { device_id: RM4 },
    "radio_frequency.rm4_pro_rf_receiver": { device_id: RM4 },
    "infrared.living_room_blaster": { device_id: "dev-blaster" },
};
const receivers = [
    { type: "native", device_id: "infrared.rm4_pro_ir_receiver", name: "RM4 IR",
      config_entry_id: null, receiver_entity_id: "infrared.rm4_pro_ir_receiver" },
    { type: "native", device_id: "radio_frequency.rm4_pro_rf_receiver", name: "RM4 RF",
      config_entry_id: null, receiver_entity_id: "radio_frequency.rm4_pro_rf_receiver",
      medium: "rf", always_on: false },
    { type: "esphome", device_id: "dev-bridge", name: "Old bridge", config_entry_id: null },
];
const facts = {
    heard: { "radio_frequency.rm4_pro_rf_receiver": ago(180) },
    sent: { "infrared.wi_fi_universal_remote_ir_emitter": ago(14) },
};
const cards = buildHardwareCards({
    states: rm4States, entities: rm4Entities, receivers, captureRows: [], facts,
    hidden: new Set(["infrared.gh72_rf_proxy"]),
});
const rm4 = cards.find((c) => c.device_id === RM4);
const sections = hardwareSections(cards);

// Everything on the RM4 Pro down. HA keeps device_class on an
// unavailable entity, and drops the rest.
const allDown = {};
for (const [id, st] of Object.entries(rm4States)) {
    const dc = st.attributes.device_class;
    allDown[id] = dc ? { state: "unavailable", attributes: { device_class: dc } } : down;
}
const emberCard = buildHardwareCards({
    states: allDown, entities: rm4Entities, receivers, captureRows: [], facts, hidden: new Set(),
}).find((c) => c.device_id === RM4);

// A remembered capture device whose integration has not loaded.
const remembered = buildHardwareCards({
    states: {}, entities: { "infrared.garage_rx": { device_id: "dev-garage" } },
    receivers: [], facts: null,
    captureRows: [{ receiver_entity_id: "infrared.garage_rx", capture_device: true, medium: "ir" }],
});

// --- The Listen pill -----------------------------------------------------
const hwRow = (over = {}) => ({
    receiver_entity_id: "radio_frequency.rm4_pro_rf_receiver", name: "Broadlink RM4 Pro",
    ha_device_id: RM4, available: true, switch_entity_id: "switch.rm4_rf_capture",
    source: "declared", device_switches: [], medium: "rf", capture_phase: null,
    frequency_hz: null, capture_device: true, software_window: false, capturing: false,
    window_ends_at: null, capture_mode: null,
    frequency_select: "select.rm4_rf_frequency", window_length: "number.rm4_capture_window",
    capture_mode_select: "select.rm4_capture_mode",
    frequency_options: [
        { option: "mhz_433_92", hz: 433920000 }, { option: "mhz_315", hz: 315000000 },
        { option: "sweep", hz: null },
    ],
    window_seconds: null, window_mode: null, ...over,
});
const swRow = (over = {}) => hwRow({
    receiver_entity_id: "radio_frequency.athom_rf_receiver", name: "Athom IR-RF Proxy",
    switch_entity_id: null, source: "software", capture_device: false, software_window: true,
    frequency_select: null, window_length: null, capture_mode_select: null,
    frequency_options: [], window_seconds: 30, window_mode: "sliding", ...over,
});
const rx = (attrs) => ({ "radio_frequency.rm4_pro_rf_receiver": on(attrs) });
const look = (row, states, item) => {
    const live = pillLive(states, row, item);
    return pillLook(row, true, live);
};
const pill = {
    idle: look(hwRow(), rx({ capturing: false })),
    open: look(hwRow(), rx({ capturing: true, window_ends_at: later(20) })),
    sweep: look(hwRow(), rx({ capturing: true, capture_phase: "sweeping" })),
    locked: look(hwRow(), rx({ capturing: true, capture_phase: "listening", frequency_hz: 433920000 })),
    hearing: look(swRow(), {}),
    software_open: look(swRow(), {}, {
        receiver_entity_id: "radio_frequency.athom_rf_receiver", capturing: true,
        window_ends_at: later(30), capture_mode: "sliding", counters: null,
    }),
    // The subscription wins over the row it started from.
    software_closed_by_item: look(swRow({ capturing: true, window_ends_at: later(30) }), {}, {
        receiver_entity_id: "radio_frequency.athom_rf_receiver", capturing: false,
        window_ends_at: null, capture_mode: null, counters: null,
    }),
    // The software window is never read from the receiver's state.
    software_ignores_hass: look(swRow(), {
        "radio_frequency.athom_rf_receiver": on({ capturing: true }),
    }),
    offline: pillLook(hwRow(), false, pillLive({}, hwRow())),
    waiting: look(hwRow({ switch_entity_id: null, source: null }), rx({ capturing: false })),
    ir_badge: pillBadge(hwRow({ medium: "ir" })),
    rf_badge: pillBadge(hwRow()),
    // An always-on infrared receiver: a status pill (fix round 1, item 6).
    status: look(hwRow({
        receiver_entity_id: "infrared.athom_ir_receiver", medium: "ir", switch_entity_id: null,
        source: null, capture_device: false, always_on: true, frequency_select: null,
        window_length: null, capture_mode_select: null, frequency_options: [],
    }), { "infrared.athom_ir_receiver": on({}) }),
};
const pressable = {};
for (const l of ["idle", "hearing", "status", "open", "sweep", "offline", "waiting"]) pressable[l] = pillPressable(l);
const active = {};
for (const l of ["idle", "hearing", "open", "sweep", "offline", "waiting"]) active[l] = pickersActive(l);

// --- The pickers -----------------------------------------------------------
const pickStates = (len, mode, freq, lengthAttrs = { min: 1, max: 60 }) => ({
    "number.rm4_capture_window": { state: String(len), attributes: lengthAttrs },
    "select.rm4_capture_mode": { state: mode, attributes: { options: ["sliding", "single", "multiple"] } },
    "select.rm4_rf_frequency": { state: freq, attributes: { options: ["mhz_433_92", "mhz_315", "sweep", "custom"] } },
    "radio_frequency.rm4_pro_rf_receiver": on({ capturing: false }),
});
const bsStates = pickStates(10, "sliding", "mhz_433_92");
const live0 = pillLive(bsStates, hwRow());
const pickers = {
    bs_lengths: lengthChoices(bsStates, hwRow()),
    bs_lengths_300: lengthChoices(pickStates(10, "sliding", "mhz_433_92", { min: 1, max: 300 }), hwRow()),
    sw_lengths: lengthChoices({}, swRow()),
    undeclared_lengths: lengthChoices(bsStates, hwRow({ window_length: null })),
    bs_length: currentLength(bsStates, hwRow()),
    sw_length: currentLength({}, swRow({ window_seconds: 120 })),
    bs_modes: modeChoices(bsStates, hwRow()),
    sw_modes: modeChoices({}, swRow()),
    bs_mode: currentMode(bsStates, hwRow()),
    sw_mode: currentMode({}, swRow({ window_mode: "single" })),
    freqs: frequencyChoices(hwRow()).map((o) => o.option),
    fixed_band: frequencyChoices(hwRow({ frequency_options: [{ option: "only", hz: 433920000 }] })),
    no_select: frequencyChoices(hwRow({ frequency_select: null })),
    freq_433: currentFrequency(bsStates, hwRow(), live0),
    freq_sweep: currentFrequency(pickStates(10, "sliding", "sweep"), hwRow(), live0),
    freq_found: currentFrequency(
        pickStates(10, "sliding", "sweep"), hwRow(),
        { on: true, endsAt: later(10), phase: "listening", frequencyHz: 433920000 },
    ),
    freq_custom: currentFrequency(
        pickStates(10, "sliding", "custom"), hwRow(),
        { on: false, endsAt: null, phase: null, frequencyHz: 303900000 },
    ),
    bands: [433920000, 315000000, 433420000, 868300000].map(bandNumber),
};

// The remotes the SHOW chips are asked about.
const R = {
    ir: { dismissed: false },
    rf: { dismissed: false, medium: "rf" },
    hidden_ir: { dismissed: true },
    none: { dismissed: false, medium: undefined },
};

const out = {
    rows: rm4.rows.map((r) => [badgeLabel(r), r.entity_id, r.available, r.fact]),
    rm4_break: mediumBreak(rm4),
    rm4_offline: cardOffline(rm4),
    ember_offline: cardOffline(emberCard),
    ember_facts: emberCard.rows.map((r) => r.fact.kind),
    sections: Object.fromEntries(Object.entries(sections).map(([k, v]) => [k, v.map((c) => c.device_id)])),
    all_ids: cards.flatMap((c) => c.rows.map((r) => r.entity_id)),
    blaster_break: mediumBreak(cards.find((c) => c.device_id === "dev-blaster")),
    remembered: remembered.map((c) => [c.device_id, c.rows.map((r) => [badgeLabel(r), r.available])]),
    capture_flag: rm4.rows.filter((r) => r.capture_device).map((r) => r.entity_id),
    ago: [5, 59, 60, 3599, 3600, 86399, 86400 * 3].map((s) => agoParts(ago(s), NOW)),
    ago_bad: agoParts("not a time", NOW),
    pill, active, pickers, pressable,
    // The three filter glyphs, each its own toggle (fix round 1, item 3).
    shows: Object.fromEntries(
        [
            ["default", { ir: true, rf: true, hidden: false }],
            ["ir_only", { ir: true, rf: false, hidden: false }],
            ["rf_only", { ir: false, rf: true, hidden: false }],
            ["with_hidden", { ir: true, rf: true, hidden: true }],
            ["rf_and_hidden", { ir: false, rf: true, hidden: true }],
            ["none", { ir: false, rf: false, hidden: false }],
        ].map(([name, show]) => [name, {
            rows: ["ir", "rf", "hidden_ir", "none"].map((k) => snifferShows(show, R[k])),
            everything: snifferShowsEverything(show),
        }]),
    ),
    carriers: [
        carrierParts({ medium: "rf", rf_frequency_hz: 433920000, frequency: 38000 }),
        carrierParts({ medium: "rf", rf_frequency_hz: null, frequency: 38000 }),
        carrierParts({ frequency: 38029 }),
        carrierParts({}),
        // The bench's second report of the same keyfob (item 8).
        carrierParts({ medium: "rf", rf_frequency_hz: 433840000 }),
    ],
    // __BAND_HZ__ is the carriers of tests/fixtures/rf/band_cases.json.
    band_cases: __BAND_HZ__.map((hz) => ({
        hz, band_hz: bandHz(hz), key: bandKey(hz), label: bandLabel(hz),
    })),
};
console.log(JSON.stringify(out));
