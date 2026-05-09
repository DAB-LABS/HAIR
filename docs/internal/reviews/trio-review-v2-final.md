# Trio Review Board — Integration Plan v2 (Final Pass)

**Date:** 2026-05-08
**Moderator:** David Bailey
**Panelists:** CTO, Senior Dev, HA Power User
**Document Under Review:** `plans/integration-plan-v2.md`

---

## Moderator

This is the final review pass. The v2 plan incorporates all 16 action items from the first review. I'm looking for sign-off or critical blockers only. Let's keep this tight.

---

## Quick Reactions

### CTO

The v2 plan is substantially improved. Three things I particularly like:

1. **Entity auto-mapping** — Commands automatically linking to entity features as they're captured is elegant. No configuration step, no "map your commands" wizard. You capture "Volume Up" and the media_player just *knows* it can do volume control.

2. **Phase 0 → 1 → 2 cadence** — Starting with capture validation before building the full panel is the right call. If the capture UX sucks on real hardware, nothing else matters.

3. **The guided checklist** — This is genuinely innovative in the HA ecosystem. No other integration does guided device setup like this. It'll be the thing people screenshot and share.

One remaining concern: **the 12-week timeline is aggressive** for a side project. Are we okay shipping Phase 1 with known gaps (no climate entity) and documenting the roadmap publicly? Users need to know climate support is coming, not missing forever.

### Senior Dev

Architecturally, v2 is solid. The `CaptureProvider` abstraction is clean and extensible. A few small gaps I want to flag:

1. **ESPHome native API access** — The ESPHome capture provider needs to subscribe to the ESPHome device's native API for IR receiver events. This works if the ESPHome device is configured in HA, but we're coupling to ESPHome's internal API. If ESPHome changes their IR receiver event format, we break. We should pin to a minimum ESPHome version in our docs.

2. **Climate preset approach** — I'm satisfied with preset-based climate for v1, but we should document the future state explicitly. Users coming from SmartIR will expect temperature sliders. The documentation should explain *why* we use presets and when full climate control is planned.

3. **Testing the capture flow** — This is inherently hard to unit test since it involves real hardware. We should define a `MockCaptureProvider` for testing that simulates signal reception with configurable delays and failure modes.

4. **Frontend bundle size** — Five separate JS files for the panel could be a concern. Consider bundling them into a single file for the HACS distribution. HA custom panels load a single JS file per panel.

### HA Power User

The capture checklist is exactly what I wanted. The "Save & Learn Next" auto-advance is the kind of detail that separates a good integration from a great one.

My remaining UX concerns:

1. **First-run experience when no receiver is available.** The plan handles "no emitters" well, but what about "emitter exists but no receiver?" An ESPHome device with an IR transmitter LED but no receiver component can *send* but not *capture.* The error message for this case needs to be crystal clear: "Your IR blaster can send commands but can't learn them. Add an IR receiver component to your ESPHome device, or use a Broadlink RM device for learning." Include a link to a setup guide.

2. **The AC preset capture UX.** In the climate command template, we have "Mode: Cool", "Mode: Heat", etc. But as I mentioned in the first review, many AC remotes send the entire device state with each press. If a user captures "Mode: Cool" while their AC is set to 72°F, the captured code will always set 72°F when played back. The UX needs to warn about this:

    > "Before learning AC commands, set your AC to a neutral state: temperature 72°F, fan auto. Each command you learn will include these settings."

3. **Accessibility.** The pulsing dots animation in the capture dialog needs an `aria-live` region and screen reader text. The progress bar needs proper `aria-valuenow`. These are easy to add but easy to forget.

---

## Focused Discussion: The Receiver Gap

### Moderator
The "emitter exists but no receiver" scenario came up again. This is the biggest UX risk. Let's nail the solution.

### Senior Dev

There are actually three hardware configurations we need to handle:

| Configuration | Can Send? | Can Capture? | Example |
|---|---|---|---|
| ESPHome with TX + RX | Yes | Yes | ESP32 + IR LED + IR receiver |
| ESPHome with TX only | Yes | No | ESP32 + IR LED only |
| Broadlink RM | Yes | Yes | Broadlink RM4 Mini |
| SMLIGHT SLZB | Yes | Unknown | Needs investigation |

The config flow should probe for capture capability:

```python
async def _detect_capture_providers(self) -> list[CaptureProvider]:
    """Find available capture-capable devices."""
    providers = []

    # Check ESPHome devices with IR receiver
    for entry in self.hass.config_entries.async_entries("esphome"):
        if await self._esphome_has_ir_receiver(entry):
            providers.append(ESPHomeCaptureProvider(entry))

    # Check Broadlink devices
    for entry in self.hass.config_entries.async_entries("broadlink"):
        if await self._broadlink_supports_learning(entry):
            providers.append(BroadlinkCaptureProvider(entry))

    return providers
```

### CTO

Important: **the capture device and the emitter device don't have to be the same device.** A user might capture with a Broadlink RM4 in the same room, but send via an ESPHome blaster mounted near the TV. The config flow should allow selecting them independently:

- **Emitter:** Which device sends commands (for daily use)
- **Capture device:** Which device listens for learning (for setup only)

This doubles the compatible hardware configurations and solves the "emitter exists but no receiver" problem — users can borrow a Broadlink for learning, then send via any emitter.

### HA Power User

That's a great insight. But the UX needs to handle it gracefully. If the user only has one device that does both, don't show them two separate selection steps. Auto-detect and combine:

```
Found IR Hardware:
✓ ESPHome IR Blaster (can send + learn)
→ Using this for everything

--- OR ---

Found IR Hardware:
✓ ESPHome IR Blaster (can send)
✓ Broadlink RM4 (can send + learn)
→ Learning with: Broadlink RM4
→ Sending with: ESPHome IR Blaster
[Change ▾]
```

### Moderator
Excellent. The separation of capture device and emitter device is a critical architecture decision. Let's capture that.

---

## Focused Discussion: Frontend Bundling

### Senior Dev

For a custom integration panel, HA loads a single JavaScript file. The v2 plan lists five separate files. Here's what I recommend:

**Development:** Separate component files for maintainability.
**Distribution:** Bundle into a single `ha-panel-ir-devices.js` using rollup or esbuild before HACS release.

The build step is standard for HA frontend development. We should add a `script/build_frontend` script to the repo.

### CTO

Agreed. The frontend build pipeline should be part of the repo from day one. Also, consider using HA's built-in web components (`ha-card`, `ha-dialog`, `ha-button`, `ha-icon-button`, `ha-list-item`, etc.) wherever possible. They inherit the user's HA theme automatically, which means HAIR looks native without any custom CSS.

### HA Power User

As a user, I want the panel to look like it *belongs* in HA. The Z-Wave and Matter panels look native because they use HA's components. If HAIR uses custom-styled components, it'll feel like a third-party add-on rather than an integral part of HA. Match the Settings page styling exactly.

---

## Final Sign-Off

### CTO — APPROVED with notes

The plan is ready for implementation. Notes:
- Consider the branding question before HACS listing (HAIR vs. IR Devices vs. something else)
- Document the roadmap publicly so users know climate entity evolution is coming
- Track speed-to-market closely; first-mover advantage matters here

### Senior Dev — APPROVED with notes

Architecture is sound. Notes:
- Add `MockCaptureProvider` to the architecture doc
- Pin minimum ESPHome version for IR receiver compatibility
- Frontend must be a single bundled JS file for distribution
- Add the capture device / emitter device separation to the data model

### HA Power User — APPROVED with notes

The UX is strong and thoughtfully designed. Notes:
- Add the AC preset warning to the capture flow
- Ensure accessibility (aria labels, screen reader support)
- The transmitter/receiver separation is critical — don't skip it
- First-time experience for "no receiver" needs a clear setup guide link

---

## Final Action Items (v2 → Implementation)

| # | Item | Owner | Priority |
|---|---|---|---|
| 1 | Separate capture device from emitter device in data model and config flow | Architecture | Critical |
| 2 | Add `MockCaptureProvider` for testing | Architecture | High |
| 3 | Bundle frontend into single JS file (add build pipeline) | Architecture | High |
| 4 | Add AC preset state warning to capture flow UX | Architecture | Medium |
| 5 | Document accessibility requirements (aria labels) | Architecture | Medium |
| 6 | Pin minimum ESPHome version for IR receiver support | Architecture | Medium |
| 7 | Document public roadmap (preset climate → full climate) | Pre-launch | Medium |
| 8 | Final branding decision before HACS listing | Pre-launch | Low |
| 9 | Probe capture capability in config flow auto-detection | Architecture | High |
| 10 | Use HA native web components for panel styling | Architecture | High |

---

## Consensus: Ready for Code Architecture Phase

The Trio Review Board unanimously approves the v2 integration plan with the action items above incorporated into the code architecture document. The plan is architecturally sound, UX-focused, and appropriately scoped for phased release.

The guided checklist capture flow is the standout feature that differentiates HAIR from all existing IR solutions. It should receive the most implementation attention and polish.

*Proceeding to Code Architecture phase.*
