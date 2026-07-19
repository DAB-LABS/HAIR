/**
 * Shared dialog styles.
 *
 * The third extraction in the family: ir-popover-styles (v0.5.7) cured
 * the popovers, ir-action-chip-styles (v0.6.6) cured the row chips, and
 * this module cures the dialogs. Every dialog in the panel carried its
 * own copy of the same anatomy -- the overlay shell, the field/input
 * block, the actions row, the cancel button, and one of two action
 * button families -- and the copies had already begun to drift (two
 * padding scales, two disabled cursors, three heading margins). One
 * source of truth now, spread into each consumer:
 *
 *   static styles = [dialogStyles, css`...component-specific...`];
 *
 * What stays local to each component, deliberately: the accent color of
 * its primary button (green Assign, copper Clipper, slate Plucker --
 * the per-tab identity), any layout unique to one dialog, and one-line
 * overrides where a dialog intentionally deviates (they layer after
 * this module in the styles array, so equal-specificity rules win).
 *
 * The two button families, preserved exactly as shipped:
 *   .action-btn          -- outlined chip (8/16px, 0.85rem, divider
 *                           border); the majority family, used by the
 *                           form dialogs.
 *   .action-btn.wide     -- solid borderless (8/20px, 0.9rem); the
 *                           assign and promote dialogs' family, whose
 *                           primary buttons fill with an accent.
 *
 * Consumers: ir-confirm-dialog, ir-trigger-dialog,
 * ir-assign-signal-dialog, ir-promote-dialog, ir-add-device-dialog,
 * ir-create-remote-dialog, ir-pluck-add-remote-dialog,
 * ir-pluck-signal-dialog, ir-test-emitter-dialog, ir-signal-editor.
 */
import { css } from "lit";

export const dialogStyles = css`
    /* --- Custom overlay shell (dialogs not hosted in <ha-dialog>) --- */
    .overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
    }
    .dialog {
        background: var(--card-background-color, #fff);
        border-radius: 12px;
        padding: 24px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .heading {
        margin: 0 0 16px;
        font-size: 1.1rem;
        font-weight: 500;
        color: var(--primary-text-color);
    }

    /* --- Form fields --- */
    .field {
        display: block;
        margin: 12px 0;
        width: 100%;
    }
    .field label {
        display: block;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
        margin-bottom: 6px;
    }
    input[type="text"],
    select {
        width: 100%;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 0.95rem;
        font-family: inherit;
        box-sizing: border-box;
    }
    input[type="text"]:focus,
    select:focus {
        outline: none;
        border-color: var(--primary-color);
    }

    /* --- Actions row --- */
    .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--divider-color);
    }

    /* --- Action buttons: outlined family (the majority) --- */
    .action-btn {
        background: none;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 0.85rem;
        font-weight: 500;
        font-family: inherit;
        cursor: pointer;
        transition: background 150ms ease;
    }
    .action-btn:disabled {
        opacity: 0.5;
        cursor: default;
    }

    /* --- Action buttons: solid borderless family (assign/promote) --- */
    .action-btn.wide {
        padding: 8px 20px;
        font-size: 0.9rem;
        border: none;
        transition: background 150ms ease, opacity 150ms ease;
    }
    .action-btn.wide:disabled {
        cursor: not-allowed;
    }

    /* --- The cancel button, identical everywhere --- */
    .cancel-btn {
        background: transparent;
        color: var(--secondary-text-color);
    }
    .cancel-btn:hover:not(:disabled) {
        background: var(--secondary-background-color);
    }
`;
