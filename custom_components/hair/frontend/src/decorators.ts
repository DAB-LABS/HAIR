import { customElement as litCustomElement } from "lit/decorators.js";

// Re-export every Lit decorator (property, state, query, ...) unchanged. The
// explicit customElement export below takes precedence over the star
// re-export of the same name.
export * from "lit/decorators.js";

// A decorator that returns the class untouched, used when the tag is already
// registered.
const noop = ((value: unknown) => value) as unknown as ReturnType<
  typeof litCustomElement
>;

/**
 * customElement decorator that no-ops when the tag name is already registered.
 *
 * Home Assistant can re-evaluate a panel bundle within a live session (for
 * example after a frontend cache-bust), and Lit's stock decorator calls
 * customElements.define unconditionally. The second define throws a
 * DOMException and aborts the rest of the module, leaving later components
 * unregistered. Guarding the define makes a re-evaluation a harmless no-op.
 */
export const customElement = (
  name: string,
): ReturnType<typeof litCustomElement> =>
  customElements.get(name) ? noop : litCustomElement(name);
