/**
 * Shared popover styles.
 *
 * Lit CSS is component-scoped: a `static styles = css\`...\`` block in one
 * component cannot be imported by a sibling. This module exports the
 * `.action-popover` styling (originally inline in ir-device-detail.ts) as a
 * tagged-template `css` result so every component that hosts a popover can
 * spread it: `static styles = [popoverStyles, css\`...\`]`.
 *
 * Consumers: ir-device-detail (action-mapping popover), ir-trigger-popover
 * (trigger picker). Keep visual parity with the original device-detail block.
 */
import { css } from "lit";

export const popoverStyles = css`
    .action-popover {
        position: fixed;
        z-index: 50;
        min-width: 200px;
        max-width: 280px;
        background: var(--card-background-color, #1c1c1c);
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
        padding: 4px 0;
        overflow: auto;
        max-height: 320px;
    }
    .popover-header {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--secondary-text-color);
        padding: 6px 12px 4px;
    }
    .popover-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 7px 12px;
        background: none;
        border: none;
        color: var(--primary-text-color);
        font-size: 0.82rem;
        font-family: inherit;
        cursor: pointer;
        text-align: left;
        transition: background 100ms ease;
    }
    .popover-item:hover {
        background: var(--secondary-background-color);
    }
    .popover-item.active {
        color: var(--primary-color);
        font-weight: 500;
    }
    .popover-item.clear {
        color: var(--secondary-text-color);
        font-style: italic;
        border-bottom: 1px solid var(--divider-color);
        margin-bottom: 2px;
    }
    .popover-check {
        color: var(--primary-color);
        font-size: 0.9rem;
    }
    .popover-existing {
        font-size: 0.72rem;
        color: var(--secondary-text-color);
        font-style: italic;
        margin-left: 8px;
        flex-shrink: 0;
    }
    /* Trigger-popover extras (v0.5.7) */
    .popover-item.accent {
        color: var(--primary-color);
        font-weight: 500;
    }
    .popover-divider {
        height: 1px;
        background: var(--divider-color);
        margin: 2px 0;
    }
    .popover-row {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 2px;
        min-width: 0;
    }
    .popover-name {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 240px;
    }
    .popover-scope {
        font-size: 0.7rem;
        color: var(--secondary-text-color);
    }
    /* Kind badge (signpost 3, Track 2 item 0.1 / Track 3 item 1): the
       combined device+remote linked popover tags each row green
       Device / gold Remote, same accent colors as the USE fork's own
       two tiles (ir-use-fork-popup.ts / ir-origin-colors.ts). */
    .popover-kind-badge {
        font-size: 0.6rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 1px 5px;
        border-radius: 3px;
        margin-right: 6px;
        flex: none;
    }
    .popover-kind-badge.kind-device {
        background: rgba(46, 125, 50, 0.18);
        color: #2e7d32;
    }
    .popover-kind-badge.kind-remote {
        background: rgba(245, 166, 35, 0.18);
        color: #f5a623;
    }
`;
