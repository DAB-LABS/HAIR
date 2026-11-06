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
