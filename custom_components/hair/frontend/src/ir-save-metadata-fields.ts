/**
 * The metadata form shared by every Save to Closet dialog: name,
 * brand, model, product identifiers, notes.
 *
 * Second Fitting v3 (coding plan Commit 4: "extract the metadata form
 * into the shared piece it already almost is") pulls this out of the
 * one dialog that used to carry it plus the perfect-fit section right
 * beside it. Save as New and Update Closet Wig both render the
 * identical fields now without two copies drifting the way the house
 * anatomy already drifted once before ir-dialog-styles cured it.
 *
 * A plain function, not a LitElement: the fields are simple enough
 * that a shared component would need as much plumbing (value
 * properties in, change events out) as it saves, and every caller
 * already owns this state as its own @state() fields.
 */
import { html } from "lit";
import { t } from "./localize.js";
import type { KindEntry } from "./types.js";

/** What the kind dropdown needs, on its own.
 *
 * Split out from the metadata form because the closet editor renders
 * the same dropdown without the rest of the form around it, and one
 * list, one dropdown (ruled 2026-09-16) is a promise about the markup
 * as much as about the words. */
export interface KindFieldValues {
    /** The KIND_LIST key the dropdown has selected, "" for a wig
     * nobody has described yet. Never a free-text word. */
    kind: string;
    /** The file's own word, when the list cannot place it. Shown under
     * the dropdown so the person can see what they are about to
     * replace; empty whenever the file and the list agree. */
    kindRaw: string;
    /** The vocabulary, as hair/wigs/kinds served it. Empty until the
     * fetch lands, which renders the dropdown with its current value
     * alone rather than an empty list. */
    kinds: KindEntry[];
}

export interface KindFieldSetters {
    setKind: (v: string) => void;
}

export interface MetadataFieldValues extends KindFieldValues {
    name: string;
    brand: string;
    model: string;
    notes: string;
    fccId: string;
    upc: string;
    asin: string;
    oem: string;
}

export interface MetadataFieldSetters extends KindFieldSetters {
    setName: (v: string) => void;
    setBrand: (v: string) => void;
    setModel: (v: string) => void;
    setNotes: (v: string) => void;
    setFccId: (v: string) => void;
    setUpc: (v: string) => void;
    setAsin: (v: string) => void;
    setOem: (v: string) => void;
}

function _field(
    label: string,
    value: string,
    set: (v: string) => void,
    placeholder = "",
) {
    return html`
        <div class="field">
            <label>${label}</label>
            <input
                type="text"
                .value=${value}
                placeholder=${placeholder}
                @input=${(e: Event) =>
                    set((e.target as HTMLInputElement).value)}
            />
        </div>
    `;
}

/** The kind dropdown, shared by every surface that edits kind.
 *
 * One list, one dropdown (ruled 2026-09-16): the options come from
 * hair/wigs/kinds and nothing here knows a kind word of its own. The
 * leading blank is "not set", which is what a wig nobody has described
 * carries -- distinct from Other, which is a real answer for a device
 * that fits no word on the list. `kindRaw` renders the file's own word
 * under it when the list could not place what the file says.
 */
export function renderKindField(
    values: KindFieldValues,
    set: KindFieldSetters,
) {
    return html`
        <div class="field">
            <label>${t("wigs.editor.kind")}</label>
            <select
                .value=${values.kind}
                @change=${(e: Event) =>
                    set.setKind((e.target as HTMLSelectElement).value)}
            >
                <option value="" ?selected=${!values.kind}>
                    ${t("wigs.editor.kind_unset")}
                </option>
                ${values.kinds.map(
                    (entry) => html`<option
                        value=${entry.key}
                        ?selected=${entry.key === values.kind}
                    >
                        ${t(entry.label_key)}
                    </option>`,
                )}
            </select>
            ${values.kindRaw
                ? html`<div class="ident-hint">
                      ${t("wigs.editor.kind_file_value", {
                          value: values.kindRaw,
                      })}
                  </div>`
                : ""}
        </div>
    `;
}

/** `renameWarning`: non-null shows the "this renames the file itself"
 * caution under the name field. Update Closet Wig's own concern (the
 * name field there can rename the very wig the save might override);
 * Save as New never passes one, since it always mints a fresh file
 * under whatever name is typed. */
export function renderMetadataFields(
    values: MetadataFieldValues,
    set: MetadataFieldSetters,
    renameWarning: string | null,
) {
    return html`
        <div class="field">
            <label>${t("common.name")}</label>
            <input
                type="text"
                .value=${values.name}
                @input=${(e: Event) =>
                    set.setName((e.target as HTMLInputElement).value)}
            />
            ${renameWarning
                ? html`<div class="rename-warn">${renameWarning}</div>`
                : ""}
        </div>
        <div class="pair-grid">
            ${_field(
                t("wigs.editor.brand"),
                values.brand,
                set.setBrand,
                t("wigs.export.brand_hint"),
            )}
            ${_field(t("wigs.editor.model"), values.model, set.setModel)}
            ${_field(t("wigs.editor.fcc_id"), values.fccId, set.setFccId)}
            ${_field(t("wigs.editor.upc"), values.upc, set.setUpc)}
            ${_field(t("wigs.editor.asin"), values.asin, set.setAsin)}
            ${_field(t("wigs.editor.oem"), values.oem, set.setOem)}
        </div>
        <div class="ident-hint">${t("wigs.editor.ids_hint")}</div>
        ${renderKindField(values, set)}
        <div class="field">
            <label>${t("wigs.editor.notes")}</label>
            <input
                type="text"
                .value=${values.notes}
                placeholder=${t("wigs.editor.notes_placeholder")}
                @input=${(e: Event) =>
                    set.setNotes((e.target as HTMLInputElement).value)}
            />
        </div>
    `;
}

// Styling (.pair-grid, .ident-hint, .rename-warn) stays with each
// caller's own `static styles`, layered after `dialogStyles` exactly
// as every other per-component override already does in this family
// -- a `css` export from a plain function module would fight Lit's
// own static-styles composition rather than joining it.
