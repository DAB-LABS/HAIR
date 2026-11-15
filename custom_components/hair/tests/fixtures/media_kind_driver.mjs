// Driver for test_picker_kinds.py: the pickers' kind rule, transpiled
// to plain JS, printed as JSON.
import { keepKind, listsInKind, mediaFor, rowsKind, soleKind, unknownKind } from "./media-kind.js";

const domain = (id) =>
    id.startsWith("infrared.") ? "ir" : id.startsWith("radio_frequency.") ? "rf" : null;
const ids = ["infrared.blaster", "radio_frequency.athom", "remote.legacy"];

console.log(JSON.stringify({
    sole: [soleKind(["rf"]), soleKind(["ir"]), soleKind(["ir", "rf"]), soleKind([]), soleKind(null), soleKind(undefined)],
    rows: [
        rowsKind([{ medium: "rf" }, { medium: "rf" }]),
        rowsKind([{ medium: "ir" }, {}, { medium: null }]),
        rowsKind([{ medium: "ir" }, { medium: "rf" }]),
        rowsKind([]),
        rowsKind(null),
        rowsKind([{ medium: "rf" }], true),
        rowsKind([], true),
        rowsKind([{ medium: "ir" }], true),
    ],
    unknown: [unknownKind("rf"), unknownKind("ir"), unknownKind(null), unknownKind(undefined)],
    keep_rf: keepKind(ids, "rf", domain),
    keep_ir: keepKind(ids, "ir", domain),
    keep_open: keepKind(ids, null, domain),
    lists: [
        listsInKind("infrared.blaster", "rf", domain, false),
        listsInKind("infrared.blaster", "rf", domain, true),
        listsInKind("radio_frequency.athom", "rf", domain, false),
        listsInKind("remote.legacy", "rf", domain, false),
        listsInKind("infrared.blaster", null, domain, false),
    ],
    media: [mediaFor("rf"), mediaFor("ir"), mediaFor(null)],
}));
