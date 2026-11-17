/**
 * The code boxes' copy icon: one click copies the code.
 *
 * Both code editors use it. The order:
 *
 * 1. The clipboard API, where the page is a secure context (https or
 *    localhost). The panel is not in an iframe, so it is allowed there.
 * 2. Otherwise, or if the browser refuses, the browser's own copy
 *    command on a temporary textarea holding the text. Over plain http
 *    there is no ``navigator.clipboard`` at all, so this runs straight
 *    away, inside the click, which the browser requires.
 * 3. If both fail, the code box is selected and the caller asks the
 *    user to press Cmd/Ctrl+C.
 *
 * The temporary textarea goes inside the code box's own container,
 * not on the page body: the editors are modal dialogs, and everything
 * outside a modal dialog is inert, so it could not take the selection
 * there. It holds the text to copy rather than reusing the box, because
 * what is copied is not always what the box shows (the radio editor
 * copies the code as a .sub file).
 */

/** The browser's copy command on a temporary textarea inside
 *  ``container``. True only when the browser says it copied. */
export function copyWithCommand(text: string, container: HTMLElement): boolean {
    const doc = container.ownerDocument;
    const root = container.getRootNode() as Document | ShadowRoot;
    const before = (root.activeElement ?? null) as HTMLElement | null;
    const scratch = doc.createElement("textarea");
    scratch.value = text;
    // Read-only keeps a phone's keyboard from opening; fixed and
    // transparent keep the page from scrolling or flashing.
    scratch.setAttribute("readonly", "");
    scratch.setAttribute("aria-hidden", "true");
    scratch.tabIndex = -1;
    scratch.style.cssText =
        "position:fixed;top:0;left:0;width:1px;height:1px;padding:0;border:0;" +
        "opacity:0;pointer-events:none;";
    container.appendChild(scratch);
    let copied = false;
    try {
        scratch.focus();
        scratch.select();
        scratch.setSelectionRange(0, text.length);
        copied = doc.execCommand("copy");
    } catch {
        copied = false;
    }
    scratch.remove();
    before?.focus?.();
    return copied;
}

/**
 * Copy ``text`` for the code box ``box``. Resolves true when the text
 * really reached the clipboard; false after selecting the box, so the
 * user can copy it with the keyboard.
 */
export async function copyCodeBox(
    text: string,
    box: HTMLTextAreaElement | null,
): Promise<boolean> {
    const clipboard = window.isSecureContext ? navigator.clipboard : undefined;
    if (clipboard?.writeText) {
        try {
            await clipboard.writeText(text);
            return true;
        } catch {
            // Refused: try the copy command below.
        }
    }
    const container = box?.parentElement;
    if (container && copyWithCommand(text, container)) return true;
    if (box) {
        box.focus();
        box.select();
    }
    return false;
}
