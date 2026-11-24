/**
 * The Cover card's fields (GH #313), shared by the Device settings
 * dialog (a screen) and the Remote settings dialog (a Remote typed as a
 * screen): one menu of the kinds of cover, in the backend's order, and
 * the line under it that says what the choice changes. The rules are
 * cover-class.ts.
 */
import { html } from "lit";
import { t } from "./localize.js";
import type { CoverDeviceClass } from "./types.js";
import { COVER_DEVICE_CLASSES, coverClassLabelKey } from "./cover-class.js";

export function renderCoverClassField(
    chosen: CoverDeviceClass,
    busy: boolean,
    onChange: (kind: CoverDeviceClass) => void,
) {
    return html`
        <section class="settings-section section-cover">
            <div class="field">
                <label for="cover-class">${t("devsettings.cover_class_label")}</label>
                <div class="select-wrap">
                    <select
                        id="cover-class"
                        .value=${chosen}
                        @change=${(e: Event) =>
                            onChange(
                                (e.target as HTMLSelectElement).value as CoverDeviceClass,
                            )}
                        ?disabled=${busy}
                    >
                        ${COVER_DEVICE_CLASSES.map(
                            (kind) => html`<option
                                value=${kind}
                                ?selected=${chosen === kind}
                            >
                                ${t(coverClassLabelKey(kind))}
                            </option>`,
                        )}
                    </select>
                    <span class="select-chevron" aria-hidden="true"></span>
                </div>
                <p class="section-explainer">${t("devsettings.cover_class_help")}</p>
            </div>
        </section>
    `;
}
