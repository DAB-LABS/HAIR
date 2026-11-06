// Driver for test_rf_send_js.py: the RF send round's frontend rules,
// transpiled to plain JS, printed as JSON.
import { emitterGroups, emitterMedium, getEmitterOptions } from "./emitter-options.js";

const on = (attrs = {}, state = "2026-11-06T20:00:00Z") => ({ state, attributes: attrs });
const states = {
    "infrared.living_room_blaster": on({ friendly_name: "Living room blaster" }),
    "infrared.rm4_pro_ir_receiver": on({ device_class: "receiver" }),
    "infrared.hair_tweezer": on({ hair_observer: true }),
    "radio_frequency.athom_rf_transmitter": on({ device_class: "transmitter", friendly_name: "Athom RF transmitter" }),
    "radio_frequency.athom_rf_receiver": on({ device_class: "receiver" }),
    "radio_frequency.rm4_pro_rf_transmitter": on({ device_class: "transmitter" }, "unavailable"),
    "infrared.second_blaster": on({ friendly_name: "Second blaster" }),
    "light.kitchen": on(),
};
for (const [id, st] of Object.entries(states)) st.entity_id = id;
const hass = { states, entities: {}, devices: {} };
const receivers = new Set(["infrared.rm4_pro_ir_receiver"]);
const options = getEmitterOptions(hass, receivers, ["infrared.second_blaster"]);

const out = {
    options: options.map((o) => [o.entity_id, o.medium, o.available]),
    media: ["infrared.x", "radio_frequency.y", "light.z", "nonsense"].map(emitterMedium),
    groups_all: emitterGroups(options, null).map((g) => [g.medium, g.items.length]),
    groups_rf: emitterGroups(options, ["rf"]).map((g) => [g.medium, g.items.length]),
    groups_ir: emitterGroups(options, ["ir"]).map((g) => [g.medium, g.items.length]),
    groups_none: emitterGroups(options.filter((o) => o.medium === "ir"), ["rf"]),
};
console.log(JSON.stringify(out));

// T3: the radio code editor's rules.
const rf = await import("./rf-code.js");
const frame = [1282, -382, 458, -1221, 458, -1221, 1282];
console.log(JSON.stringify({
    t3: {
        sub_with_gap: rf.toSub(frame, 433920000, 12909),
        sub_on_space: rf.toSub([...frame, -9000], 315000000, 12909),
        sub_no_freq: rf.toSub(frame, null, null),
        sub_long: rf.toSub([...Array(401).keys()].map((i) => (i % 2 ? -500 : 500)), 433920000, 9000),
        mhz: ["433.92", "433,92", " 315 ", "303.875 MHz", "0.5", "20000", "abc", "", "433.92.1"].map(rf.mhzToHz),
        to_mhz: [433920000, 315000000, 303875000, 433420000].map(rf.hzToMhz),
        preset: [433920000, 315000000, 433420000, null].map(rf.presetOf),
        source: ["signal", "receiver", "window", "user", "assumed", null, "other"].map(rf.sourceKey),
        refusal: ["rf_paste_empty", "rf_paste_unreadable", "rf_paste_no_frame", "rf_paste_frames_disagree", "duplicate_signal", null].map(rf.pasteRefusalKey),
    },
}));
