/**
 * Shared trigger-picker popover.
 *
 * Rendered when a signal row's Trigger button is clicked and one or more
 * triggers already bind that signal's fingerprint (the zero-trigger case
 * bypasses the popover and opens the Create dialog directly). Hosts the
 * "+ new trigger" action plus one row per existing trigger, each showing its
 * receiver scope. Emits `create-new` and `edit-trigger` (detail = the
 * trigger) for the parent to handle.
 *
 * The parent owns position (`top`/`left`) and dismiss-on-outside-click /
 * dismiss-on-scroll, mirroring the action-popover pattern in
 * ir-device-detail.ts.
 *
 * Add Popups signpost 2 punch list item 8 (ruled 2026-08-10, scoped
 * 2026-08-17): each row now also names its OWNING remote (the drawer
 * or a named TriggerRemote), so a signal that already triggers on two
 * different remotes reads that way across the popover's rows. Self-
 * fetched off an optional `.api` -- see that property's own doc below.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { popoverStyles } from "./ir-popover-styles.js";
import type { HairApi } from "./api.js";
import type { IRTrigger, ReceiverInfo, TriggerRemoteInfo } from "./types.js";

@customElement("ir-trigger-popover")
export class IrTriggerPopover extends LitElement {
    @property({ attribute: false }) triggers: IRTrigger[] = [];
    @property({ attribute: false }) receivers: ReceiverInfo[] = [];
    @property({ type: Number }) top = 0;
    @property({ type: Number }) left = 0;

    /** Add Popups signpost 2 punch list item 8: HAIR API client, used
     *  only to self-fetch the named-remote list + drawer name for the
     *  "on <remote>" line below -- the same self-fetch shape
     *  ir-receiver-picker.ts already uses for its own chip labels.
     *  Optional so a caller that never sets it keeps rendering exactly
     *  as before (no remote label). */
    @property({ attribute: false }) api?: HairApi;

    @state() private _remotes: TriggerRemoteInfo[] = [];
    @state() private _drawerName: string | null = null;
    private _remotesLoaded = false;

    updated(changed: Map<string, unknown>): void {
        super.updated(changed);
        if (changed.has("api") && this.api && !this._remotesLoaded) {
            this._remotesLoaded = true;
            void this._loadRemotes();
        }
    }

    private async _loadRemotes(): Promise<void> {
        if (!this.api) return;
        try {
            this._remotes = await this.api.listTriggerRemotes();
        } catch {
            this._remotes = [];
        }
        try {
            this._drawerName = (await this.api.getTriggerDrawer()).name;
        } catch {
            this._drawerName = null;
        }
    }

    render() {
        return html`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${t("popover.triggers")}</div>
                <button
                    class="popover-item accent"
                    @click=${() => this._emit("create-new")}
                >
                    <span>${t("popover.new_trigger")}</span>
                </button>
                <div class="popover-divider"></div>
                ${this.triggers.map(
                    (trig) => html`
                        <button
                            class="popover-item"
                            @click=${() => this._emit("edit-trigger", trig)}
                        >
                            <span class="popover-row">
                                <span class="popover-name">${trig.name}</span>
                                <span class="popover-scope"
                                    >${this._renderMeta(trig)}</span
                                >
                            </span>
                        </button>
                    `,
                )}
            </div>
        `;
    }

    private _renderScope(trig: IRTrigger): string {
        const ids = trig.receiver_entity_ids ?? [];
        if (ids.length === 0) return t("popover.any_receiver");
        if (ids.length === 1) return this._friendly(ids[0]);
        return t("popover.n_more", {
            name: this._friendly(ids[0]),
            count: ids.length - 1,
        });
    }

    /** Add Popups signpost 2 punch list item 8: prefix each row with
     *  its owning remote's name. A remote-owned trigger's receiver
     *  scope is inert (see ir-trigger-dialog.ts's identical note), so
     *  only the drawer-owned case still appends _renderScope()'s
     *  text after the remote name. */
    private _renderMeta(trig: IRTrigger): string {
        const remoteName = trig.trigger_remote_id
            ? this._remotes.find((r) => r.id === trig.trigger_remote_id)?.name ??
              t("common.kind_remote")
            : this._drawerName ?? t("devlist.trigger_drawer_default_name");
        const onRemote = t("popover.trigger_on_remote", { name: remoteName });
        return trig.trigger_remote_id
            ? onRemote
            : `${onRemote} - ${this._renderScope(trig)}`;
    }

    private _friendly(entityId: string): string {
        const match = this.receivers.find((r) => r.entity_id === entityId);
        return match?.name ?? entityId;
    }

    private _emit(kind: string, trigger?: IRTrigger): void {
        this.dispatchEvent(
            new CustomEvent(kind, {
                detail: trigger,
                bubbles: true,
                composed: true,
            }),
        );
    }

    static styles = [
        popoverStyles,
        css`
            :host {
                display: contents;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-popover": IrTriggerPopover;
    }
}
