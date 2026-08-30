/**
 * Devices overview page with four sections:
 *   Devices  -- HAIR-managed IR devices (expandable inline detail)
 *   Emitters -- infrared.* TX entities
 *   Receivers -- RX-only capture providers
 *   Proxies  -- TX+RX capable hardware (both emitter and receiver)
 *
 * Emits ``device-selected`` and ``add-device`` events for HAIR devices.
 * Emitter/receiver/proxy cards link to their HA integration page.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import {
    ICON_TRASH,
    TRASH_VIEWBOX,
    ICON_SETTINGS,
    SETTINGS_VIEWBOX,
    settingsButtonStyles,
    renderExitToEntityBtn,
    exitToEntityButtonStyles,
} from "./ir-icons.js";
import { BloomTracker, bloomStyles } from "./ir-bloom-styles.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import { keyed } from "lit/directives/keyed.js";
import { repeat } from "lit/directives/repeat.js";
import Sortable from "sortablejs";
import "./ir-device-detail.js";
import "./ir-trigger-dialog.js";
import "./ir-trigger-row.js";
// Signpost 4, Track M: the remote detail's hear-side pair. The card is
// the device page's lattice in "hear" mode; the row is the readout of
// the one state most recently heard through it.
import "./ir-matrix-card.js";
import "./ir-last-heard-row.js";
import "./ir-confirm-dialog.js";
import "./ir-duplicate-device-dialog.js";
import "./ir-duplicate-trigger-remote-dialog.js";
import "./ir-promote-remote-dialog.js";
import "./ir-promote-dialog.js";
import "./ir-pin-prompt-dialog.js";
import "./ir-header-chip-group.js";
import type { HeaderChipRow } from "./ir-header-chip-group.js";
import "./ir-trigger-remote-settings-dialog.js";
import "./ir-ghost-tile.js";
import { GREEN_PEAK, ORIGIN_COLORS } from "./ir-origin-colors.js";
import { PINNING_UI_ENABLED, PIN_BLUE } from "./ir-pin-flag.js";
import type { HairApi } from "./api.js";
import type { MatrixCardPick } from "./ir-matrix-card.js";
import type { WigPickRow } from "./ir-wig-picker.js";
import type {
    CaptureProviderInfo,
    CombSummary,
    DeviceSummary,
    DeviceTypeId,
    IRDevice,
    IRTrigger,
    LastHeard,
    MatrixCellDetail,
    MatrixSummary,
    PluckedStoreRecord,
    ReceiverInfo,
    ReverseSupersessionBlock,
    TriggerDrawerInfo,
    TriggerFiredEvent,
    TriggerRemoteInfo,
    WigInfo,
} from "./types.js";

/**
 * Sentinel "device id" for the single HAIR Triggers drawer card, reusing
 * the parent panel's existing ``expandedDeviceId``/``device-selected``
 * expand-one-at-a-time machinery (ha-panel-ir-devices.ts's
 * ``_toggleDevice``) rather than inventing a second, parallel expansion
 * concept. Guaranteed not to collide with a real device id (those are
 * storage-assigned uuids).
 */
const TRIGGER_DRAWER_ID = "__hair_triggers_drawer__";

const DEVICE_TYPE_ICONS: Record<DeviceTypeId, string> = {
    media_player: "M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",
    ac: "M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",
    fan: "M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",
    light: "M12,2A7,7 0 0,0 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H15A1,1 0 0,0 16,17V14.74C17.81,13.47 19,11.38 19,9A7,7 0 0,0 12,2M9,21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9V21Z",
    switch: "M13,3H11V13H13V3M17.83,5.17L16.41,6.59C18,7.35 19,9.05 19,11A7,7 0 0,1 12,18A7,7 0 0,1 5,11C5,9.05 6,7.35 7.58,6.59L6.17,5.17C4.23,6.82 3,9.26 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12C21,9.26 19.77,6.82 17.83,5.17Z",
    screen: "M20,19H4A2,2 0 0,1 2,17V7A2,2 0 0,1 4,5H20A2,2 0 0,1 22,7V17A2,2 0 0,1 20,19M4,7V17H20V7H4M12,10L16,14H13V17H11V14H8L12,10Z",
    other: "M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z",
};

// Dictionary keys, resolved through t() at render time. "other" maps
// to the card-specific label ("IR Device"), not the dialogs' "Other".
const DEVICE_TYPE_LABEL_KEYS: Record<DeviceTypeId, string> = {
    media_player: "device_type.media_player",
    ac: "device_type.ac",
    fan: "device_type.fan",
    light: "device_type.light",
    switch: "device_type.switch",
    screen: "device_type.screen",
    other: "device_type.other_card",
};

// Remote control (SVG Repo, scaled to a 24x24 box).
const ICON_DEVICES =
    "M17.655 0C17.391 0.034 17.201 0.276 17.235 0.54C17.269 0.804 17.511 0.994 17.775 0.96C17.775 0.96 18.154 0.941 18.81 1.155C19.466 1.369 20.353 1.804 21.255 2.73C22.162 3.66 22.611 4.551 22.83 5.205C23.049 5.859 23.04 6.24 23.04 6.24C23.038 6.412 23.128 6.574 23.278 6.662C23.428 6.748 23.612 6.748 23.762 6.662C23.912 6.574 24.002 6.412 24 6.24C24 6.24 23.991 5.679 23.73 4.905C23.469 4.131 22.957 3.109 21.945 2.07C20.927 1.027 19.894 0.495 19.11 0.24C18.326 -0.015 17.745 0 17.745 0C17.73 0 17.715 0 17.7 0C17.685 0 17.67 0 17.655 0 Z M 13.77 2.88C13.26 2.88 12.746 3.064 12.345 3.435C12.339 3.441 12.336 3.444 12.33 3.45L0.57 15.255C-0.195 16.02 -0.188 17.286 0.555 18.09C0.561 18.096 0.564 18.099 0.57 18.105L5.955 23.475C6.72 24.24 7.971 24.232 8.775 23.49C8.781 23.484 8.784 23.481 8.79 23.475L20.55 11.715C20.556 11.706 20.561 11.694 20.565 11.685C21.289 10.841 21.315 9.6 20.55 8.835L15.165 3.45C14.782 3.067 14.28 2.88 13.77 2.88 Z M 17.67 2.88C17.406 2.904 17.211 3.141 17.235 3.405C17.259 3.669 17.496 3.864 17.76 3.84C17.76 3.84 17.91 3.831 18.21 3.93C18.51 4.029 18.911 4.241 19.335 4.665C19.759 5.089 19.971 5.49 20.07 5.79C20.169 6.09 20.16 6.24 20.16 6.24C20.158 6.412 20.248 6.574 20.398 6.662C20.548 6.748 20.732 6.748 20.882 6.662C21.032 6.574 21.122 6.412 21.12 6.24C21.12 6.24 21.111 5.91 20.97 5.49C20.829 5.07 20.561 4.511 20.025 3.975C19.489 3.439 18.93 3.171 18.51 3.03C18.09 2.889 17.76 2.88 17.76 2.88C17.745 2.88 17.73 2.88 17.715 2.88C17.7 2.88 17.685 2.88 17.67 2.88 Z M 13.77 3.84C14.04 3.84 14.297 3.932 14.49 4.125L19.875 9.51C20.263 9.898 20.274 10.569 19.845 11.07L8.115 22.785C7.671 23.194 7.018 23.188 6.63 22.8L1.26 17.43C1.254 17.424 1.251 17.421 1.245 17.415C0.849 16.971 0.862 16.328 1.245 15.945L13.005 4.14C13.226 3.936 13.5 3.84 13.77 3.84 Z M 13.44 6.72C11.325 6.72 9.6 8.445 9.6 10.56C9.6 12.675 11.325 14.4 13.44 14.4C15.555 14.4 17.28 12.675 17.28 10.56C17.28 8.445 15.555 6.72 13.44 6.72 Z M 13.44 7.68C15.036 7.68 16.32 8.964 16.32 10.56C16.32 12.156 15.036 13.44 13.44 13.44C11.844 13.44 10.56 12.156 10.56 10.56C10.56 8.964 11.844 7.68 13.44 7.68 Z M 13.44 9.6C12.909 9.6 12.48 10.029 12.48 10.56C12.48 11.091 12.909 11.52 13.44 11.52C13.971 11.52 14.4 11.091 14.4 10.56C14.4 10.029 13.971 9.6 13.44 9.6 Z M 7.2 12.96C6.669 12.96 6.24 13.389 6.24 13.92C6.24 14.451 6.669 14.88 7.2 14.88C7.731 14.88 8.16 14.451 8.16 13.92C8.16 13.389 7.731 12.96 7.2 12.96 Z M 4.8 15.36C4.269 15.36 3.84 15.789 3.84 16.32C3.84 16.851 4.269 17.28 4.8 17.28C5.331 17.28 5.76 16.851 5.76 16.32C5.76 15.789 5.331 15.36 4.8 15.36 Z M 10.08 15.84C9.549 15.84 9.12 16.269 9.12 16.8C9.12 17.331 9.549 17.76 10.08 17.76C10.611 17.76 11.04 17.331 11.04 16.8C11.04 16.269 10.611 15.84 10.08 15.84 Z M 7.68 18.24C7.149 18.24 6.72 18.669 6.72 19.2C6.72 19.731 7.149 20.16 7.68 20.16C8.211 20.16 8.64 19.731 8.64 19.2C8.64 18.669 8.211 18.24 7.68 18.24Z";

// TV (owner-supplied, images/tv2.svg, scaled to a 490.797x490.797
// box -- non-24x24 native viewBox, paired with TV_VIEWBOX per the
// ICON_X/X_VIEWBOX convention below). Devices toolbar only -- the
// Remotes toolbar keeps ICON_DEVICES, the remote-control glyph.
const TV_VIEWBOX = "0 0 490.797 490.797";
const ICON_DEVICES_TV =
    "M56.879,450.427c9.517,1.554,20.216,3.072,32.626,4.621c0.508,1.838,1.041,3.661,1.569,5.484 c1.153,3.966,2.351,8.059,3.22,12.115c1.412,6.607,7.978,11.583,15.279,11.583c1.356,0,2.691-0.178,3.961-0.522 c8.079-2.225,12.781-10.42,10.938-19.062c-0.432-2.026-0.939-4.022-1.453-5.911c46.662,4.397,99.148,6.622" +
    ",156.087,6.622 c29.071,0,58.971-0.59,88.91-1.752c-0.396,2.392-1.025,4.656-1.985,7.17c-1.314,3.468-1.03,7.378,0.817,11.014 c2.093,4.123,5.84,7.271,10.009,8.42c1.402,0.386,2.813,0.589,4.199,0.589l0,0c6.571,0,12.289-4.316,14.925-11.253 c1.909-5.018,3.011-10.45,3.514-17.387c15.991-0.838,31.347-1.788,45." +
    "682-2.839c9.485-0.69,14.619-8.439,14.904-15.899 c32.245-93.363,31.478-201.943-2.225-314.032c-2.026-6.743-7.643-10.933-14.665-10.933c-0.828,0-1.66,0.061-2.488,0.175 c-1.514-0.437-2.925-0.645-4.383-0.645c-32.772-0.084-68.237-0.734-105.784-1.424c-39.166-0.719-79.587-1.462-119.602-1.597 c26.334-17.189,5" +
    "2.131-35.561,76.779-54.692c4.946-3.836,6.713-9.161,4.845-14.609c-2.229-6.51-9.283-11.42-16.402-11.42 c-3.595,0-7.063,1.216-10.034,3.521c-35.688,27.677-74.326,53.771-114.869,77.538l-4.108,0.063 c-7.003-37.315-16.595-71.648-29.29-104.901C115.388,4.009,109.502,0,102.49,0c-5.535,0-10.705,2.501-13.472,6." +
    "535 c-2.478,3.596-2.869,8.107-1.112,12.7c11.811,30.922,20.886,62.657,27.695,96.918c-26.096,0.868-48.982,2.178-69.873,3.994 c-5.967,0.516-10.75,3.895-13.213,9.303c-1.742,1.785-3.011,3.94-3.773,6.421c-32.575,106.863-28.335,212.94,12.258,306.75 C43.87,449.259,50.192,452.296,56.879,450.427z M57.032,150." +
    "517c37.923-2.93,84.092-4.354,141.051-4.354 c44.26,0,89.327,0.822,132.916,1.617c35.476,0.645,69.025,1.259,100.006,1.394c28.386,101.054,28.701,195.174,0.925,279.825 c-50.582,3.478-104.114,5.321-154.935,5.321c-82.177,0-155.305-4.834-211.614-13.995 C32.226,338.899,29.342,245.688,57.032,150.517z M99.306," +
    "407.589c43.6,7.114,89.738,10.572,140.995,10.572c0,0,0,0,0.005,0c32.662,0,67.853-1.411,107.577-4.326 c8.506-0.625,13.208-7.363,13.686-14.005c23.008-66.994,22.424-144.794-1.701-225.025c-2.037-6.762-8.171-10.766-15.168-10.096 c-1.123-0.269-2.229-0.403-3.352-0.403c-24.359-0.063-49.155-0.584-73.128-1.087" +
    "c-25.634-0.541-52.136-1.092-78.216-1.092 c-38.156,0-69.639,1.191-99.061,3.743c-5.215,0.452-9.592,3.433-11.908,8.039c-1.417,1.571-2.452,3.417-3.092,5.507 c-23.41,76.8-20.353,153.061,8.851,220.547C87.373,405.913,93.223,408.95,99.306,407.589z M101.85,193.971 c26.472-1.983,54.761-2.913,88.626-2.913c25.9" +
    "08,0,52.278,0.546,77.784,1.082c21.876,0.452,44.448,0.924,66.75,1.049 c19.104,69.464,19.342,134.208,0.717,192.554c-35.871,2.438-67.599,3.621-96.888,3.621c-47.931,0-90.896-3.144-131.235-9.613 C85.23,323.579,83.24,259.495,101.85,193.971z M411.912,232.147c4.672,0,8.617-1.722,11.415-4.972c2.433-2.828,3.7" +
    "73-6.608,3.773-10.638 c0-7.759-5.216-15.61-15.188-15.61c-4.672,0-8.617,1.722-11.415,4.972c-2.433,2.828-3.773,6.609-3.773,10.638 C396.723,224.294,401.938,232.147,411.912,232.147z M413.537,249.715c-4.667,0-8.612,1.727-11.41,4.977c-2.433,2.823-3.778,6.606-3.778,10.633 c0,7.759,5.215,15.61,15.184,15.61c" +
    "4.672,0,8.617-1.717,11.41-4.967c2.432-2.834,3.777-6.611,3.777-10.644 C428.725,257.575,423.504,249.715,413.537,249.715z";

// MDI: upload-outline for emitters (mirrors download-outline for receivers)
const ICON_EMITTER =
    "M9,10V16H15V10H19L12,3L5,10H9M12,5.8L14.2,8H13V14H11V8H9.8L12,5.8M19,18H5V20H19V18Z";

// MDI: download-outline for receivers
const ICON_RECEIVER =
    "M13,5V11H14.17L12,13.17L9.83,11H11V5H13M15,3H9V9H5L12,16L19,9H15V3M19,18H5V20H19V18Z";

// MDI: radio-tower for proxies
const ICON_PROXY =
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z";

// MDI: flash (lightning bolt) for triggers
const ICON_TRIGGER =
    "M7,2V13H10V22L17,10H13L17,2H7Z";

// MDI: drag (six-dot grip), for the trigger row's slotted drag handle.
// Same glyph ir-device-detail.ts's own (unexported) ICON_GRIP uses for
// command rows -- kept as a local copy rather than a shared export,
// matching that file's own precedent of not centralizing this one icon.
const ICON_GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

// MDI: content-copy (duplicate icon)
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";

// Tweezers (matches the Plucker tab icon).
const ICON_BLASTER =
    "M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z";

/** Debounce delay (ms) between a drop and the persist call. */
const REORDER_DEBOUNCE_MS = 500;

/**
 * Width of the Remote detail header's label column, in px (punch list
 * item 9, `header-pin-layout-handoff.md`). Every row on that header
 * passes this same value to ir-header-chip-group, which is what puts
 * "RECEIVERS:" and "PINNED:" on one colon line and keeps a wrapped row
 * of chips under the chips column instead of back under the label.
 *
 * DERIVED, not arbitrary: sized to "RECEIVERS:", 10 characters, the
 * longest label this column carries in any state now that the pin row
 * says "PINNED:" rather than "Pinned Devices:". The Device header's own
 * column is narrower (76px, sized to "EMITTERS:") and lives in
 * ir-device-detail.ts. Re-measure before adding a longer label here.
 */
const REMOTE_HDR_LABEL_W = 80;

/**
 * Result of merging capture providers by HA device ID.
 *
 * A physical device with both a native ``InfraredReceiverEntity`` and a
 * legacy ESPHome event-bridge entry collapses into one of these.  Broadlink
 * (proprietary learn mode) is bucketed as bridge for display purposes.
 */
interface MergedHardwareEntry {
    device_id: string;            // HA device-registry ID (merge key)
    name: string;                 // display name
    nav_type: string;             // integration domain for navigation
    has_native: boolean;          // InfraredReceiverEntity present
    has_bridge: boolean;          // ESPHome bridge or Broadlink learn mode
    has_tx: boolean;              // also TX-capable (= shows as proxy)
    native_entity_id?: string;    // entity_id of the native receiver, if any
    tx_entity_ids: string[];      // infrared.* TX entity_ids on this device
}

@customElement("ir-device-list")
export class IrDeviceList extends LitElement {
    @property({ attribute: false }) public devices: DeviceSummary[] = [];
    // Add Popups signpost 2, Track 4: named trigger remotes, parent-owned
    // and refreshed the same way ``devices`` is -- see this property's
    // sibling in ha-panel-ir-devices.ts. The HAIR Triggers drawer itself
    // (below) stays self-loaded via ``_triggerDrawer``/``_triggers``,
    // unaffected.
    @property({ attribute: false }) public triggerRemotes: TriggerRemoteInfo[] = [];
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api?: HairApi;
    @property({ type: Boolean }) public loading = false;
    @property({ attribute: false }) public expandedDeviceId: string | null = null;

    @state() private _emitters: { entity_id: string; name: string }[] = [];
    @state() private _captureProviders: CaptureProviderInfo[] = [];
    @state() private _pluckBlasters: {
        integration: string;
        entity_id: string;
        name: string;
        vendorName: string;
    }[] = [];
    // Learned-code stores this install has plucked (0.10.3). They sit
    // in the same section as the replay-capable hardware above, because
    // to a user both answer "where did these codes come from", but they
    // are records rather than devices: there is no entity behind one,
    // so the row is informational plus a delete.
    @state() private _pluckedStores: PluckedStoreRecord[] = [];
    @state() private _expandedDevice: IRDevice | null = null;
    @state() private _triggers: IRTrigger[] = [];
    @state() private _glowTriggerIds = new Set<string>();
    @state() private _editTrigger: IRTrigger | null = null;
    // Signpost 4, Track M: the create-mode trigger dialog, opened
    // pre-filled from a matrix cell. Three doors reach it -- the LAST
    // HEARD row, the card's action bar on the heard cell, the card's
    // action bar on a cell never heard -- and all three resolve to
    // this one piece of state, because they open the SAME dialog
    // aimed at the same remote with the same cell already in hand.
    @state() private _mintTrigger: {
        remoteId: string;
        detail: MatrixCellDetail;
    } | null = null;
    @state() private _confirmDeleteTrigger: IRTrigger | null = null;
    @state() private _duplicateTarget: DeviceSummary | null = null;
    @state() private _confirmDeleteDevice: DeviceSummary | null = null;
    // Mirror-door mints (signpost 3, Track 3.5, owner-directed
    // 2026-08-15): the source object riding between a Settings
    // dialog's request-make-remote/request-make-device and the mint
    // dialog it opens. The full IRDevice (not DeviceSummary) is
    // needed on the remote-mint side for its own .commands, to count
    // eligible (non-matrix-cell) rows for the preview line.
    @state() private _makeRemoteSource: IRDevice | null = null;
    @state() private _makeDeviceSource: TriggerRemoteInfo | null = null;
    // Pin prompt (Track 3.5): the remote/device pair riding from a
    // mirror-door mint's completion into ir-pin-prompt-dialog.ts.
    // Null whenever PINNING_UI_ENABLED is false, or the mint's own
    // source somehow went missing (defensive; should not happen).
    @state() private _pinPromptTarget: {
        remoteId: string;
        remoteName: string;
        deviceId: string;
        deviceName: string;
    } | null = null;
    @state() private _confirmDeleteRemote: TriggerRemoteInfo | null = null;
    /** Which ghost tile is reading a dropped file right now (F10). */
    @state() private _dropBusy: "device" | "remote" | null = null;
    /** A drop whose wig the closet already has a newer version of
     *  (R3, issue 11). Holds the successor's row for USE THE NEWER
     *  ONE, and the dropped bytes and filename for IMPORT THIS FILE
     *  ANYWAY, which has to resend them identically with confirmed
     *  set. Nothing has been written when this is set. */
    @state() private _dropSupersede: {
        block: ReverseSupersessionBlock;
        text: string;
        filename: string;
        kind: "device" | "remote";
    } | null = null;
    // Add Popups signpost 2, Track 5: named-remote expand-view
    // rename-in-place. Single-instance, same shape as the drawer's
    // own _editingDrawerName/_draftDrawerName/_drawerBusy trio --
    // safe because only one card (drawer OR one remote) can be
    // expanded at a time via the shared expandedDeviceId slot.
    @state() private _editingRemoteName = false;
    @state() private _draftRemoteName = "";
    @state() private _remoteNameBusy = false;
    @state() private _duplicateRemoteTarget: TriggerRemoteInfo | null = null;
    // Add Popups signpost 2, Track 5 follow-up: the expand view's
    // own receiver-scope picker (owner bench request 2026-08-14).
    @state() private _remoteReceiversBusy = false;
    // Track 1 item 6: the Remote settings dialog target. Universal --
    // Remotes never had a settings dialog before this item, so unlike
    // the Device gear there's no prior gating logic to generalize.
    @state() private _remoteSettingsTarget: TriggerRemoteInfo | null = null;

    // Receivers, for the trigger rows' scope-chip name resolution (v0.5.7
    // per-trigger scoping). Fetched alongside the capture-provider list in
    // ``_discoverHardware`` -- that method already calls ``listReceivers()``
    // for the emitter-exclusion set but was discarding the list itself.
    @state() private _receivers: ReceiverInfo[] = [];

    // HAIR Triggers drawer identity (name + optional HA device-registry
    // link, Track B item 9). Loaded once the trigger drawer card is
    // expanded, not eagerly -- same lazy-load discipline as
    // ``_expandedDevice``.
    @state() private _triggerDrawer: TriggerDrawerInfo | null = null;
    @state() private _editingDrawerName = false;
    @state() private _draftDrawerName = "";
    @state() private _drawerBusy = false;

    // Drag-to-reorder for trigger rows inside the expanded drawer (grip
    // handle, mirrors ir-device-detail.ts's command-reorder pattern).
    @state() private _triggerRowsVersion = 0;
    private _triggerSortable: Sortable | null = null;
    private _pendingTriggerReorderSave: number | null = null;

    // Sequence-numbered fire-glow tracker (ir-bloom-styles.ts). Replaces
    // the old bare ``setTimeout`` + ``Set`` pair, which let a fast repeat
    // fire's glow get cut short by the first fire's still-pending timeout
    // (v0.7.2 bug, see ir-bloom-styles.ts's module doc).
    private _bloomTracker = new BloomTracker();

    // Drag-to-reorder for the HAIR device cards (whole-card drag, no handle).
    // ``_localDevices`` holds the optimistic order between a drop and the
    // next parent refresh; it is reset to null whenever the parent pushes a
    // fresh ``devices`` property (which is then the source of truth).
    @state() private _devicesVersion = 0;
    @state() private _localDevices: DeviceSummary[] | null = null;
    private _devicesSortable: Sortable | null = null;
    private _pendingDevicesSave: number | null = null;

    /** The trigger-fired subscription, held as the PROMISE rather
     * than as the unsubscribe it resolves to (issue 125).
     *
     * THE RACE. connectedCallback starts a subscribe; `updated` runs
     * before it resolves, sees a null unsubscribe handle, and starts a
     * second one. Both land, both stay, and every fire is delivered
     * twice for the rest of the session: the row counted two per press
     * and the Sniffer, which assigns rather than adds, looked merely
     * one ahead. Restarting fixed it because a fresh element subscribes
     * once, which is exactly why it never reproduced on demand.
     *
     * A promise assigned synchronously closes it. The guard is set in
     * the same tick the subscribe starts, so there is no window for a
     * second caller to find nothing there. */
    private _triggerFiredSub: Promise<() => Promise<void>> | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._discoverHardware();
        void this._loadTriggers();
        void this._loadTriggerDrawer();
        void this._subscribeTriggerFired();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribeTriggerFired();
        this._devicesSortable?.destroy();
        this._devicesSortable = null;
        if (this._pendingDevicesSave !== null) clearTimeout(this._pendingDevicesSave);
        this._triggerSortable?.destroy();
        this._triggerSortable = null;
        if (this._pendingTriggerReorderSave !== null) {
            clearTimeout(this._pendingTriggerReorderSave);
        }
    }

    protected willUpdate(changed: PropertyValues): void {
        // When the parent hands us a fresh device list, adopt it as the
        // source of truth and drop any optimistic local ordering.
        if (changed.has("devices")) {
            this._localDevices = null;
        }
    }

    updated(changed: PropertyValues): void {
        if (changed.has("hass") || changed.has("api")) {
            this._discoverHardware();
        }
        if (changed.has("api") && this.api && !this._triggerFiredSub) {
            void this._loadTriggers();
            void this._loadTriggerDrawer();
            void this._subscribeTriggerFired();
        }
        if (changed.has("triggerRemotes") && this.api) {
            // Add Popups signpost 2, Track 5 bench catch
            // (2026-08-14): the parent hands down a brand new array
            // every time it refreshes this list -- after creating,
            // duplicating, renaming, or deleting a remote. None of
            // those flows live in this component, so without this
            // our own _triggers stays stale and a freshly seeded
            // remote's expand view reads empty until a hard reload.
            void this._loadTriggers();
        }
        if (changed.has("expandedDeviceId")) {
            void this._loadExpandedDevice();
        }
        this._syncDevicesSortable();
        this._syncTriggerSortable();
    }

    /** Attach / detach the device-grid SortableJS instance. */
    private _syncDevicesSortable(): void {
        const grid = this.renderRoot.querySelector(".device-grid") as HTMLElement | null;
        if (grid && !this._devicesSortable) {
            this._attachDevicesSortable(grid);
        } else if (!grid && this._devicesSortable) {
            this._devicesSortable.destroy();
            this._devicesSortable = null;
        }
    }

    private _attachDevicesSortable(grid: HTMLElement): void {
        this._devicesSortable = Sortable.create(grid, {
            // Whole card drags (no grip). ``delay`` keeps a quick click as
            // expand/collapse and a press-and-hold as a drag. The corner
            // duplicate/delete buttons are excluded as drag origins.
            draggable: ".device-card",
            filter: ".card-action",
            preventOnFilter: false,
            delay: 150,
            delayOnTouchOnly: true,
            animation: 150,
            ghostClass: "sortable-ghost",
            onEnd: () => {
                // Read the new order straight from the DOM (robust against
                // the expanded-detail sibling that also lives in the grid).
                const ids = Array.from(
                    grid.querySelectorAll(".device-card"),
                )
                    .map((el) => (el as HTMLElement).dataset.id)
                    .filter((id): id is string => !!id);
                const base = this._localDevices ?? this.devices;
                const byId = new Map(base.map((d) => [d.id, d]));
                const reordered = ids
                    .map((id) => byId.get(id))
                    .filter((d): d is DeviceSummary => !!d);
                if (reordered.length !== base.length) return;
                this._localDevices = reordered;
                this._devicesSortable?.destroy();
                this._devicesSortable = null;
                for (const el of Array.from(
                    grid.querySelectorAll(".device-card, .expanded-detail"),
                )) {
                    el.remove();
                }
                this._devicesVersion++;
                this._scheduleDevicesSave(reordered.map((d) => d.id));
            },
        });
    }

    private _scheduleDevicesSave(deviceIds: string[]): void {
        if (this._pendingDevicesSave !== null) clearTimeout(this._pendingDevicesSave);
        this._pendingDevicesSave = window.setTimeout(async () => {
            this._pendingDevicesSave = null;
            if (!this.api) return;
            try {
                await this.api.reorderDevices(deviceIds);
            } catch {
                // Backend rejected (stale set). Force a parent refresh to
                // resync the canonical order.
                this.dispatchEvent(
                    new CustomEvent("device-changed", {
                        bubbles: true,
                        composed: true,
                    }),
                );
            }
        }, REORDER_DEBOUNCE_MS);
    }

    private async _loadExpandedDevice(): Promise<void> {
        // The trigger drawer's sentinel id shares the parent's expand-one
        // -at-a-time slot but isn't a real device -- ``getDevice`` would
        // 404 on it. ``_loadTriggerDrawer`` (called separately, see
        // ``updated()``) handles that case.
        if (
            !this.expandedDeviceId ||
            this.expandedDeviceId === TRIGGER_DRAWER_ID ||
            // Add Popups signpost 2, Track 5: a named remote shares
            // this same expand-one-at-a-time slot (its own card sets
            // expandedDeviceId to its id) -- getDevice() would 404 on
            // it exactly like it would on TRIGGER_DRAWER_ID above.
            this.triggerRemotes.some((r) => r.id === this.expandedDeviceId) ||
            !this.api
        ) {
            this._expandedDevice = null;
            return;
        }
        try {
            this._expandedDevice = await this.api.getDevice(this.expandedDeviceId);
        } catch {
            this._expandedDevice = null;
        }
    }

    private async _onExpandedDeviceChanged(): Promise<void> {
        await this._loadExpandedDevice();
        this.dispatchEvent(
            new CustomEvent("device-changed", { bubbles: true, composed: true }),
        );
    }

    /**
     * The expanded child refetched its own device; take its copy.
     *
     * The same trade _onCommandsReordered makes, for the same reason:
     * the child has the authoritative object already, so a round-trip
     * here would buy nothing and cost a render. What it prevents is
     * the opposite of a missing refresh -- this cache overwriting a
     * fresher device on its next render (P8).
     *
     * Guarded on the id because the cache belongs to whichever device
     * is expanded NOW. A refresh that resolves after the person has
     * collapsed the card, or opened another one, is about a device
     * this element is no longer showing.
     */
    private _onExpandedDeviceRefreshed(ev: CustomEvent): void {
        const fresh = ev.detail?.device as IRDevice | undefined;
        if (!fresh || fresh.id !== this.expandedDeviceId) return;
        this._expandedDevice = fresh;
    }

    private _onExpandedDeviceDeleted(): void {
        this.dispatchEvent(
            new CustomEvent("device-deleted", { bubbles: true, composed: true }),
        );
    }

    /**
     * Apply a command-order change reported by the child detail view.
     *
     * Updates the cached ``_expandedDevice`` synchronously so the next
     * render passes the new order back down. Skips the full re-fetch
     * round-trip we do on ``device-changed`` because the child already
     * has authoritative local state for this mutation -- and because
     * the server save is debounced and asynchronous, a fetch here would
     * race with the user's in-flight reorder.
     */
    private _onCommandsReordered(ev: CustomEvent): void {
        if (!this._expandedDevice) return;
        const commands = ev.detail?.commands;
        if (!Array.isArray(commands)) return;
        this._expandedDevice = {
            ...this._expandedDevice,
            commands,
        };
    }

    private _onCollapse(): void {
        this.dispatchEvent(
            new CustomEvent("device-selected", {
                detail: this.expandedDeviceId,
                bubbles: true,
                composed: true,
            }),
        );
    }

    private async _discoverHardware(): Promise<void> {
        // Fetch native receiver entity IDs so we can exclude them from emitters.
        const receiverEntityIds = new Set<string>();
        if (this.api) {
            try {
                const receivers = await this.api.listReceivers();
                for (const r of receivers) {
                    receiverEntityIds.add(r.entity_id);
                }
                // Keep the full list too -- ir-trigger-row's scope chip
                // resolves receiver_entity_ids to friendly names from it.
                // (Previously this method only kept the id Set for the
                // emitter-exclusion check below and threw the names away.)
                this._receivers = receivers;
            } catch {
                // Pre-2026.6 or non-fatal error.
            }
        }

        // Emitters from hass.states (exclude receiver entities)
        const states = (this.hass?.states ?? {}) as Record<
            string,
            {
                entity_id: string;
                attributes: { friendly_name?: string; hair_observer?: boolean };
            }
        >;
        const emitters: { entity_id: string; name: string }[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (
                entityId.startsWith("infrared.") &&
                !receiverEntityIds.has(entityId) &&
                !st.attributes.hair_observer
            ) {
                emitters.push({
                    entity_id: entityId,
                    name: st.attributes.friendly_name ?? entityId,
                });
            }
        }
        this._emitters = emitters;

        // Capture providers (RX hardware) from API
        if (this.api) {
            try {
                this._captureProviders = await this.api.listCaptureProviders();
            } catch {
                // Non-fatal
            }
        }

        // Pluckable blasters (vendor IR blasters HAIR can pull codes from).
        if (this.api) {
            try {
                const { vendors, plucked_stores } =
                    await this.api.listPluckVendors();
                this._pluckedStores = plucked_stores ?? [];
                const blasters: {
                    integration: string;
                    entity_id: string;
                    name: string;
                    vendorName: string;
                }[] = [];
                for (const v of vendors) {
                    for (const b of v.blasters) {
                        blasters.push({
                            integration: v.integration,
                            entity_id: b.entity_id,
                            name: b.name,
                            vendorName: v.name,
                        });
                    }
                }
                this._pluckBlasters = blasters;
            } catch {
                this._pluckBlasters = [];
                this._pluckedStores = [];
            }
        }
    }

    /**
     * Forget a plucked store's row.
     *
     * The record only. Every remote that came out of that store stays
     * exactly where it is, which is the same semantics a blaster delete
     * has always had; re-plucking brings the row back and, thanks to
     * the tiered duplicate guard, adds no signals.
     */
    private async _forgetStore(store: PluckedStoreRecord): Promise<void> {
        if (!this.api) return;
        try {
            await this.api.forgetPluckedStore(store.id);
            this._pluckedStores = this._pluckedStores.filter(
                (s) => s.id !== store.id,
            );
        } catch {
            // Non-fatal: the row stays and the next load settles it.
        }
    }

    private _select(deviceId: string) {
        this.dispatchEvent(
            new CustomEvent("device-selected", {
                detail: deviceId,
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _add() {
        this.dispatchEvent(
            new CustomEvent("add-device", { bubbles: true, composed: true }),
        );
    }

    private _openInPlucker(entityId: string): void {
        this.dispatchEvent(
            new CustomEvent("navigate-plucker", {
                detail: { vendor_entity_id: entityId },
                bubbles: true,
                composed: true,
            }),
        );
    }

    // --- Device corner actions (duplicate + delete) ---

    private _openDuplicateDialog(device: DeviceSummary, e: Event): void {
        e.stopPropagation();
        this._duplicateTarget = device;
    }

    private _closeDuplicateDialog(): void {
        this._duplicateTarget = null;
    }

    private _onDeviceDuplicated(): void {
        // Tell the parent panel to refresh its device list. The duplicate
        // already lives in storage server-side; the parent owns the list.
        this._duplicateTarget = null;
        this.dispatchEvent(
            new CustomEvent("device-changed", { bubbles: true, composed: true }),
        );
    }

    private _requestDeleteDevice(device: DeviceSummary, e: Event): void {
        e.stopPropagation();
        this._confirmDeleteDevice = device;
    }

    // --- Trigger remotes (Add Popups signpost 2, Track 4) ---

    private _addRemote(): void {
        this.dispatchEvent(
            new CustomEvent("add-trigger-remote", { bubbles: true, composed: true }),
        );
    }

    /** Ghost tile drop wiring (signpost 3, Track 3 item 3). See the
     *  file header note above the imports for the full design; this
     *  is the funnel call + preselect-or-quiet-fallback itself. Only
     *  the first dropped file is processed -- a drop target names one
     *  file in both the s11 mock and the Track 3.3 bench, and looping
     *  multiple files into an ambiguous multi-preselect isn't worth
     *  building for a case nothing exercises. */
    private async _onGhostTileDrop(
        kind: "device" | "remote",
        e: CustomEvent<{ files: File[] }>,
    ): Promise<void> {
        const file = e.detail.files[0];
        if (!file || !this.api) return;
        // Before anything else: the tile says it is working. Reading,
        // parsing, combing and writing all happen before the dialog
        // can open, and that gap used to be silent (issue 6).
        this._dropBusy = kind;
        let text: string;
        try {
            text = await file.text();
        } catch {
            this._dropBusy = null;
            return;
        }
        try {
            const result = await this.api.wigsUpload(text, file.name);
            // THE DROP ANSWERS (R3, issue 11). This used to be a bare
            // return, and it ate the drop: the closet holds a newer
            // version of the wig, wigs/upload writes nothing and says
            // so, and the tile just stopped. Pre-existing since this
            // path was built and unreachable until repairs started
            // minting successors, at which point the owner dropped a
            // file and watched a spinner turn into nothing.
            //
            // What the person is doing here is creating a device, so
            // the offer leads with the wig they almost certainly want
            // (owner ruled): use the newer one, import this file
            // anyway, or cancel.
            if (result.reverse_supersession) {
                this._dropSupersede = {
                    block: result.reverse_supersession,
                    text,
                    filename: file.name,
                    kind,
                };
                return;
            }
            this._landedFromDrop(kind, result);
        } catch (err) {
            this._dropFailed((err as Error).message);
        } finally {
            this._dropBusy = null;
        }
    }

    /** A drop that actually filed: hand its row to the create dialog.
     *  Shared by the ordinary path and by IMPORT THIS FILE ANYWAY,
     *  which files the same bytes a second time with confirmed set and
     *  then continues exactly here. */
    private _landedFromDrop(
        kind: "device" | "remote",
        result: Awaited<ReturnType<HairApi["wigsUpload"]>>,
    ): void {
        if (!result.success) {
            this._dropFailed((result.errors ?? []).join("; "));
            return;
        }
        const landed = result.files ?? [];
        if (landed.length !== 1) return;
        this._offerWig(kind, landed[0]);
    }

    private _dropFailed(reason: string): void {
        this.dispatchEvent(
            new CustomEvent("drop-upload-failed", {
                detail: t("wigs.upload_failed", { reason }),
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** Build the picker row and open the create dialog on it.
     *
     * The upload already knows this row (B4). It used to be fetched
     * back out of a full wigs/list, which re-scans and re-parses every
     * wig in the closet -- claims, receipts and matrix summaries for
     * each -- to find the one file this path has known the name of
     * since the write.
     *
     * The same shape arrives from two places now: a landed file's own
     * entry, and (R3) the superseding wig's row on a
     * reverse-supersession answer. Both come out of one function on
     * the server, so one reader here is right for both.
     *
     * notes and origin are on neither answer and nothing on this path
     * reads them; they are null here rather than guessed, and the
     * closet's own list still serves the full record everywhere else. */
    private _offerWig(
        kind: "device" | "remote",
        entry: {
            filename: string;
            name: string;
            brand: string | null;
            model?: string | null;
            kind?: string | null;
            signal_count?: number;
            matrix?: MatrixSummary | null;
            comb?: CombSummary | null;
        },
    ): void {
        const wig: WigInfo = {
            filename: entry.filename,
            name: entry.name,
            brand: entry.brand,
            model: entry.model ?? null,
            notes: null,
            origin: null,
            signal_count: entry.signal_count ?? 0,
            kind: entry.kind ?? null,
            matrix: entry.matrix ?? null,
            comb: entry.comb ?? null,
        };
        const row: WigPickRow = {
            source: "local",
            id: `wig:${wig.filename}`,
            label: wig.name,
            signalCount: wig.signal_count,
            wig,
            brand: null,
            codebook: null,
        };
        this.dispatchEvent(
            new CustomEvent(
                kind === "device" ? "add-device" : "add-trigger-remote",
                {
                    detail: { dropSource: row },
                    bubbles: true,
                    composed: true,
                },
            ),
        );
    }

    /** USE THE NEWER ONE: straight into the create dialog on the
     *  successor's row. Nothing files -- the dropped file is not
     *  written, which is the same thing Cancel does to it. */
    private _onDropUseNewer(): void {
        const held = this._dropSupersede;
        if (!held) return;
        this._dropSupersede = null;
        this._offerWig(held.kind, {
            ...held.block,
            brand: held.block.brand ?? null,
        });
    }

    /** IMPORT THIS FILE ANYWAY: resend the identical bytes with
     *  confirmed set, which is the one thing that gets past the
     *  reverse check, then continue with the file that just filed. */
    private async _onDropImportAnyway(): Promise<void> {
        const held = this._dropSupersede;
        if (!held || !this.api) return;
        this._dropSupersede = null;
        this._dropBusy = held.kind;
        try {
            const result = await this.api.wigsUpload(
                held.text, held.filename, true,
            );
            this._landedFromDrop(held.kind, result);
        } catch (err) {
            this._dropFailed((err as Error).message);
        } finally {
            this._dropBusy = null;
        }
    }

    private _renderDropSupersede() {
        const held = this._dropSupersede;
        if (!held) return nothing;
        return html`<ir-confirm-dialog
            title=${t("supersede.drop_newer_title")}
            message=${t("supersede.drop_newer_message", {
                name: held.block.name,
            })}
            confirmLabel=${t("supersede.drop_newer_use")}
            altLabel=${t("supersede.drop_newer_import")}
            @confirmed=${this._onDropUseNewer}
            @alt-action=${this._onDropImportAnyway}
            @closed=${() => (this._dropSupersede = null)}
        ></ir-confirm-dialog>`;
    }

    private _requestDeleteRemote(remote: TriggerRemoteInfo, e: Event): void {
        e.stopPropagation();
        this._confirmDeleteRemote = remote;
    }

    private async _doDeleteRemote(): Promise<void> {
        if (!this._confirmDeleteRemote || !this.api) return;
        const remote = this._confirmDeleteRemote;
        this._confirmDeleteRemote = null;
        try {
            await this.api.deleteTriggerRemote(remote.id);
            this.dispatchEvent(
                new CustomEvent("remote-deleted", { bubbles: true, composed: true }),
            );
        } catch {
            // Non-fatal; parent refresh will reconcile.
        }
    }

    // --- Named remote rename-in-place (Track 5, mirrors the drawer's
    //     own _startEditDrawerName/_saveDrawerName/_onDrawerNameKeydown
    //     trio further down this file) ---

    private _startEditRemoteName(remote: TriggerRemoteInfo, e: Event): void {
        e.stopPropagation();
        if (this._remoteNameBusy) return;
        this._draftRemoteName = remote.name;
        this._editingRemoteName = true;
        void this.updateComplete.then(() => {
            const input = this.renderRoot.querySelector<HTMLInputElement>(
                ".remote-name-input",
            );
            input?.focus();
            input?.select();
        });
    }

    private async _saveRemoteName(): Promise<void> {
        if (!this._editingRemoteName) return;
        const name = this._draftRemoteName.trim();
        this._editingRemoteName = false;
        const remoteId = this.expandedDeviceId;
        const current = this.triggerRemotes.find((r) => r.id === remoteId);
        if (!name || !this.api || !remoteId || name === current?.name) return;
        this._remoteNameBusy = true;
        try {
            await this.api.renameTriggerRemote(remoteId, name);
            this.dispatchEvent(
                new CustomEvent("remote-renamed", { bubbles: true, composed: true }),
            );
        } catch {
            // Non-fatal; the header reverts to the parent-refreshed name.
        } finally {
            this._remoteNameBusy = false;
        }
    }

    private _onRemoteNameKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            e.preventDefault();
            void this._saveRemoteName();
        } else if (e.key === "Escape") {
            this._editingRemoteName = false;
        }
    }

    // --- Named remote duplicate (Track 5, mirrors
    //     _openDuplicateDialog/_closeDuplicateDialog/_onDeviceDuplicated
    //     further down this file, device-card's own corner action) ---

    private _openDuplicateRemoteDialog(
        remote: TriggerRemoteInfo,
        e: Event,
    ): void {
        e.stopPropagation();
        this._duplicateRemoteTarget = remote;
    }

    private _closeDuplicateRemoteDialog(): void {
        this._duplicateRemoteTarget = null;
    }

    private _onRemoteDuplicated(): void {
        this._duplicateRemoteTarget = null;
        this.dispatchEvent(
            new CustomEvent("remote-duplicated", { bubbles: true, composed: true }),
        );
    }

    // --- Mirror-door mints (signpost 3, Track 3.5, owner-directed
    //     2026-08-15): "Make a Remote" (device -> remote) and
    //     "Make a Device" (remote -> device). Both mint dialogs
    //     already dispatch the generic remote-created/device-created
    //     events on success (every other door through them does the
    //     same); these handlers just close the source state and let
    //     that bubble on up to ha-panel-ir-devices.ts's own
    //     _onRemoteChanged/_onDeviceChanged refresh. ---

    private _onMakeRemoteRequested(device: IRDevice | null): void {
        this._makeRemoteSource = device;
    }

    private _closeMakeRemoteDialog(): void {
        this._makeRemoteSource = null;
    }

    private _onRemoteMinted(e: CustomEvent<TriggerRemoteInfo>): void {
        const source = this._makeRemoteSource;
        this._makeRemoteSource = null;
        // Mirror-door mint: the source device IS the new remote's
        // counterpart by construction (owner ruling 2026-08-15), no
        // matching to do. e.detail is only populated on this
        // sourceDeviceId branch (see ir-promote-remote-dialog.ts).
        if (PINNING_UI_ENABLED && source && e.detail) {
            this._pinPromptTarget = {
                remoteId: e.detail.id,
                remoteName: e.detail.name,
                deviceId: source.id,
                deviceName: source.name,
            };
        }
    }

    /** The mirror-door pin prompt was accepted (punch list item 19).
     *
     * A pin is one fact standing on TWO objects: the remote gains the
     * device in its pinned list, the device gains the remote in its
     * own. Both of those lists are owned by the panel shell and passed
     * down as properties, and nothing was asking it to re-read either
     * one after the pin call returned -- so the freshly minted object
     * opened with empty pin chips, and its counterpart did not show
     * the new pin either, until a page refresh proved the storage side
     * had been right all along.
     *
     * Both sides are told, not one: whichever object the user opens
     * next, the mint could have gone in either direction. */
    private _onPinPromptPinned(): void {
        this._pinPromptTarget = null;
        this.dispatchEvent(
            new CustomEvent("remote-pins-changed", {
                bubbles: true,
                composed: true,
            }),
        );
        this.dispatchEvent(
            new CustomEvent("device-changed", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _onMakeDeviceRequested(remote: TriggerRemoteInfo | null): void {
        this._makeDeviceSource = remote;
    }

    private _closeMakeDeviceDialog(): void {
        this._makeDeviceSource = null;
    }

    private _onDeviceMinted(e: CustomEvent<IRDevice>): void {
        const source = this._makeDeviceSource;
        this._makeDeviceSource = null;
        if (PINNING_UI_ENABLED && source && e.detail) {
            this._pinPromptTarget = {
                remoteId: source.id,
                remoteName: source.name,
                deviceId: e.detail.id,
                deviceName: e.detail.name,
            };
        }
    }

    /** Non-matrix-cell command count, for the mint dialog's preview
     *  line only -- ws_device_make_remote applies the authoritative
     *  filter server-side regardless (THE MATRIX RULE). */
    private _eligibleCommandCount(device: IRDevice): number {
        return device.commands.filter((c) => !c.matrix_cell).length;
    }

    // --- Named remote receiver scope (Track 5 follow-up, mirrors
    //     ir-device-detail.ts's _onEmittersChanged) ---

    /** Every known receiver (this._receivers -- already loaded, no new
     *  fetch), mapped to header-chip-group's row shape. Two states
     *  only, same as ir-receiver-picker.ts: receivers carry no
     *  availability flag to key a `down` state on. */
    private _receiverRows(remote: TriggerRemoteInfo): HeaderChipRow[] {
        return this._receivers.map((r) => ({
            id: r.entity_id,
            name: r.name,
            on: remote.receiver_scope.includes(r.entity_id),
        }));
    }

    /** Rows for a Remote detail's Pin: group -- candidates are
     *  Devices, `on` read from that remote's stored pin list (signpost
     *  4, Track 4). Takes the remote explicitly because several remote
     *  cards can be on screen and each has its own pins. */
    private _pinRows(remote: TriggerRemoteInfo): HeaderChipRow[] {
        const pinned = new Set(remote.pinned_device_ids ?? []);
        return this.devices.map((d) => ({
            id: d.id,
            name: d.name,
            on: pinned.has(d.id),
        }));
    }

    /** Pin or unpin whichever Device's chip moved on this Remote.
     *
     * Mirror image of the Device detail's handler: the group reports
     * the full new "on" list, the delta names the device that changed,
     * and the parent refetches so the chips show stored truth. */
    private async _onRemotePinsChanged(
        remote: TriggerRemoteInfo,
        e: CustomEvent<{ value: string[] }>,
    ): Promise<void> {
        if (!this.api) return;
        const next = new Set(e.detail.value);
        const before = new Set(remote.pinned_device_ids ?? []);
        const added = [...next].filter((id) => !before.has(id));
        const removed = [...before].filter((id) => !next.has(id));
        try {
            for (const deviceId of added) {
                await this.api.pinTriggerRemoteDevice(remote.id, deviceId);
            }
            for (const deviceId of removed) {
                await this.api.unpinTriggerRemoteDevice(remote.id, deviceId);
            }
        } finally {
            this.dispatchEvent(
                new CustomEvent("remote-pins-changed", {
                    bubbles: true,
                    composed: true,
                }),
            );
        }
    }

    private async _onRemoteReceiversChanged(
        remote: TriggerRemoteInfo,
        e: CustomEvent<{ value: string[] }>,
    ): Promise<void> {
        if (!this.api) return;
        this._remoteReceiversBusy = true;
        try {
            await this.api.setTriggerRemoteReceiverScope(
                remote.id,
                e.detail.value,
            );
            this.dispatchEvent(
                new CustomEvent("remote-receivers-changed", {
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch {
            // Non-fatal; the picker reverts once the parent refresh
            // hands back the server-confirmed scope.
        } finally {
            this._remoteReceiversBusy = false;
        }
    }

    private async _doDeleteDevice(): Promise<void> {
        if (!this._confirmDeleteDevice || !this.api) return;
        const device = this._confirmDeleteDevice;
        this._confirmDeleteDevice = null;
        try {
            await this.api.deleteDevice(device.id);
            this.dispatchEvent(
                new CustomEvent("device-deleted", { bubbles: true, composed: true }),
            );
        } catch {
            // Non-fatal; parent refresh will reconcile.
        }
    }

    private _navigateIntegration(domain: string) {
        const url = `/config/integrations/integration/${domain}`;
        window.history.pushState(null, "", url);
        window.dispatchEvent(new PopStateEvent("popstate"));
    }

    // --- Triggers ---

    /**
     * Number of trigger remotes: the HAIR Triggers drawer plus every
     * named remote. The header counts remotes, not the triggers living
     * inside them (owner ruling 2026-08-14: "each remote card has their
     * own numbered triggers on it") -- multi-drawer support shipped in
     * this track, so this is no longer the hardcoded 1 it was before.
     */
    private get _triggerDrawerCount(): number {
        return 1 + this.triggerRemotes.length;
    }

    private async _loadTriggers(): Promise<void> {
        if (!this.api) return;
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
    }

    // Add Popups signpost 2, Track 5: listTriggers() returns every
    // trigger system-wide, drawer- and remote-owned alike (same flat
    // list ws_get_triggers has always returned). Before this track
    // the drawer's own expand view rendered that whole list
    // unfiltered -- harmless while no named remote had triggers to
    // leak, but wrong now that they do. These two views split it.
    private get _drawerTriggers(): IRTrigger[] {
        return this._triggers.filter((trig) => !trig.trigger_remote_id);
    }

    private _remoteTriggers(remoteId: string): IRTrigger[] {
        return this._triggers.filter(
            (trig) => trig.trigger_remote_id === remoteId,
        );
    }

    private async _subscribeTriggerFired(): Promise<void> {
        if (!this.api || this._triggerFiredSub) return;
        try {
            this._triggerFiredSub = this.api.subscribeTriggerFired(
                (ev: TriggerFiredEvent) => {
                    // One channel, two kinds of news (signpost 4, Track M):
                    // a matrix Remote's heard state rides this same
                    // subscription with kind "state_heard". It is not a
                    // fire, so none of the trigger bookkeeping below
                    // applies -- but the remote it names now holds a new
                    // last_heard, and that one stored fact is what the
                    // card's rest ring, its slim readout and the LAST
                    // HEARD row all render from. Ask the shell for a
                    // fresh remote list (the one-call rule: last_heard
                    // rides the list payload, there is no per-remote
                    // follow-up), and the new value reaching the card as
                    // a property is what blooms it.
                    if (ev.kind === "state_heard") {
                        this.dispatchEvent(
                            new CustomEvent("remote-state-heard", {
                                bubbles: true,
                                composed: true,
                            }),
                        );
                        return;
                    }
                    if (ev.kind) return;
                    // Glow the collapsed drawer card and the fired row alike
                    // (BloomTracker's sequence numbering is what fixes the
                    // v0.7.2 repeat-fire-cut-short bug -- see
                    // ir-bloom-styles.ts's module doc).
                    this._bloomTracker.trigger(
                        ev.trigger_id,
                        () => {
                            this._glowTriggerIds = new Set([
                                ...this._glowTriggerIds,
                                ev.trigger_id,
                            ]);
                        },
                        () => {
                            const next = new Set(this._glowTriggerIds);
                            next.delete(ev.trigger_id);
                            this._glowTriggerIds = next;
                        },
                    );
                    // ASSIGN, DO NOT ADD (issue 125). The push
                    // carries the store's own fire_count taken after
                    // the fire, and its timestamp is the instant
                    // last_fired_at was stamped with, so the row shows
                    // the two facts the backend actually holds. It
                    // still updates without waiting on a full
                    // _loadTriggers() round-trip, which is the whole
                    // point of doing it here; what it no longer does
                    // is compute a number of its own that only a
                    // restart could correct.
                    this._triggers = this._triggers.map((t) =>
                        t.id === ev.trigger_id
                            ? {
                                  ...t,
                                  fire_count: ev.fire_count,
                                  last_fired_at: ev.timestamp,
                              }
                            : t,
                    );
                },
            );
            await this._triggerFiredSub;
        } catch {
            // Non-fatal, and it lets a later attempt try again.
            this._triggerFiredSub = null;
        }
    }

    private async _unsubscribeTriggerFired(): Promise<void> {
        const pending = this._triggerFiredSub;
        this._triggerFiredSub = null;
        if (!pending) return;
        try {
            // Awaited, not skipped: tearing down while the subscribe
            // is still in flight is the other half of the same race,
            // and dropping the handle there would leave a live
            // subscription behind on a page the person has left.
            const unsub = await pending;
            await unsub();
        } catch {
            // Never landed; there is nothing to tear down.
        }
    }

    private _openEditTrigger(trigger: IRTrigger, e?: Event): void {
        e?.stopPropagation();
        this._editTrigger = trigger;
    }

    private _closeEditTrigger(): void {
        this._editTrigger = null;
    }

    private async _onTriggerUpdated(): Promise<void> {
        this._editTrigger = null;
        await this._loadTriggers();
    }

    // --- The three doors onto a state trigger (signpost 4, Track M) ---
    //
    // A matrix Remote can mint a trigger from a cell in three places,
    // and the handoff is explicit that all three land in the SAME
    // dialog, pre-aimed at this remote and pre-filled from the cell.
    // Two of them (the card's action bar) already hold coordinates; the
    // third (the LAST HEARD row) holds a stored heard state, which
    // carries the very same coordinates. So both shapes fold into one
    // coordinate pick, one fetch, one dialog -- rather than three code
    // paths that would have to be kept saying the same thing.
    //
    // The fetch is what the cell browser's no-bytes contract requires:
    // the lattice ships without Pronto, so the door asks for the single
    // cell it is about to use. Coordinates come from the card or the
    // stored fact verbatim, never re-derived from the display name.

    // A matrix cell's code is Pronto by construction -- a wig file
    // stores nothing else -- and ``protocol`` on a trigger is the
    // TRANSPORT, which is what ir-trigger-row gates its S/L diamond
    // line on and what the dialog gates its own preview on. Not to be
    // confused with the endpoint's ``decoded_protocol``, which is the
    // decoder's name for the frame and is null for every AC lattice
    // frame in the corpus; feeding that into this prop cost the minted
    // row both its protocol chip and its whole fingerprint line.
    // (Bench, 2026-08-17.)
    private async _mintFromMatrix(
        remoteId: string,
        pick: {
            mode: string | null;
            fan: string | null;
            swing: string | null;
            temp: number | null;
            power: "on" | "off" | null;
        },
    ): Promise<void> {
        if (!this.api) return;
        try {
            const detail = await this.api.remoteMatrixCell(remoteId, pick);
            this._mintTrigger = { remoteId, detail };
        } catch {
            // The cell stopped resolving between the card drawing it
            // and the click (a matrix file edited underneath, a remote
            // deleted in another tab). Non-fatal: no dialog opens, and
            // the card is still showing the truth it last fetched.
        }
    }

    /** Door 1: the LAST HEARD row's + Trigger. */
    private _onLastHeardTrigger(remoteId: string, heard: LastHeard): void {
        void this._mintFromMatrix(remoteId, {
            mode: heard.mode,
            fan: heard.fan,
            swing: heard.swing,
            temp: heard.temp,
            power: heard.power,
        });
    }

    /** Doors 2 and 3: the card's action bar, on a browsed cell that
     * has been heard and on one that never has. They are the same
     * door as far as minting goes -- the card reports what is browsed
     * and the browse is what gets minted, heard or not. That the
     * never-heard case works at all is the point of the card
     * rendering live from the start. */
    private _onMatrixSaveTrigger(
        remoteId: string,
        ev: CustomEvent<MatrixCardPick>,
    ): void {
        const p = ev.detail;
        void this._mintFromMatrix(remoteId, {
            mode: p.mode,
            fan: p.fan,
            swing: p.swing,
            temp: p.temp,
            power: p.power,
        });
    }

    private _closeMintTrigger(): void {
        this._mintTrigger = null;
    }

    private async _onMintTriggerSaved(): Promise<void> {
        this._mintTrigger = null;
        await this._loadTriggers();
        // The remote's own trigger_count and badge line live on the
        // parent-owned remote list, the same reason a toggle tells the
        // shell to refetch.
        this.dispatchEvent(
            new CustomEvent("remote-trigger-toggled", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    private async _toggleTriggerEnabled(trigger: IRTrigger, e?: Event): Promise<void> {
        e?.stopPropagation();
        try {
            await this.api!.updateTrigger(trigger.id, {
                enabled: !trigger.enabled,
            });
            await this._loadTriggers();
            // Punch list item 3 (signpost 3 bench round, 2026-08-17):
            // _loadTriggers() only refreshes this drawer's own trigger
            // rows. The Remote card's ON:/OFF: badges read `triggerRemotes`,
            // a property the panel shell owns and only re-fetches on its
            // own remote-* events -- tell it this one changed too, same
            // as remote-renamed/remote-duplicated/remote-receivers-changed.
            this.dispatchEvent(
                new CustomEvent("remote-trigger-toggled", { bubbles: true, composed: true }),
            );
        } catch {
            // Non-fatal.
        }
    }

    private _requestDeleteTrigger(trigger: IRTrigger, e?: Event): void {
        e?.stopPropagation();
        this._confirmDeleteTrigger = trigger;
    }

    private async _doDeleteTrigger(): Promise<void> {
        if (!this._confirmDeleteTrigger) return;
        const trigger = this._confirmDeleteTrigger;
        this._confirmDeleteTrigger = null;
        try {
            await this.api!.deleteTrigger(trigger.id);
            await this._loadTriggers();
        } catch {
            // Non-fatal.
        }
    }

    /** ``rename-trigger`` from an ``<ir-trigger-row>`` -- rides the same
     *  ``updateTrigger`` patch path the edit dialog uses (device_trigger.py's
     *  alias-history tolerance already covers a plain name patch). */
    private async _onRenameTrigger(
        ev: CustomEvent<{ trigger: IRTrigger; name: string }>,
    ): Promise<void> {
        const { trigger, name } = ev.detail;
        if (!this.api) return;
        try {
            await this.api.updateTrigger(trigger.id, { name });
            await this._loadTriggers();
        } catch {
            // Non-fatal; the row reverts to the server-confirmed name on
            // the next render since it reads straight off this._triggers.
        }
    }

    // --- HAIR Triggers drawer identity (name + go-to-HA link) ---

    private async _loadTriggerDrawer(): Promise<void> {
        if (!this.api) {
            this._triggerDrawer = null;
            return;
        }
        try {
            this._triggerDrawer = await this.api.getTriggerDrawer();
        } catch {
            this._triggerDrawer = null;
        }
    }

    private _startEditDrawerName(e: Event): void {
        e.stopPropagation();
        if (this._drawerBusy || !this._triggerDrawer) return;
        this._draftDrawerName = this._triggerDrawer.name;
        this._editingDrawerName = true;
        void this.updateComplete.then(() => {
            const input = this.renderRoot.querySelector<HTMLInputElement>(
                ".drawer-name-input",
            );
            input?.focus();
            input?.select();
        });
    }

    private async _saveDrawerName(): Promise<void> {
        if (!this._editingDrawerName) return;
        const name = this._draftDrawerName.trim();
        this._editingDrawerName = false;
        if (!name || !this.api || name === this._triggerDrawer?.name) return;
        this._drawerBusy = true;
        try {
            this._triggerDrawer = await this.api.renameTriggerDrawer(name);
        } catch {
            // Non-fatal; keeps the prior drawer name displayed.
        } finally {
            this._drawerBusy = false;
        }
    }

    private _onDrawerNameKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            e.preventDefault();
            void this._saveDrawerName();
        } else if (e.key === "Escape") {
            this._editingDrawerName = false;
        }
    }

    // --- Trigger row drag reorder (grip handle, mirrors
    //     ir-device-detail.ts's command-reorder pattern) ---

    private _syncTriggerSortable(): void {
        const list = this.renderRoot.querySelector(
            ".trigger-rows",
        ) as HTMLElement | null;
        if (list && !this._triggerSortable) {
            this._attachTriggerSortable(list);
        } else if (!list && this._triggerSortable) {
            this._triggerSortable.destroy();
            this._triggerSortable = null;
        }
    }

    private _attachTriggerSortable(list: HTMLElement): void {
        this._triggerSortable = Sortable.create(list, {
            handle: ".grip-handle",
            animation: 150,
            ghostClass: "sortable-ghost",
            onEnd: (e) => {
                const oldIndex = e.oldIndex;
                const newIndex = e.newIndex;
                if (
                    oldIndex === undefined ||
                    newIndex === undefined ||
                    oldIndex === newIndex
                ) {
                    return;
                }
                // Add Popups signpost 2, Track 5 bench catch
                // (2026-08-14): .trigger-rows now renders either the
                // drawer's own triggers or one named remote's, never
                // the full this._triggers list -- so oldIndex/
                // newIndex from SortableJS are positions WITHIN that
                // subset, not the full array. Reorder the subset,
                // then splice it back into the full list in place
                // (every trigger outside the subset keeps its exact
                // slot) so the save below still sends the complete
                // ordering store.reorder_triggers requires.
                const remoteId = this.expandedDeviceId;
                const inSubset =
                    remoteId && remoteId !== TRIGGER_DRAWER_ID
                        ? (t: IRTrigger) => t.trigger_remote_id === remoteId
                        : (t: IRTrigger) => !t.trigger_remote_id;
                const subset = this._triggers.filter(inSubset);
                const [moved] = subset.splice(oldIndex, 1);
                subset.splice(newIndex, 0, moved);
                const queue = [...subset];
                const triggers = this._triggers.map((t) =>
                    inSubset(t) ? queue.shift()! : t,
                );
                this._triggers = triggers;

                // Tear down and let ``updated()`` re-attach against a
                // fresh ``.trigger-rows`` DOM tree, same discipline as
                // ir-device-detail.ts's command reorder -- avoids
                // SortableJS leaving the dragged row outside keyed()'s
                // managed range after the rebuild.
                this._triggerSortable?.destroy();
                this._triggerSortable = null;
                const container = this.renderRoot.querySelector(
                    ".trigger-rows",
                );
                if (container) {
                    for (const row of Array.from(
                        container.querySelectorAll("ir-trigger-row"),
                    )) {
                        row.remove();
                    }
                }
                this._triggerRowsVersion++;
                this._scheduleTriggerReorderSave(triggers.map((t) => t.id));
            },
        });
    }

    private _scheduleTriggerReorderSave(triggerIds: string[]): void {
        if (this._pendingTriggerReorderSave !== null) {
            clearTimeout(this._pendingTriggerReorderSave);
        }
        this._pendingTriggerReorderSave = window.setTimeout(async () => {
            this._pendingTriggerReorderSave = null;
            if (!this.api) return;
            try {
                await this.api.reorderTriggers(triggerIds);
            } catch {
                // Backend rejected (stale set) -- resync from server.
                await this._loadTriggers();
            }
        }, REORDER_DEBOUNCE_MS);
    }

    private _emitterIntegrationDomain(entityId: string): string {
        const entityReg = this.hass?.entities?.[entityId];
        if (entityReg?.platform) return entityReg.platform;
        return entityId.split(".")[0];
    }

    /** Device-registry IDs that have an emitter entity (TX capable). */
    private _getEmitterDeviceIds(): Set<string> {
        const ids = new Set<string>();
        for (const em of this._emitters) {
            const reg = this.hass?.entities?.[em.entity_id];
            if (reg?.device_id) ids.add(reg.device_id);
        }
        return ids;
    }

    /** Group emitter entity_ids by their HA device_id. */
    private _getEmitterEntityIdsByDevice(): Map<string, string[]> {
        const byDevice = new Map<string, string[]>();
        for (const em of this._emitters) {
            const reg = this.hass?.entities?.[em.entity_id];
            const deviceId = reg?.device_id;
            if (!deviceId) continue;
            const list = byDevice.get(deviceId) ?? [];
            list.push(em.entity_id);
            byDevice.set(deviceId, list);
        }
        return byDevice;
    }

    /** Detect HA versions older than 2026.6 (no native InfraredReceiverEntity). */
    private _isPre2026_6(): boolean {
        const v: string | undefined = this.hass?.config?.version;
        if (!v) return false;
        const m = v.match(/^(\d+)\.(\d+)/);
        if (!m) return false;
        const major = parseInt(m[1], 10);
        const minor = parseInt(m[2], 10);
        return major < 2026 || (major === 2026 && minor < 6);
    }

    /** Resolve integration domain for navigation. */
    private _resolveNavType(
        cp: CaptureProviderInfo,
        nativeEntityId: string | undefined,
    ): string {
        if (cp.type === "native" && nativeEntityId) {
            const platform = this.hass?.entities?.[nativeEntityId]?.platform;
            if (platform) return platform;
            // Fall back to esphome -- by far the most common source of
            // InfraredReceiverEntity in the wild.
            return "esphome";
        }
        return cp.type;
    }

    /**
     * Classify capture providers, merging native + bridge entries for the
     * same physical HA device into one entry with both flags set.
     *
     * Receivers = every capture-capable device.
     * Proxies   = subset that also has an emitter on the same HA device.
     * A TX+RX device shows in both sections by design (each section answers
     * a different question; same hardware legitimately answers both).
     */
    private _classifyHardware(): {
        receivers: MergedHardwareEntry[];
        proxies: MergedHardwareEntry[];
    } {
        const txByDevice = this._getEmitterEntityIdsByDevice();
        const txDeviceIds = new Set(txByDevice.keys());
        const byDeviceId = new Map<string, MergedHardwareEntry>();

        for (const cp of this._captureProviders) {
            // For native providers the backend stashes the entity_id in
            // ``cp.device_id``; the real HA device-registry ID has to be
            // looked up via ``hass.entities``.
            let haDeviceId: string | undefined;
            let nativeEntityId: string | undefined;
            if (cp.type === "native") {
                nativeEntityId = cp.receiver_entity_id ?? cp.device_id;
                haDeviceId = this.hass?.entities?.[nativeEntityId]?.device_id;
                // Fallback: use the entity_id as a synthetic merge key so
                // the card still shows even if the entity isn't registered.
                if (!haDeviceId) haDeviceId = nativeEntityId;
            } else {
                haDeviceId = cp.device_id;
            }
            if (!haDeviceId) continue;

            const existing = byDeviceId.get(haDeviceId);
            const entry: MergedHardwareEntry = existing ?? {
                device_id: haDeviceId,
                name: cp.name,
                nav_type: this._resolveNavType(cp, nativeEntityId),
                has_native: false,
                has_bridge: false,
                has_tx: txDeviceIds.has(haDeviceId),
                tx_entity_ids: txByDevice.get(haDeviceId) ?? [],
            };
            if (cp.type === "native") {
                entry.has_native = true;
                entry.native_entity_id = nativeEntityId;
            } else {
                // ESPHome event-bus bridge or Broadlink learn mode.
                entry.has_bridge = true;
                // Prefer the bridge's device-registry name (cleaner) and
                // its concrete integration domain over any native default.
                entry.name = cp.name;
                entry.nav_type = cp.type;
            }
            byDeviceId.set(haDeviceId, entry);
        }

        const merged = Array.from(byDeviceId.values());
        const proxies = merged.filter((e) => e.has_tx);
        return { receivers: merged, proxies };
    }

    /** Render TX/RX-NATIVE / RX-BRIDGE badges with a pre-2026.6 upgrade hint. */
    private _renderRxBadges(entry: MergedHardwareEntry) {
        const showGrayedNative =
            !entry.has_native && entry.has_bridge && this._isPre2026_6();
        return html`
            ${entry.has_native
                ? html`<span
                      class="badge rx-native"
                      title=${t("devlist.rx_native_title")}
                  >RX-NATIVE</span>`
                : nothing}
            ${entry.has_bridge
                ? html`<span
                      class="badge rx-bridge"
                      title=${entry.has_native
                          ? t("devlist.rx_bridge_active")
                          : t("devlist.rx_bridge_title")}
                  >RX-BRIDGE</span>`
                : nothing}
            ${showGrayedNative
                ? html`<span
                      class="badge rx-native-disabled"
                      title=${t("devlist.rx_upgrade_title")}
                  >RX-NATIVE</span>`
                : nothing}
        `;
    }

    render() {
        if (this.loading) {
            return html`<div class="loading">${t("devlist.loading")}</div>`;
        }

        const devices = this._localDevices ?? this.devices;
        const hasDevices = devices.length > 0;
        const hasEmitters = this._emitters.length > 0;
        const { receivers, proxies } = this._classifyHardware();
        const hasReceivers = receivers.length > 0;
        const hasProxies = proxies.length > 0;
        const hasNothing = !hasDevices && !hasEmitters && !hasReceivers && !hasProxies;

        if (hasNothing) {
            return html`
                <ha-card class="empty">
                    <h2>${t("devlist.empty_title")}</h2>
                    <p>${t("devlist.empty_sub")}</p>
                    <mwc-button raised @click=${this._add}>${t("devlist.add_device_plus")}</mwc-button>
                </ha-card>
            `;
        }

        return html`
            <!-- Devices -->
            <div class="toolbar">
                <div class="toolbar-title-group">
                    <span class="toolbar-title">
                        <ha-svg-icon .path=${ICON_DEVICES_TV} .viewBox=${TV_VIEWBOX}></ha-svg-icon>
                        ${t("devlist.title")}
                        <span class="toolbar-count">(${this.devices.length})</span>
                        <span class="toolbar-tagline">- ${t("devlist.tagline")}</span>
                    </span>
                </div>
            </div>
            ${hasDevices
                ? html`
                      <div class="grid device-grid">
                          ${keyed(
                              this._devicesVersion,
                              repeat(
                                  devices,
                                  (device) => device.id,
                                  (device) => html`
                                  <div
                                      class="card device-card ${device.id === this.expandedDeviceId ? "expanded" : ""}"
                                      data-id=${device.id}
                                      tabindex="0"
                                      @click=${() => this._select(device.id)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._select(device.id);
                                          }
                                      }}
                                  >
                                      <button
                                          class="card-action duplicate-action"
                                          title=${t("dup.heading")}
                                          @click=${(e: Event) =>
                                              this._openDuplicateDialog(device, e)}
                                      >
                                          <ha-svg-icon .path=${ICON_COPY}></ha-svg-icon>
                                      </button>
                                      <button
                                          class="card-action delete-action"
                                          title=${t("devlist.delete_device")}
                                          @click=${(e: Event) =>
                                              this._requestDeleteDevice(device, e)}
                                      >
                                          <ha-svg-icon
                                              .path=${ICON_TRASH}
                                              .viewBox=${TRASH_VIEWBOX}
                                          ></ha-svg-icon>
                                      </button>
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${DEVICE_TYPE_ICONS[
                                                  device.device_type
                                              ] ?? DEVICE_TYPE_ICONS.other}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${device.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${[
                                              device.manufacturer,
                                              t(
                                                  DEVICE_TYPE_LABEL_KEYS[
                                                      device.device_type
                                                  ],
                                              ),
                                          ]
                                              .filter(Boolean)
                                              .join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge cmd-badge">
                                              ${t("devlist.cmd_badge", { count: device.command_count })}
                                          </span>
                                          ${device.emitter_entity_ids.length > 0
                                              ? html`<span class="badge tx-badge">${t("devlist.tx_badge", { count: device.emitter_entity_ids.length })}</span>`
                                              : html`<span class="badge no-tx-badge">${t("devlist.no_tx")}</span>`}
                                      </div>
                                  </div>
                                  ${device.id === this.expandedDeviceId && this._expandedDevice
                                      ? html`
                                            <div class="expanded-detail">
                                                <ir-device-detail
                                                    .api=${this.api}
                                                    .device=${this._expandedDevice}
                                                    .hass=${this.hass}
                                                    .receivers=${this._receivers}
                                                    .triggerRemotes=${this.triggerRemotes}
                                                    @device-changed=${this._onExpandedDeviceChanged}
                                                    @device-refreshed=${this
                                                        ._onExpandedDeviceRefreshed}
                                                    @device-deleted=${this._onExpandedDeviceDeleted}
                                                    @commands-reordered=${this._onCommandsReordered}
                                                    @trigger-changed=${this._loadTriggers}
                                                    @collapse=${this._onCollapse}
                                                    @request-duplicate=${(ev: Event) =>
                                                        this._expandedDevice &&
                                                        this._openDuplicateDialog(this._expandedDevice, ev)}
                                                    @request-delete=${() => {
                                                        if (this._expandedDevice) {
                                                            this._confirmDeleteDevice = this._expandedDevice;
                                                        }
                                                    }}
                                                    @request-make-remote=${() =>
                                                        this._onMakeRemoteRequested(
                                                            this._expandedDevice,
                                                        )}
                                                ></ir-device-detail>
                                            </div>
                                        `
                                      : nothing}
                              `,
                              ),
                          )}
                          <ir-ghost-tile
                              kind="device"
                              .busy=${this._dropBusy === "device"}
                              @add-click=${this._add}
                              @files-dropped=${(e: CustomEvent<{ files: File[] }>) =>
                                  this._onGhostTileDrop("device", e)}
                          ></ir-ghost-tile>
                      </div>
                  `
                : html`
                      <div class="grid device-grid">
                          <ir-ghost-tile
                              kind="device"
                              .empty=${true}
                              .busy=${this._dropBusy === "device"}
                              @add-click=${this._add}
                              @files-dropped=${(e: CustomEvent<{ files: File[] }>) =>
                                  this._onGhostTileDrop("device", e)}
                          ></ir-ghost-tile>
                      </div>
                  `}

            <!-- Remotes: one HAIR Triggers drawer card, same size as
                 a collapsed device card (owner bench ruling), expanding via
                 the same expandedDeviceId/device-selected slot a device
                 card uses (TRIGGER_DRAWER_ID sentinel). Renders even at
                 zero triggers -- the drawer itself is a permanent fixture,
                 not conditional on having any remotes captured yet; the
                 expanded view's own empty state (trow.empty_state) covers
                 that case instead of hiding the section. -->
            <div class="toolbar trigger-toolbar">
                <div class="toolbar-title-group">
                    <span class="toolbar-title trigger-toolbar-title">
                        <ha-svg-icon .path=${ICON_DEVICES}></ha-svg-icon>
                        ${t("devlist.trigger_remotes_title")}
                        <span class="toolbar-count">(${this._triggerDrawerCount})</span>
                        <span class="toolbar-tagline">- ${t("devlist.trigger_remotes_tagline")}</span>
                    </span>
                </div>
            </div>
            <div class="grid">
                <div
                    class="card trigger-drawer-card ${this.expandedDeviceId === TRIGGER_DRAWER_ID ? "expanded" : ""} ${this._drawerTriggers.some((t) => this._glowTriggerIds.has(t.id)) ? "bloom" : ""}"
                    tabindex="0"
                    @click=${() => this._select(TRIGGER_DRAWER_ID)}
                    @keydown=${(e: KeyboardEvent) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            this._select(TRIGGER_DRAWER_ID);
                        }
                    }}
                >
                    <div class="card-header">
                        <ha-svg-icon class="trigger-icon" .path=${ICON_TRIGGER}></ha-svg-icon>
                        <div class="card-name">
                            ${this._triggerDrawer?.name ?? t("devlist.trigger_drawer_default_name")}
                        </div>
                    </div>
                    <div class="card-footer">
                        <span class="badge cmd-badge"
                            >${t("devlist.on_badge", {
                                count: this._drawerTriggers.filter(
                                    (trig) => trig.enabled,
                                ).length,
                            })}</span
                        >
                        ${this._drawerTriggers.some((trig) => !trig.enabled)
                            ? html`<span class="badge trigger-off-badge"
                                  >${t("devlist.off_badge", {
                                      count: this._drawerTriggers.filter(
                                          (trig) => !trig.enabled,
                                      ).length,
                                  })}</span
                              >`
                            : ""}
                    </div>
                </div>
                ${this.expandedDeviceId === TRIGGER_DRAWER_ID
                    ? html`
                          <div class="expanded-detail trigger-drawer-detail">
                              <section class="header trh-header">
                                  <div class="header-left">
                                      <div class="name-row">
                                          <div class="name-line">
                                          ${this._editingDrawerName
                                              ? html`
                                                    <input
                                                        class="name-input drawer-name-input"
                                                        type="text"
                                                        .value=${this._draftDrawerName}
                                                        @input=${(e: Event) =>
                                                            (this._draftDrawerName = (
                                                                e.target as HTMLInputElement
                                                            ).value)}
                                                        @blur=${this._saveDrawerName}
                                                        @keydown=${this._onDrawerNameKeydown}
                                                        ?disabled=${this._drawerBusy}
                                                    />
                                                `
                                              : html`
                                                    <h1
                                                        class="editable-name"
                                                        @click=${this._startEditDrawerName}
                                                        title=${t("cmdrow.rename")}
                                                    >
                                                        ${this._triggerDrawer?.name ?? t("devlist.trigger_drawer_default_name")}
                                                        <span class="edit-icon">&#9998;</span>
                                                    </h1>
                                                `}
                                          <span class="trh-count"
                                              >(${tp("trow.header_count", this._drawerTriggers.length)})</span
                                          >
                                          ${this._triggerDrawer?.ha_device_id
                                              ? renderExitToEntityBtn(
                                                    `/config/devices/device/${this._triggerDrawer.ha_device_id}`,
                                                    t("devices.open_in_ha"),
                                                )
                                              : nothing}
                                          </div>
                                      </div>
                                  </div>
                                  <button
                                      class="collapse-btn"
                                      @click=${() => this._select(TRIGGER_DRAWER_ID)}
                                      title=${t("common.close")}
                                  >&#x2715;</button>
                              </section>
                              <div class="trh-triggers-header">
                                  <span
                                      >${t("trow.section_header", {
                                          count: this._drawerTriggers.length,
                                      })}</span
                                  >
                              </div>
                              ${this._drawerTriggers.length > 0
                                  ? html`
                                        <div class="trigger-rows">
                                            ${keyed(
                                                this._triggerRowsVersion,
                                                repeat(
                                                    this._drawerTriggers,
                                                    (trig) => trig.id,
                                                    (trig) => html`
                                                        <ir-trigger-row
                                                            .trigger=${trig}
                                                            .receivers=${this._receivers}
                                                            .bloom=${this._glowTriggerIds.has(trig.id)}
                                                            @rename-trigger=${this._onRenameTrigger}
                                                            @toggle-enabled=${(ev: CustomEvent) =>
                                                                this._toggleTriggerEnabled(ev.detail.trigger, ev)}
                                                            @edit-trigger=${(ev: CustomEvent) =>
                                                                this._openEditTrigger(ev.detail.trigger, ev)}
                                                            @delete-trigger=${(ev: CustomEvent) =>
                                                                this._requestDeleteTrigger(ev.detail.trigger, ev)}
                                                        >
                                                            <ha-svg-icon
                                                                slot="grip"
                                                                class="grip-handle"
                                                                .path=${ICON_GRIP}
                                                            ></ha-svg-icon>
                                                        </ir-trigger-row>
                                                    `,
                                                ),
                                            )}
                                        </div>
                                    `
                                  : html`<div class="trigger-drawer-empty">${t("trow.empty_state")}</div>`}
                          </div>
                      `
                    : nothing}
                ${repeat(
                    this.triggerRemotes,
                    (remote) => remote.id,
                    (remote) => html`
                        <div
                            class="card trigger-remote-card ${remote.id === this.expandedDeviceId ? "expanded" : ""} ${this._remoteTriggers(remote.id).some((t) => this._glowTriggerIds.has(t.id)) ? "bloom" : ""}"
                            tabindex="0"
                            @click=${() => this._select(remote.id)}
                            @keydown=${(e: KeyboardEvent) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    this._select(remote.id);
                                }
                            }}
                        >
                            <button
                                class="card-action duplicate-action"
                                title=${t("duptr.heading")}
                                @click=${(e: Event) =>
                                    this._openDuplicateRemoteDialog(remote, e)}
                            >
                                <ha-svg-icon .path=${ICON_COPY}></ha-svg-icon>
                            </button>
                            <button
                                class="card-action delete-action"
                                title=${t("devlist.del_remote_title")}
                                @click=${(e: Event) => this._requestDeleteRemote(remote, e)}
                            >
                                <ha-svg-icon
                                    .path=${ICON_TRASH}
                                    .viewBox=${TRASH_VIEWBOX}
                                ></ha-svg-icon>
                            </button>
                            <div class="card-header">
                                <ha-svg-icon class="trigger-icon" .path=${ICON_TRIGGER}></ha-svg-icon>
                                <div class="card-name">${remote.name}</div>
                            </div>
                            <div class="card-footer">
                                <span class="badge cmd-badge"
                                    >${t("devlist.on_badge", {
                                        count: remote.enabled_count,
                                    })}</span
                                >
                                ${remote.disabled_count > 0
                                    ? html`<span class="badge trigger-off-badge"
                                          >${t("devlist.off_badge", {
                                              count: remote.disabled_count,
                                          })}</span
                                      >`
                                    : ""}
                            </div>
                        </div>
                        ${remote.id === this.expandedDeviceId
                            ? html`
                                  <div class="expanded-detail trigger-remote-detail">
                                      <section class="header trh-header rdetail-top">
                                          <div class="rtitle-block">
                                              <div class="name-line">
                                                  ${this._editingRemoteName
                                                      ? html`
                                                            <input
                                                                class="name-input remote-name-input"
                                                                type="text"
                                                                .value=${this._draftRemoteName}
                                                                @input=${(e: Event) =>
                                                                    (this._draftRemoteName = (
                                                                        e.target as HTMLInputElement
                                                                    ).value)}
                                                                @blur=${this._saveRemoteName}
                                                                @keydown=${this._onRemoteNameKeydown}
                                                                ?disabled=${this._remoteNameBusy}
                                                            />
                                                        `
                                                      : html`
                                                            <h1
                                                                class="editable-name"
                                                                @click=${(e: Event) =>
                                                                    this._startEditRemoteName(remote, e)}
                                                                title=${t("cmdrow.rename")}
                                                            >
                                                                ${remote.name}
                                                                <span class="edit-icon">&#9998;</span>
                                                            </h1>
                                                        `}
                                                  ${remote.ha_device_id
                                                      ? renderExitToEntityBtn(
                                                            `/config/devices/device/${remote.ha_device_id}`,
                                                            t("devices.open_in_ha"),
                                                        )
                                                      : nothing}
                                              </div>
                                          </div>
                                          <div class="rdetail-divider"></div>
                                          <div class="hdr-rows">
                                              <ir-header-chip-group
                                                  label=${t("hdrchips.receivers_label")}
                                                  .labelWidth=${REMOTE_HDR_LABEL_W}
                                                  .rows=${this._receiverRows(remote)}
                                                  .tone=${GREEN_PEAK}
                                                  ?disabled=${this._remoteReceiversBusy}
                                                  @chips-changed=${(
                                                      ev: CustomEvent<{ value: string[] }>,
                                                  ) => this._onRemoteReceiversChanged(remote, ev)}
                                              ></ir-header-chip-group>
                                              ${PINNING_UI_ENABLED
                                                  ? html`
                                                        <ir-header-chip-group
                                                            label=${t("hdrchips.pin_label_full")}
                                                            labelEmpty=${t("hdrchips.pin_label_empty")}
                                                            .labelWidth=${REMOTE_HDR_LABEL_W}
                                                            .rows=${this._pinRows(remote)}
                                                            .tone=${PIN_BLUE}
                                                            @chips-changed=${(ev: CustomEvent<{ value: string[] }>) =>
                                                                this._onRemotePinsChanged(remote, ev)}
                                                        ></ir-header-chip-group>
                                                    `
                                                  : nothing}
                                          </div>
                                          <div class="rdetail-actions">
                                              <button
                                                  class="collapse-btn"
                                                  @click=${() => this._select(remote.id)}
                                                  title=${t("common.close")}
                                              >&#x2715;</button>
                                              <button
                                                  class="settings-btn"
                                                  title=${t("devsettings.remote_title")}
                                                  @click=${() => (this._remoteSettingsTarget = remote)}
                                              >
                                                  <svg class="settings-icon" viewBox=${SETTINGS_VIEWBOX}>
                                                      <path d=${ICON_SETTINGS} fill="currentColor"></path>
                                                  </svg>
                                              </button>
                                          </div>
                                      </section>
                                      ${remote.matrix
                                          ? html`
                                                <ir-matrix-card
                                                    .hass=${this.hass}
                                                    mode="hear"
                                                    .summary=${remote.matrix}
                                                    .cellsKey=${remote.id}
                                                    .cellsLoader=${() =>
                                                        this.api!.remoteMatrixCells(remote.id)}
                                                    .heard=${remote.last_heard}
                                                    .haDeviceId=${remote.ha_device_id}
                                                    @matrix-save-trigger=${(
                                                        ev: CustomEvent<MatrixCardPick>,
                                                    ) => this._onMatrixSaveTrigger(remote.id, ev)}
                                                ></ir-matrix-card>
                                                <div class="trh-triggers-header">
                                                    <span>${t("lastheard.header")}</span>
                                                </div>
                                                <ir-last-heard-row
                                                    .heard=${remote.last_heard}
                                                    .receivers=${this._receivers}
                                                    @last-heard-trigger=${(
                                                        ev: CustomEvent<LastHeard>,
                                                    ) => this._onLastHeardTrigger(remote.id, ev.detail)}
                                                ></ir-last-heard-row>
                                            `
                                          : nothing}
                                      <div class="trh-triggers-header">
                                          <span
                                              >${t("trow.section_header", {
                                                  count: remote.trigger_count,
                                              })}</span
                                          >
                                      </div>
                                      ${this._remoteTriggers(remote.id).length > 0
                                          ? html`
                                                <div class="trigger-rows">
                                                    ${keyed(
                                                        this._triggerRowsVersion,
                                                        repeat(
                                                            this._remoteTriggers(remote.id),
                                                            (trig) => trig.id,
                                                            (trig) => html`
                                                                <ir-trigger-row
                                                                    .trigger=${trig}
                                                                    .receivers=${this._receivers}
                                                                    .mappings=${remote.pin_map?.[trig.id] ?? []}
                                                                    .showMappings=${(remote.pinned_device_ids ?? []).length > 0}
                                                                    .bloom=${this._glowTriggerIds.has(trig.id)}
                                                                    @rename-trigger=${this._onRenameTrigger}
                                                                    @toggle-enabled=${(ev: CustomEvent) =>
                                                                        this._toggleTriggerEnabled(ev.detail.trigger, ev)}
                                                                    @edit-trigger=${(ev: CustomEvent) =>
                                                                        this._openEditTrigger(ev.detail.trigger, ev)}
                                                                    @delete-trigger=${(ev: CustomEvent) =>
                                                                        this._requestDeleteTrigger(ev.detail.trigger, ev)}
                                                                >
                                                                    <ha-svg-icon
                                                                        slot="grip"
                                                                        class="grip-handle"
                                                                        .path=${ICON_GRIP}
                                                                    ></ha-svg-icon>
                                                                </ir-trigger-row>
                                                            `,
                                                        ),
                                                    )}
                                                </div>
                                            `
                                          : html`<div class="trigger-drawer-empty">${t("trow.empty_state")}</div>`}
                                  </div>
                              `
                            : nothing}
                    `,
                )}
                <!-- Always compact (0.10.1 item 6). The Remotes grid is
                     never truly empty -- the HAIR Triggers drawer always
                     occupies a card -- so the zero-named-remotes case is
                     a populated grid, not an empty section, and the tile
                     that belongs beside a card is the compact one. -->
                <ir-ghost-tile
                    kind="remote"
                    .busy=${this._dropBusy === "remote"}
                    @add-click=${this._addRemote}
                    @files-dropped=${(e: CustomEvent<{ files: File[] }>) =>
                        this._onGhostTileDrop("remote", e)}
                ></ir-ghost-tile>
            </div>

            <!-- Blasters (Pluckable) -- vendor IR blasters HAIR can pull
                 from, plus the learned-code stores it has plucked -->
            ${this._pluckBlasters.length + this._pluckedStores.length > 0
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.blasters")}</h2>
                          <span class="section-count"
                              >${this._pluckBlasters.length +
                              this._pluckedStores.length}</span
                          >
                      </div>
                      <div class="grid">
                          ${this._pluckedStores.map(
                              (s) => html`
                                  <div class="card hw-card">
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${ICON_BLASTER}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${s.friendly_name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${s.kind} &middot; ${s.store_id}
                                      </div>
                                      <div class="card-footer">
                                          <button
                                              class="badge forget-badge"
                                              title=${t(
                                                  "devlist.forget_store_title",
                                              )}
                                              @click=${() =>
                                                  void this._forgetStore(s)}
                                          >
                                              ${t("devlist.forget_store")}
                                          </button>
                                      </div>
                                  </div>
                              `,
                          )}
                          ${this._pluckBlasters.map(
                              (b) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      title=${t("devlist.open_plucker_title")}
                                      @click=${() => this._openInPlucker(b.entity_id)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._openInPlucker(b.entity_id);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_BLASTER}></ha-svg-icon>
                                          <div class="card-name">
                                              ${b.vendorName}: ${b.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">${b.entity_id}</div>
                                      <div class="card-footer">
                                          <span class="badge pluck-badge"
                                              >${t("devlist.open_plucker")}</span
                                          >
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Emitters -->
            ${hasEmitters
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.emitters")}</h2>
                          <span class="section-count">${this._emitters.length}</span>
                      </div>
                      <div class="grid">
                          ${this._emitters.map(
                              (em) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${() =>
                                          this._navigateIntegration(
                                              this._emitterIntegrationDomain(em.entity_id),
                                          )}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._navigateIntegration(
                                                  this._emitterIntegrationDomain(em.entity_id),
                                              );
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_EMITTER}></ha-svg-icon>
                                          <div class="card-name">${em.name}</div>
                                      </div>
                                      <div class="card-meta">${em.entity_id}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${t("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Receivers (capture-capable hardware; proxies appear here too by design) -->
            ${hasReceivers
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.receivers")}</h2>
                          <span class="section-count">${receivers.length}</span>
                      </div>
                      <div class="grid">
                          ${receivers.map(
                              (entry) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${() => this._navigateIntegration(entry.nav_type)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._navigateIntegration(entry.nav_type);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_RECEIVER}></ha-svg-icon>
                                          <div class="card-name">${entry.name}</div>
                                      </div>
                                      <div class="card-meta">${entry.native_entity_id ?? entry.nav_type}</div>
                                      <div class="card-footer">
                                          ${this._renderRxBadges(entry)}
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Proxies (TX + RX hardware) -->
            ${hasProxies
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.proxies")}</h2>
                          <span class="section-count">${proxies.length}</span>
                      </div>
                      <div class="grid">
                          ${proxies.map(
                              (entry) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${() => this._navigateIntegration(entry.nav_type)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._navigateIntegration(entry.nav_type);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_PROXY}></ha-svg-icon>
                                          <div class="card-name">${entry.name}</div>
                                      </div>
                                      ${entry.tx_entity_ids[0]
                                          ? html`<div class="card-meta">${entry.tx_entity_ids[0]}</div>`
                                          : nothing}
                                      <div class="card-meta">${entry.native_entity_id ?? entry.nav_type}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${t("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                          ${this._renderRxBadges(entry)}
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            ${this._editTrigger
                ? html`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._editTrigger}
                          @trigger-saved=${this._onTriggerUpdated}
                          @closed=${this._closeEditTrigger}
                      ></ir-trigger-dialog>
                  `
                : nothing}

            ${this._mintTrigger
                ? html`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .remoteId=${this._mintTrigger.remoteId}
                          origin="matrix"
                          .presetName=${this._mintTrigger.detail.name}
                          .code=${this._mintTrigger.detail.pronto}
                          protocol="PRONTO"
                          .signalFingerprint=${this._mintTrigger.detail.identity
                              .signal_fingerprint}
                          .byteHash=${this._mintTrigger.detail.identity
                              .byte_hash}
                          .decodedFingerprint=${this._mintTrigger.detail
                              .identity.decoded_fingerprint}
                          @trigger-saved=${this._onMintTriggerSaved}
                          @closed=${this._closeMintTrigger}
                      ></ir-trigger-dialog>
                  `
                : nothing}

            ${this._confirmDeleteTrigger
                ? html`
                      <ir-confirm-dialog
                          title=${t("mirror.del_trigger_title")}
                          message=${t("devlist.del_trigger_msg", { name: this._confirmDeleteTrigger.name })}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${() => (this._confirmDeleteTrigger = null)}
                      ></ir-confirm-dialog>
                  `
                : nothing}

            ${this._duplicateTarget && this.api
                ? html`
                      <ir-duplicate-device-dialog
                          .api=${this.api}
                          .sourceId=${this._duplicateTarget.id}
                          .sourceName=${this._duplicateTarget.name}
                          @device-duplicated=${this._onDeviceDuplicated}
                          @closed=${this._closeDuplicateDialog}
                      ></ir-duplicate-device-dialog>
                  `
                : nothing}

            ${this._duplicateRemoteTarget && this.api
                ? html`
                      <ir-duplicate-trigger-remote-dialog
                          .api=${this.api}
                          .sourceId=${this._duplicateRemoteTarget.id}
                          .sourceName=${this._duplicateRemoteTarget.name}
                          .sourceReceiverScope=${this._duplicateRemoteTarget.receiver_scope}
                          @remote-duplicated=${this._onRemoteDuplicated}
                          @closed=${this._closeDuplicateRemoteDialog}
                      ></ir-duplicate-trigger-remote-dialog>
                  `
                : nothing}

            ${this._confirmDeleteDevice
                ? html`
                      <ir-confirm-dialog
                          title=${t("devlist.del_device_title")}
                          message=${t("devlist.del_device_msg", { name: this._confirmDeleteDevice.name })}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteDevice}
                          @closed=${() => (this._confirmDeleteDevice = null)}
                      ></ir-confirm-dialog>
                  `
                : nothing}

            ${this._renderDropSupersede()}

            ${this._confirmDeleteRemote
                ? html`
                      <ir-confirm-dialog
                          title=${t("devlist.del_remote_title")}
                          message=${t("devlist.del_remote_msg", { name: this._confirmDeleteRemote.name })}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteRemote}
                          @closed=${() => (this._confirmDeleteRemote = null)}
                      ></ir-confirm-dialog>
                  `
                : nothing}

            ${this._remoteSettingsTarget
                ? html`
                      <ir-trigger-remote-settings-dialog
                          .remote=${this._remoteSettingsTarget}
                          @request-duplicate=${(ev: Event) => {
                              const target = this._remoteSettingsTarget;
                              this._remoteSettingsTarget = null;
                              if (target) this._openDuplicateRemoteDialog(target, ev);
                          }}
                          @request-delete=${() => {
                              const target = this._remoteSettingsTarget;
                              this._remoteSettingsTarget = null;
                              if (target) this._confirmDeleteRemote = target;
                          }}
                          @request-make-device=${() => {
                              const target = this._remoteSettingsTarget;
                              this._remoteSettingsTarget = null;
                              this._onMakeDeviceRequested(target);
                          }}
                          @closed=${() => (this._remoteSettingsTarget = null)}
                      ></ir-trigger-remote-settings-dialog>
                  `
                : nothing}

            ${this._makeRemoteSource && this.api
                ? html`
                      <ir-promote-remote-dialog
                          .api=${this.api}
                          .sourceDeviceId=${this._makeRemoteSource.id}
                          .suggestedName=${this._makeRemoteSource.name}
                          .previewCount=${this._eligibleCommandCount(
                              this._makeRemoteSource,
                          )}
                          @remote-created=${this._onRemoteMinted}
                          @closed=${this._closeMakeRemoteDialog}
                      ></ir-promote-remote-dialog>
                  `
                : nothing}

            ${this._makeDeviceSource && this.api
                ? html`
                      <ir-promote-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .sourceRemoteId=${this._makeDeviceSource.id}
                          .suggestedName=${this._makeDeviceSource.name}
                          @device-created=${this._onDeviceMinted}
                          @closed=${this._closeMakeDeviceDialog}
                      ></ir-promote-dialog>
                  `
                : nothing}

            ${this._pinPromptTarget && this.api
                ? html`
                      <ir-pin-prompt-dialog
                          .api=${this.api}
                          .remoteId=${this._pinPromptTarget.remoteId}
                          .remoteName=${this._pinPromptTarget.remoteName}
                          .deviceId=${this._pinPromptTarget.deviceId}
                          .deviceName=${this._pinPromptTarget.deviceName}
                          @pinned=${this._onPinPromptPinned}
                          @closed=${() => (this._pinPromptTarget = null)}
                      ></ir-pin-prompt-dialog>
                  `
                : nothing}
        `;
    }

    static styles = [
        exitToEntityButtonStyles,
        settingsButtonStyles,
        bloomStyles,
        css`
        /* Punch list item 17. A .trh-header .settings-btn rule setting
           margin-right 2px used to live here, from the header this one
           replaced, and it was the entire difference between the two
           details: measured on the bench, the Device gear's right edge sits at
           the X's exactly (delta 0) while the Remote's sat 2px inside
           it. Everything else -- the stretched actions column, the
           space-between distribution, align-self: flex-end on both
           children -- was already identical. The gear is the only
           .settings-btn in this file (the Trigger Drawer header has no
           gear to nudge), so the rule had no other consumer and is
           gone rather than re-scoped. */
        :host {
            display: block;
        }
        .loading,
        .empty {
            padding: 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty h2 {
            margin-top: 8px;
            color: var(--primary-text-color);
        }

        /* --- Devices toolbar (matches sniffer) --- */
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toolbar-title-group {
            display: flex;
        }
        /* Remotes Rename Label Pass (owner request, 2026-08-14): a
           one-line description of each section header -- "Devices"
           and "Remotes" alone are generic enough to want the
           disambiguation.

           ONE LINE + ALL CAPS (owner ruling 2026-08-15): the tagline
           used to sit on its own indented row below the title -- now
           it runs inline right after the count, prefixed with a
           hyphen so it reads as a continuation of the title rather
           than a caption. Both title and tagline are upper-cased,
           matching the small-caps convention already used for
           header-chip-group labels and the device Type label
           elsewhere on this page. */
        .toolbar-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .toolbar-tagline {
            font-size: 0.8rem;
            font-weight: 400;
            color: var(--secondary-text-color);
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .toolbar-title ha-svg-icon {
            --mdc-icon-size: 24px;
            /* Devices wears the device green: the same #2e7d32 as the
               expanded-card stroke and the Assign chip (owner ruling,
               2026-07-20 -- green = device-ward, everywhere). */
            color: #2e7d32;
        }
        .toolbar-count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        /* Remotes' own toolbar -- same treatment as the devices
           toolbar above (icon + title + count), gold instead of device
           green, with the section boundary itself living here as a
           border-top (owner ruling 2026-08-14: the line caps off
           Devices, the header sits below it, not the other
           way around). */
        .trigger-toolbar {
            border-top: 2px solid var(--divider-color);
            padding-top: 20px;
            margin: 24px 0 16px;
        }
        .trigger-toolbar-title ha-svg-icon {
            color: #d4a017;
        }
        /* --- Section headers (neutral) --- */
        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 24px 0 10px;
            padding-top: 14px;
            border-top: 2px solid var(--divider-color);
        }
        .section-header:first-child {
            margin-top: 0;
        }
        .section-header h2 {
            margin: 0;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            color: var(--secondary-text-color);
        }
        .section-count {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 4px;
            background: var(--secondary-background-color);
            color: var(--secondary-text-color);
        }

        /* --- Card grid (compact) --- */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 12px;
            /* Explicit though it is the default: every item in a row
               takes the row's height, so the tallest item sets it. The
               ghost tile used to win that contest in the Remotes grid
               and drag the row up to its own min-height (punch list
               item 12); the floor came off the tile rather than the
               alignment being changed here. */
            align-items: stretch;
        }

        /* --- Shared card styles (neutral, sniffer palette) --- */
        .card {
            padding: 12px;
            cursor: pointer;
            border-radius: 8px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .card:hover,
        .card:focus-visible {
            background: var(--secondary-background-color);
            outline: none;
        }
        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-header ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            /* Long card names (eg the Athom proxy transmitter title) can
               otherwise squeeze the flex item below its intrinsic size. */
            flex-shrink: 0;
        }
        .card-name {
            font-size: 0.95rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            /* Ellipsize ~2 characters earlier so a full-width name never
               runs under the corner glyph (owner catch, 2026-07-20: the
               duplicate glyph zone reaches 27px in from the card edge,
               the card's own padding only 12px). */
            padding-right: 16px;
        }
        .card-meta {
            margin-top: 6px;
            margin-left: 35px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-footer {
            margin-top: 8px;
            margin-left: 32px;
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .badge {
            border-radius: 4px;
            padding: 2px 4px;
            font-size: 0.72rem;
            font-weight: 500;
            line-height: 1;
        }

        /* Command count badge (green) */
        .cmd-badge {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }

        /* TX badge (amber text, dark bg) */
        .tx-badge {
            background: var(--secondary-background-color);
            color: #ff9800;
        }

        /* RX badge (blue text, dark bg) */
        .rx-badge {
            background: var(--secondary-background-color);
            color: var(--primary-color, #2196f3);
        }

        /* No TX warning (muted) */
        .no-tx-badge {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            font-style: italic;
        }

        /* Remote card ON:/OFF: badges (signpost 3, Track 2 item 0.6 /
           Track 3 item 2). ON: reuses .cmd-badge verbatim (see the
           markup). OFF: keeps .tx-badge's shape -- dark chip
           background -- but swaps TX:'s amber for this project's
           ember, deliberately: do not carry the amber over. */
        .trigger-off-badge {
            background: var(--secondary-background-color);
            color: #e65100;
        }

        /* Hardware section badges -- consistent <direction>-<source> pattern. */
        /* TX-NATIVE and RX-NATIVE share the green palette of .cmd-badge. */
        .tx-native,
        .rx-native {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }
        /* RX-BRIDGE uses HAIR's existing orange. */
        .rx-bridge {
            background: rgba(255, 152, 0, 0.15);
            color: #ff9800;
        }
        /* Pre-2026.6 upgrade hint: grayed RX-NATIVE alongside RX-BRIDGE. */
        .rx-native-disabled {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            opacity: 0.6;
            cursor: help;
        }

        /* --- Expanded detail row --- */
        .expanded-detail {
            grid-column: 1 / -1;
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            padding: 16px;
            animation: expand-in 200ms ease;
        }
        @keyframes expand-in {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Device card expanded highlight --- */
        .device-card {
            position: relative;
        }
        .device-card.expanded {
            border-color: #2e7d32;
            box-shadow: 0 0 0 1px #2e7d32;
        }
        /* SortableJS marks the card being dragged. */
        .device-card.sortable-ghost {
            opacity: 0.4;
        }
        .device-card.sortable-chosen {
            cursor: grabbing;
        }

        /* --- Card corner actions (duplicate top-right, delete bottom-right) --- */
        .card-action {
            position: absolute;
            background: transparent;
            border: none;
            padding: 4px;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 120ms ease, color 120ms ease, opacity 120ms ease;
        }
        .card-action ha-svg-icon {
            /* Default card-action glyph size. The duplicate-action overrides
               this with a smaller value because the copy MDI glyph fills more
               of its viewbox than the trash glyph. */
            --mdc-icon-size: 16px;
        }
        .duplicate-action {
            top: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0;
        }
        /* Hidden until the card itself is hovered or has focus within
           (keyboard users tabbing onto the card or its children) --
           always-visible at rest read as busy (owner catch
           2026-08-14). */
        .device-card:hover .duplicate-action,
        .device-card:focus-within .duplicate-action,
        .device-card:hover .delete-action,
        .device-card:focus-within .delete-action {
            opacity: 0.55;
        }
        .duplicate-action ha-svg-icon {
            /* Copy MDI glyph fills more of its viewbox than the trash glyph,
               so render it smaller to land at the same visual size as the
               trash icon in the opposite corner. */
            --mdc-icon-size: 13px;
        }
        .duplicate-action:hover {
            color: var(--primary-text-color);
            opacity: 1;
        }
        .delete-action {
            bottom: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0;
        }
        /* EMBER, not material red (owner ruling 2026-08-03). Ember is
           already the panel's delete colour on every text chip, and the
           trash sweep put it on nine more cans; these two shipped in
           red and were suddenly the odd ones out. Two conventions for
           the same act is the exact failure the ruling avoids. */
        .delete-action:hover {
            background: rgba(230, 81, 0, 0.12);
            color: #e65100;
            opacity: 1;
        }

        /* --- Hardware cards inherit shared .card styles --- */
        .hw-card {
            /* Neutral -- no per-section color backgrounds */
        }
        /* "Open in Plucker" badge -- standard badge form, no stroke. */
        .pluck-badge {
            background: var(--secondary-background-color);
            color: #78909c;
            text-transform: uppercase;
        }
        /* Same form, but this one is a real button: forgetting a
           plucked store's row is the only action it carries. */
        .forget-badge {
            background: var(--secondary-background-color);
            color: var(--secondary-text-color);
            text-transform: uppercase;
            border: none;
            font: inherit;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            cursor: pointer;
        }
        .forget-badge:hover {
            color: var(--primary-text-color);
        }

        /* --- Remotes: single HAIR Triggers drawer card --- */
        .trigger-drawer-card {
            transition: transform 120ms ease, box-shadow 300ms ease,
                        border-color 300ms ease, background 400ms ease;
            position: relative;
        }
        .trigger-drawer-card .trigger-icon {
            /* Gold, matching the drawer's own palette (bloomStyles'
               default hue) -- not the device green .toolbar-title uses,
               per the owner's green = device-ward ruling above. */
            color: #d4a017;
            transition: color 200ms ease, transform 200ms ease;
        }
        .trigger-drawer-card.expanded {
            border-color: #d4a017;
            box-shadow: 0 0 0 1px #d4a017;
        }
        /* Fire-glow now rides the shared .bloom class (ir-bloom-styles.ts)
           instead of this file's own trigger-card-flash/trigger-bolt-pulse
           keyframes -- same shape the Mirror's silver bloom uses, gold by
           this class's own default custom properties. */
        .trigger-drawer-card.bloom .trigger-icon {
            color: var(--bloom-peak);
        }

        /* --- Remotes: named-remote cards (Track 4 minimal
           card; Track 5 full expand/rename/duplicate parity with the
           drawer -- clickable now, so no cursor/hover override left
           to neutralize). Corner actions follow the same hover-to-
           reveal treatment .device-card's own actions use (owner
           catch 2026-08-14: always-visible reads as busy);
           .expanded uses the same gold outline
           .trigger-drawer-card.expanded uses. --- */
        .trigger-remote-card {
            position: relative;
        }
        .trigger-remote-card .trigger-icon {
            color: #d4a017;
        }
        .trigger-remote-card.expanded {
            border-color: #d4a017;
            box-shadow: 0 0 0 1px #d4a017;
        }
        /* Add Popups signpost 2, Track 5 follow-up: the drawer card's
           own .bloom icon-color rule (below) predates named remotes
           having cards of their own to glow -- same treatment, once
           the remote card actually gets the .bloom class (see the
           class= edit above). */
        .trigger-remote-card.bloom .trigger-icon {
            color: var(--bloom-peak);
        }
        .trigger-remote-card:hover .delete-action,
        .trigger-remote-card:focus-within .delete-action,
        .trigger-remote-card:hover .duplicate-action,
        .trigger-remote-card:focus-within .duplicate-action {
            opacity: 0.55;
        }

        /* --- Drawer header (rename-in-place + go-to-HA + close),
               parity with ir-device-detail.ts's own device header --- */
        .trh-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }
        .trh-header .header-left {
            flex: 1;
            min-width: 0;
        }

        /* --- Named-remote header, punch list item 9 ---------------
           header-pin-layout-handoff.md, owner-approved 2026-08-16,
           reconciled against the shipped chip group per item 11.

           This layer is ADDITIVE and applies only where .rdetail-top
           joins .trh-header: the named remote's own header. The Trigger
           Drawer's header keeps the plain .trh-header rules above --
           item 9's scope is the Remote and Device detail headers, no
           other surfaces, and the drawer has neither chip rows nor a
           gear to anchor.

           align-items: stretch (not the base rule's center) is what
           lets the actions column span the full header height, which is
           what the X/gear anchoring depends on. justify-content returns
           to flex-start because the columns now carry their own widths;
           space-between would fight the rows column's flex: 1. */
        .trh-header.rdetail-top {
            align-items: stretch;
            justify-content: flex-start;
            gap: 16px;
        }
        .rdetail-top .rtitle-block {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 6px;
            flex-shrink: 0;
            min-width: 0;
        }
        /* Full height of the header block, restored from the original
           comps -- it was a short stub (a left border on the old
           .remote-receiver-scope) in the shipped version. */
        .rdetail-top .rdetail-divider {
            width: 1px;
            align-self: stretch;
            background: var(--divider-color);
            flex-shrink: 0;
        }
        .rdetail-top .hdr-rows {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 11px;
            flex: 1;
            min-width: 0;
        }
        /* THE ANCHORING (owner: "right now it seems to move"), and it is
           structural rather than a pixel offset that happened to look
           right in one screenshot. The column is stretched to the full
           header height and distributes with space-between, so its first
           child sits on the top edge and its last child on the bottom
           edge no matter how tall the rows column grows. Do NOT
           reimplement as position: absolute corners -- the card's height
           is content-driven, so absolute corners break the moment a row
           wraps. */
        .rdetail-top .rdetail-actions {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-self: stretch;
            flex-shrink: 0;
        }
        /* Both buttons hug the right edge of the column. The base
           .trh-header .collapse-btn rule sets align-self: center, which
           in this column means horizontally centered -- it left the X
           9px inside the gear's right edge, measured live on the bench.
           Both selectors carry two classes, so specificity ties and the
           later rule wins; .trh-header.rdetail-top adds the third class
           to settle it rather than relying on rule order in the sheet.
           settingsButtonStyles' own align-self: end is restated for the
           same reason. */
        .trh-header.rdetail-top .rdetail-actions > * {
            align-self: flex-end;
        }
        .trh-header.rdetail-top .rdetail-actions .collapse-btn,
        .trh-header.rdetail-top .rdetail-actions .settings-btn {
            align-self: flex-end;
        }
        /* Punch list item 23: ONE fixed square box for both actions.
           Item 17 aligned the button EDGES and they do align -- but a
           box's edge is not what the eye reads, its glyph is, and the
           two glyphs sat at different insets because the two buttons
           carried different padding (the Device header's X had
           2px 8px, this one had 4px, the shared gear has 5px around a 29px
           icon). Right-aligning boxes of different widths lines up the
           right edges and nothing else.

           Equal squares fix it by construction rather than by
           arithmetic: each glyph is centered in its own box, the boxes
           are the same size, and their right edges already coincide,
           so the glyph centers coincide too -- on this header and on
           the Device's, which carries the identical rule. Nothing here
           needs to be re-derived if a glyph or a font size changes
           later. */
        .trh-header.rdetail-top .rdetail-actions .collapse-btn,
        .trh-header.rdetail-top .rdetail-actions .settings-btn {
            width: 32px;
            height: 32px;
            min-width: 32px;
            padding: 0;
            box-sizing: border-box;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        /* The Remote header is a twin of ir-device-detail.ts's Device
           header, but it never got that file's narrow-width query, and
           the omission is what put the chips outside the card on a
           phone. .rtitle-block is flex-shrink: 0 and .hdr-rows is
           flex: 1 (basis 0), so once the name plus the 32px actions
           column exceed the header, .hdr-rows is the only item that can
           give and it gives everything: measured 0px wide inside a
           313px header at a 390px viewport, with the emitter chip
           spilling 129px past the card edge. At 320px the actions
           column went out with it.

           Mirrors ir-device-detail.ts's 700px block rule for rule, on
           purpose -- same layout, same content, same breakpoint, so the
           two headers keep behaving identically. Restoring the title
           block's ability to shrink is what lets the top line fit; the
           chips then take a full-width line of their own below it.

           Same-specificity selectors as the rules above, winning on
           source order (not raised specificity), matching how the twin
           file does it. Above 700px nothing here applies and the
           desktop layout is untouched, divider included. */
        @media (max-width: 700px) {
            .trh-header.rdetail-top {
                flex-wrap: wrap;
                align-items: flex-start;
                gap: 12px;
            }
            .rdetail-top .rtitle-block {
                flex: 1;
            }
            .rdetail-top .rdetail-divider {
                display: none;
            }
            .rdetail-top .hdr-rows {
                flex-basis: 100%;
                order: 3;
            }
            .rdetail-top .rdetail-actions {
                align-self: flex-start;
            }
        }
        /* Owner ruling 2026-08-15: was align-items: center, so when
           the Receivers chip group (inside this same row) wraps to
           two lines it centered the name/count/exit-to-HA button
           against that taller wrapped content instead of pinning
           them to the top.

           DRAWER-ONLY as of punch list item 9: the named remote's
           header no longer nests its name inside .name-row (it uses
           .rtitle-block above, with the chip rows in their own
           column), so this rule and .trh-count below now serve the
           Trigger Drawer's header alone. Both are left in place --
           the drawer is out of item 9's scope by ruling. */
        .trh-header .name-row {
            display: flex;
            align-items: flex-start;
            gap: 6px;
            min-width: 0;
        }
        /* Owner ruling 2026-08-15: the name, trigger count,
           and exit-to-HA button should center against each
           other (not the whole row, which can grow taller
           than them once Receivers wraps) while staying
           pinned to the top edge of the row -- so they get
           their own inner flex row, centered, nested inside
           .name-row (which stays flex-start so this group
           does not get pushed down when the row below it
           wraps). Shared by both the named-remote header
           (inside .rtitle-block since item 9) and the
           Trigger Drawer header. */
        /* Owner ruling 2026-08-15 (third pass, found via live
           Chrome DevTools inspection after two CSS-only misses):
           this block must never shrink below its own content --
           its children (h1, the exit-to-HA button, and the
           drawer's .trh-count) are all flex-shrink: 0 already
           and don't wrap, so shrinking the box below their
           combined width just let them overflow visibly on top
           of Receivers instead of actually getting smaller. The
           chip rows shrink and wrap correctly on their own, so
           they take 100% of the squeeze. */
        .trh-header .name-line {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-shrink: 0;
        }
        .trh-header h1 {
            font-size: 1.3rem;
            margin: 0;
        }
        /* Add Popups signpost 2, Track 5 follow-up: the
           trigger count for a named remote sits inline right
           after its name instead of on its own subtitle row
           below (owner request 2026-08-14, "Samsung TV (49
           triggers)"). Owner ruling 2026-08-15: the Trigger
           Drawer catch-all gets the same treatment now --
           its count moved here too, off the retired
           .trh-subtitle. */
        .trh-header .trh-count {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            flex-shrink: 0;
        }
        .trh-header .editable-name {
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
            flex-shrink: 0;
        }
        /* Add Popups signpost 2, Track 5 follow-up: the exit-to-entity
           button used to be the last thing on the name-row -- now the
           receiver-scope standoff box sits after it and can wrap to
           two lines, so pin this in place too rather than letting it
           get squeezed. */
        .trh-header .exit-to-entity-btn {
            flex-shrink: 0;
        }
        .trh-header .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .trh-header .edit-icon {
            /* .editable-name's own flex gap (6px) already spaces this
               from the name -- an explicit margin here would double
               up with it (bench catch 2026-08-14: pushed the pencil
               out to 12px instead of 6). */
            font-size: 0.7rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .trh-header .editable-name:hover .edit-icon {
            opacity: 1;
        }
        .trh-header .name-input {
            font-size: 1.3rem;
            font-family: inherit;
            font-weight: bold;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            flex: 1;
            min-width: 0;
            padding: 0 0 2px;
        }
        .trh-header .collapse-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: none;
            border: none;
            padding: 4px;
            border-radius: 4px;
            font-size: 1rem;
            line-height: 1;
            color: var(--secondary-text-color);
            cursor: pointer;
            flex-shrink: 0;
            align-self: center;
            transition: background 150ms ease, color 150ms ease;
        }
        .trh-header .collapse-btn:hover {
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
        }

        /* .remote-receiver-scope RETIRED, punch list item 9. It was the
           2026-08-14 inline standoff box: the receiver picker sat on the
           name row behind a left border, and its chips wrapped inside
           that box. The handoff's header replaces the whole arrangement
           -- the standoff border becomes the full-height
           .rdetail-divider above, and the box's shrink-and-wrap job
           moves inside ir-header-chip-group, whose own label column and
           flex-wrap chips column now do it row by row. The rules that
           made the old box behave (min-width: 0 on the box and on its
           chip-group children) went with it; the replacements live in
           .rdetail-top's block above and in the component itself. */

        /* Triggers section header (owner ruling 2026-08-15):
           parity with the .commands-header already used in
           ir-device-detail.ts -- a named remote trigger list
           used to start directly under the drawer header
           with no label of its own, unlike Commands.
           Same-day follow-up: the Trigger Drawer catch-all
           gets this header too, above its own trigger-rows
           / empty-state block -- .trh-subtitle (its
           previous, differently formatted count) is
           retired. */
        .trh-triggers-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 500;
            margin: 4px 0 8px;
            padding-top: 9px;
            border-top: 1px solid var(--divider-color);
            color: var(--primary-text-color);
        }

        /* --- Trigger row list (SortableJS grip-drag) --- */
        .trigger-rows {
            display: flex;
            flex-direction: column;
        }
        .trigger-rows ir-trigger-row.sortable-ghost {
            opacity: 0.4;
        }
        .grip-handle {
            --mdc-icon-size: 18px;
            color: var(--disabled-text-color, #999);
            cursor: grab;
        }
        .trigger-drawer-empty {
            padding: 20px 8px;
            text-align: center;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-list": IrDeviceList;
    }
}
