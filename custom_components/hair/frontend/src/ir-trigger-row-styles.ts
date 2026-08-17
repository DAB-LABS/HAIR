/**
 * The trigger-row anatomy, shared (signpost 4, Track M, decision 8).
 *
 * A trigger row is two lines: a name cluster on the left of line one
 * with a right-hand readout and controls, and the S/L diamond
 * fingerprint alone on line two, indented to sit under the name's
 * first letter. The LAST HEARD row on a matrix Remote is that same
 * anatomy holding a different fact, so the shape lives here instead of
 * being retyped -- the ir-popover-styles / ir-action-chip-styles cure,
 * applied to rows.
 *
 * What is HERE is only what both rows must agree on: the row box, the
 * two-line frame, the name cluster, and the diamonds. What stays local
 * to ir-trigger-row.ts is everything only a real trigger has -- the
 * toggle, the inline rename, the pin and scope chips, the reserved
 * 144px aliveness column (a LIST of rows must align against each
 * other; the Last Heard row is always alone and has nothing to align
 * against, so it deliberately does NOT take that reservation).
 *
 * ``relTime`` rides along for the same reason. It is not CSS, but it
 * is part of the row's shared vocabulary -- "2 min ago" has to read
 * identically on both rows or the two look like different features --
 * and one four-line pure function does not earn a module of its own.
 */
import { css } from "lit";
import { t } from "./localize.js";

export const triggerRowStyles = css`
    :host {
        display: block;
    }
    .trow {
        padding: 8px 10px;
        border-radius: 4px;
        background: var(--primary-background-color);
        border: 1px solid transparent;
    }
    .trow-top {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }
    .trow-grip {
        flex: 0 0 24px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .trow-namewrap {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        flex: 1 1 auto;
        min-width: 0;
        font-weight: 500;
    }
    .trow-name {
        font-size: 0.92rem;
    }
    /* Line 2: diamonds alone, full width, wrapping freely.
       36px aligns the first diamond under the name's first
       letter: the grip's flex-basis (24px) + .trow-top's gap
       (12px). */
    .trow-diamonds {
        margin-left: 36px;
        margin-top: 4px;
        min-height: 1px;
    }
    .diamonds {
        display: inline-flex;
        gap: 1px;
        flex-wrap: wrap;
        line-height: 1;
    }
    .diamond {
        font-size: 0.7rem;
    }
    .diamond.long {
        color: var(--primary-color);
    }
    .diamond.short {
        color: var(--warning-color, #ff9800);
    }
`;

/** Relative time like "2 min ago", on the four-tier scale every row
 *  readout uses. */
export function relTime(iso: string | null): string {
    if (!iso) return "";
    try {
        const diff = Date.now() - new Date(iso).getTime();
        if (diff < 60_000) return t("rel.just_now");
        if (diff < 3_600_000)
            return t("rel.min_ago", { count: Math.floor(diff / 60_000) });
        if (diff < 86_400_000)
            return t("rel.h_ago", { count: Math.floor(diff / 3_600_000) });
        return t("rel.d_ago", { count: Math.floor(diff / 86_400_000) });
    } catch {
        return "";
    }
}
