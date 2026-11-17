/**
 * The Clipper's add window: one window for any code HAIR reads.
 *
 * The user pastes anything. The window shows the infrared editor or the
 * radio editor inside itself, whichever the paste is, and the code stays
 * in the box while the fields under it change. Which one is the server's
 * answer (`medium` on both validate doors, `paste_medium.py`), never a
 * guess here: each editor, `embedded`, hands a paste of the other medium
 * back with `medium-changed`, and this window shows the other editor
 * with the same text.
 *
 * Everything else is the editors' own: validation, "Recognized as" and
 * the pill, repairs, the rolling-code line, the duplicate refusal, and
 * the `signal-created` event the Clipper already listens for.
 */
import { LitElement, html, css } from "lit";
import { keyed } from "lit/directives/keyed.js";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import { editorFor, hintLines, type Medium } from "./paste-formats.js";
import "./ir-signal-editor.js";
import "./ir-rf-editor.js";

@customElement("ir-add-code-dialog")
export class IrAddCodeDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    /** The clipped remote the code is added to. */
    @property({ attribute: false }) public deviceId!: string;

    /** Infrared until a paste says otherwise. */
    @state() private _medium: Medium = "ir";
    /** The text and name handed to the editor now shown. */
    @state() private _text = "";
    @state() private _alias = "";
    /** Bumped on each hand-over, so the new editor starts fresh. */
    @state() private _turn = 0;

    private _onMediumChanged(
        e: CustomEvent<{ medium: string | null; text: string; alias: string }>,
    ): void {
        e.stopPropagation();
        // Only the editor shown now: one already swapped out may still
        // have an answer on its way.
        const shown = this.shadowRoot?.querySelector("ir-signal-editor, ir-rf-editor");
        if (e.target !== shown) return;
        const next = editorFor(this._medium, e.detail.medium);
        if (next === this._medium) return;
        this._text = e.detail.text;
        this._alias = e.detail.alias;
        this._medium = next;
        this._turn++;
    }

    private _close(): void {
        this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
    }

    render() {
        const hint = hintLines(t);
        const editor =
            this._medium === "ir"
                ? html`<ir-signal-editor
                      embedded
                      .api=${this.api}
                      .deviceId=${this.deviceId}
                      .initialPronto=${this._text}
                      .initialAlias=${this._alias}
                      .hint=${hint}
                      @medium-changed=${this._onMediumChanged}
                  ></ir-signal-editor>`
                : html`<ir-rf-editor
                      embedded
                      .api=${this.api}
                      .deviceId=${this.deviceId}
                      .initialCode=${this._text}
                      .initialAlias=${this._alias}
                      .hint=${hint}
                      @medium-changed=${this._onMediumChanged}
                  ></ir-rf-editor>`;
        // The dialog's own child never changes: only what is inside it.
        // Replacing a dialog's whole content at once has left it dark
        // before (ir-save-new-dialog.ts).
        return html`<ha-dialog open scrimClickAction="" @closed=${this._close}>
            <div class="body">${keyed(`${this._medium}-${this._turn}`, editor)}</div>
        </ha-dialog>`;
    }

    static styles = [dialogStyles, css``];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-add-code-dialog": IrAddCodeDialog;
    }
}
