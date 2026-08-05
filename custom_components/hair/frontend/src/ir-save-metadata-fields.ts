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

export interface MetadataFieldValues {
    name: string;
    brand: string;
    model: string;
    notes: string;
    fccId: string;
    upc: string;
    asin: string;
    oem: string;
}

export interface MetadataFieldSetters {
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
