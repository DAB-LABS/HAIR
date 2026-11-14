/**
 * The one file picker for code-set files.
 *
 * The Closet's Browse and the ghost tile's folder button both open the
 * system file dialog for the same kinds of file, so the accepted types
 * live here once (they used to live only in ir-wigs.ts) and both call
 * the same function.
 *
 * `accept` is a hint to the dialog, not a filter: a person can still
 * pick any file, and the server decides what it can read.
 */

/** Code-set files HAIR can import: Wig, SmartIR, Flipper, LIRC, Girr,
 * Harmony, Global Cache, Tasmota and irdb all arrive as one of these. */
export const CODESET_ACCEPT =
    ".json,.ir,.conf,.girr,.xml,.csv,.txt,application/json,text/plain,text/csv";

/**
 * Open the system file dialog for one code-set file.
 *
 * Resolves with the chosen file, or null when nothing was chosen. A
 * cancelled dialog resolves null through the input's `cancel` event
 * where the browser fires one. Where it does not, the promise simply
 * never settles, so a caller must not hold state that waits on it:
 * act when it resolves with a file, and do nothing before.
 */
export function pickOneFile(): Promise<File | null> {
    return new Promise((resolve) => {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = CODESET_ACCEPT;
        input.addEventListener("change", () => {
            resolve(input.files?.[0] ?? null);
        });
        input.addEventListener("cancel", () => resolve(null));
        input.click();
    });
}
