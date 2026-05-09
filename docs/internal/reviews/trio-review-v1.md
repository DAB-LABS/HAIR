# Trio Review Board — Integration Plan v1

**Date:** 2026-05-08
**Moderator:** David Bailey
**Panelists:**
- **CTO** — Architecture, scalability, market positioning
- **Senior Dev** — Implementation, HA platform constraints, edge cases
- **HA Power User** — UX, real-world usage, migration experience

**Document Under Review:** `plans/integration-plan-v1.md`

---

## Opening Remarks (Moderator)

We're reviewing the integration plan for HA IR Admin — a unified admin interface for IR devices in Home Assistant. The north star is *frictionless*. I want this panel to focus heavily on UX, but don't pull punches on architecture or implementation feasibility. Let's start with high-level reactions, then dig into specifics.

---

## Round 1: First Impressions

### CTO

The architecture is clean. I like the layered approach — storage, WebSocket API, frontend, entity platforms. The dependency on HA's native IR platform (2026.4) is the right call; building our own IR abstraction would be suicide by complexity.

My concern is **market timing**. We're one month after 2026.4 shipped. Someone else could be building this right now. Speed to market matters. I'd argue we strip the MVP even further — get device creation and command capture out the door, worry about climate entity sophistication later.

The positioning as "the Z-Wave JS UI, but for IR" is strong. That's a story people understand immediately.

### Senior Dev

The plan is ambitious but achievable. A few things jumped out:

1. **The IR receiving problem is undersolved.** The plan mentions Options A and B (ESPHome receiver, Broadlink learning mode) but doesn't address how we abstract over them. These are fundamentally different APIs. ESPHome gives you raw timing data via its native API. Broadlink gives you a blob via a service call. We need a `CaptureProvider` abstraction from day one, or we'll end up with spaghetti.

2. **The storage schema needs versioning strategy.** Version 1 is fine, but what happens when v1.1 adds command groups? Or v2.0 adds state tracking? We need a migration path designed now.

3. **WebSocket API + Frontend in a custom integration is significant frontend work.** Has anyone on the team built a LitElement panel for HA before? The Z-Wave JS panel is maintained by the core team with dedicated frontend developers. We're a custom integration — our frontend has to be self-contained, can't depend on unreleased HA frontend components.

### HA Power User

Okay, I'm going to be blunt: **the capture flow is the make-or-break moment.** Right now, if I want to learn an IR command with Broadlink, I have to:

1. Open Developer Tools
2. Call `broadlink.learn` service
3. Point my remote at the Broadlink
4. Press a button
5. Wait for the service call to return
6. Copy the raw data from the result
7. Paste it into a YAML file or SmartIR JSON

That's **seven steps**, three of which require developer knowledge. Your plan shows a 4-phase capture dialog that looks great on paper, but I have questions:

- **What happens when the capture fails?** Your error state table is good but the UX for "try again" needs to be instant. Don't make me dismiss a dialog and reopen it.
- **The "Test It" button after capture is brilliant.** That's the moment of delight. I press capture, I hear my TV click, I know it worked. Don't bury that button.
- **Command naming:** Pre-populate common command names based on device type. If I'm setting up a TV, suggest "Power," "Volume Up," "Volume Down," "Mute," "Source" etc. Don't make me type "Power" from scratch.

---

## Round 2: Deep Dive — Architecture

### Moderator
Let's dig into the CTO's concern about speed-to-market and the Senior Dev's concern about the capture abstraction.

### CTO

Here's my proposal for an even tighter MVP:

**Phase 0 (2 weeks):** Raw capture + storage only. No entity creation. Just let users capture IR commands and store them. Service call to send them. This validates the capture UX immediately.

**Phase 1 (4 weeks):** Add the admin panel, device CRUD, and basic entity creation (remote entity only — it's the simplest). Ship to HACS.

**Phase 2 (4 weeks):** media_player and climate entity platforms. This is where the real value unlocks but it's also the hardest part.

Why this phasing? Because the capture UX is the differentiator. If we nail that, everything else is plumbing. If we ship a mediocre capture UX buried inside a feature-complete integration, we lose.

### Senior Dev

I agree with the phasing but I want to push back on one thing: **don't skip entity creation in the first HACS release.** A capture-only tool with no entities is a tech demo, not an integration. Users will install it, capture some commands, and then ask "now what?" with no answer.

I'd compromise: Phase 1 ships with the `remote` entity platform only. That gives users something functional — they can call `remote.send_command` in automations. Climate and media_player come in Phase 2.

On the capture abstraction, here's my proposal:

```python
class CaptureProvider(ABC):
    """Abstract base class for IR capture providers."""

    @abstractmethod
    async def async_start_capture(self, timeout: int) -> None:
        """Start listening for IR signals."""

    @abstractmethod
    async def async_stop_capture(self) -> None:
        """Stop listening."""

    @abstractmethod
    async def async_get_result(self) -> CaptureResult | None:
        """Get the captured IR data."""

class ESPHomeCaptureProvider(CaptureProvider):
    """Capture via ESPHome remote_receiver."""

class BroadlinkCaptureProvider(CaptureProvider):
    """Capture via Broadlink learning mode."""
```

This way, adding a new capture source (say, SMLIGHT adds a receiver) is a single class implementation.

### HA Power User

I want to challenge something the CTO said. You said "capture UX is the differentiator." I'd say **capture UX is table stakes.** The real differentiator is the **device setup flow end-to-end.**

Let me describe what I actually want as a user:

1. I just bought a Daikin mini-split. I installed it. I have the remote.
2. I go to HA IR Admin, click "Add Device."
3. I select "Air Conditioner" and type "Daikin."
4. **HA IR Admin says: "We have codes for Daikin ACs. Want to try them?"**
5. I click yes. It sends a power-on command. My AC turns on. Magic.
6. I click "Use these codes" and I'm done. No manual capture needed.

That's the dream. The capture flow is the fallback for when we *don't* have codes in a database. The happy path should be "we already know your device."

### CTO

That's a v2 feature. We can't ship v1 with a device code database — that's a massive undertaking. But the HA Power User is right about the *vision*. The architecture should support a future where captured codes can be shared to a community database, and common devices have pre-loaded profiles.

### Senior Dev

Architecturally, this means the data model needs a `source` field on commands:

```
Command {
    ...
    source: "captured" | "database" | "imported"
    ...
}
```

And the device profile should support a `database_id` field for when we eventually match against a known device.

### Moderator

Good. Let's capture that as a v2 design consideration but not a v1 blocker. The data model should accommodate it now though.

---

## Round 3: Deep Dive — UX

### Moderator
Let's focus on the capture dialog and the overall user experience. Power User, tear it apart.

### HA Power User

The capture dialog as drawn has four phases. I want to simplify to three and make it tighter:

**Phase 1: Name + Start (combined)**
Don't make users click "Start Capture" as a separate step. The moment they type a name and hit Enter (or click a single button), we should start listening. Reduce clicks.

```
┌───────────────────────────────────┐
│  Learn: "Power"            [×]   │
│                                   │
│  Point your remote at the         │
│  IR receiver and press the        │
│  button for "Power"               │
│                                   │
│       ◉ ◉ ◉ Listening...         │
│       ████████░░░░  15s           │
│                                   │
│  [Cancel]                         │
└───────────────────────────────────┘
```

Wait — actually, I changed my mind. The name should be pre-filled from a template. For a TV, the first capture should auto-suggest "Power." The dialog should open straight into listening mode with a pre-filled name. The user can change the name, but the default is smart.

**Phase 2: Captured + Test**
```
┌───────────────────────────────────┐
│  Learn: "Power"            [×]   │
│                                   │
│       ✓ Captured!                 │
│                                   │
│  Protocol: NEC                    │
│                                   │
│  Did it work?                     │
│  [▶ Test]  [Re-capture]          │
│                                   │
│  [Save & Learn Next ▶]           │
└───────────────────────────────────┘
```

The key insight: **"Save & Learn Next" is the primary CTA**, not "Save." We expect users to capture multiple commands in sequence. The flow should bias toward staying in the capture loop.

**Phase 3: (No separate phase — it's inline)**
After saving, the dialog immediately transitions to the next suggested command name and starts listening again. The transition should feel seamless — a brief "Saved!" toast, then back to listening.

### Senior Dev

I love the streamlined dialog, but there's a technical subtlety with "auto-start listening." ESPHome and Broadlink have different latencies for entering learning mode. ESPHome is near-instant (it's just enabling the GPIO receiver). Broadlink can take 1-2 seconds to enter learning mode. We need a loading state between "dialog opens" and "actually listening."

Also, the "suggested command names" feature means we need a command template system per device type:

```python
DEVICE_COMMAND_TEMPLATES = {
    "tv": ["Power", "Volume Up", "Volume Down", "Mute", "Source", "Channel Up", "Channel Down"],
    "ac": ["Power", "Temperature Up", "Temperature Down", "Mode", "Fan Speed", "Swing"],
    "fan": ["Power", "Speed", "Oscillate", "Timer"],
    "soundbar": ["Power", "Volume Up", "Volume Down", "Mute", "Source"],
}
```

### CTO

Command templates are cheap to implement and hugely impactful on UX. Include them in MVP. The guided capture flow — where the system suggests the next command — turns a tedious task into a satisfying checklist experience.

Think about it: instead of staring at a blank command list wondering "what should I capture next?", the user sees:

```
Commands for Living Room TV:
☐ Power          [Learn]
☐ Volume Up      [Learn]
☐ Volume Down    [Learn]
☐ Mute           [Learn]
☐ Source         [Learn]
☐ Channel Up     [Learn]
☐ Channel Down   [Learn]
+ Add custom command
```

Each time they learn one, the checkbox fills in. It's gamified without being gimmicky.

### HA Power User

YES. That checklist view is the killer feature. It transforms "capture a bunch of IR codes" into "complete your device setup." Progress bars activate completion instinct.

But here's another UX issue nobody's mentioned: **what if the user captures the wrong command?** Say I press Volume Up when I meant to capture Power. The dialog says "Captured!" but I know it's wrong.

The "Re-capture" button handles this, but there's a subtler case: what if I don't realize the mistake until later? The command list in the device detail view needs an easy re-learn option on each command. Not buried in a menu — a visible "Re-learn" button.

### Senior Dev

We also need to handle **duplicate detection.** If the user captures the same IR signal for two different commands, we should warn them. Comparing raw timing data has tolerance issues (IR signals vary slightly each capture), but protocol + code matches should be flagged.

```
"This signal matches your existing 'Power Off' command. 
 Same command, different name? Or save as separate?"
```

---

## Round 4: Deep Dive — Climate Entity

### Moderator
Climate is the highest-value entity type (mini-splits, window ACs). It's also the hardest. Let's discuss.

### Senior Dev

Climate entities in HA expect bidirectional state. They show current temperature, target temperature, HVAC mode, fan mode, etc. IR is one-directional — you send a command and hope it worked. This creates a fundamental state-tracking problem.

SmartIR solves this with "assumed state" — it tracks what it thinks the state is based on commands sent. This works 90% of the time but breaks when:
- Someone uses the physical remote (HA doesn't know)
- A power outage resets the AC
- Multiple HA automations race

For MVP, I recommend **assumed state with a prominent "I don't know" escape hatch.** Show the assumed state but add a manual override button for when it's wrong.

### HA Power User

The SmartIR approach works well enough for daily use. The bigger UX question is: **how does the user set up climate commands?**

AC remotes are weird. Unlike TVs where each button does one thing, AC remotes send the *entire state* with every button press. When you press "Temperature Up" on a Daikin remote, it doesn't send "increment temperature." It sends "mode=cool, temp=73, fan=auto, swing=on" — the whole shebang.

This means capturing individual commands like "Temperature Up" and "Temperature Down" doesn't work for most ACs. You need to capture a **state matrix**: every combination of mode × temperature × fan speed.

### Senior Dev

That's the SmartIR approach — a JSON file with hundreds of codes, one per state combination. For MVP, I'd argue we go simpler:

**Approach 1: Raw command capture** — User captures "Set Cool 72°F" as a single command. Limited but functional. User creates as many temperature presets as they want.

**Approach 2: Protocol-aware state construction** — If we detect a known protocol (Daikin, Mitsubishi, etc.), we can construct state commands programmatically using the `infrared-protocols` library. This is the right long-term approach but requires protocol support in the library.

For MVP, I'd do Approach 1 with an architecture that supports Approach 2 in v2. The `infrared-protocols` library is brand new — device-specific encoders will come.

### CTO

Agreed. Don't try to solve the AC state matrix problem in v1. Offer basic climate entity support with captured commands (mode buttons, temperature presets), and leave full climate entity intelligence for v2 when the `infrared-protocols` library has more device encoders.

The v1 climate entity should be honest about its limitations. Don't pretend to have a temperature slider if we can only do presets.

### HA Power User

I can live with preset-based climate in v1. But make sure the UX communicates what's happening:

```
Climate Setup for Bedroom AC:
┌─────────────────────────────────────┐
│  HVAC Modes:                        │
│  ☑ Cool   [Learn command]           │
│  ☑ Heat   [Learn command]           │
│  ☑ Fan    [Learn command]           │
│  ☐ Dry    [Learn command]           │
│  ☑ Off    [Learn command]           │
│                                     │
│  Temperature Presets:                │
│  [Learn 68°F] [Learn 70°F]          │
│  [Learn 72°F] [Learn 74°F]          │
│  [+ Add preset]                     │
│                                     │
│  ℹ️ For full temperature control,    │
│  capture a command for each          │
│  temperature you commonly use.       │
└─────────────────────────────────────┘
```

This is transparent about the limitation while being functional. Users capture the 4-5 temperatures they actually use.

---

## Round 5: Final Concerns

### CTO

Three final items:

1. **Naming**: "HA IR Admin" is functional but boring. Consider something catchier for community recognition. "HAIR" as the repo name is memorable though — lean into it for branding.

2. **HACS listing**: Get this listed on HACS default repos ASAP. Custom repository installs have 10x higher friction.

3. **Documentation**: Plan for docs from day one. A GitHub Pages site with GIFs of the capture flow would drive adoption faster than any feature.

### Senior Dev

1. **Testing strategy**: We need integration tests for the capture flow, storage migration, and entity creation. Use `pytest-homeassistant-custom-component`.

2. **Error handling**: The capture timeout needs careful tuning. Too short (5s) and users fumble. Too long (60s) and they wait forever when something's wrong. I recommend 15s default with a visible countdown and an easy "try again" that doesn't require re-entering the command name.

3. **Concurrency**: What happens if two admin users open the capture dialog simultaneously? We need a lock on the receiver resource.

### HA Power User

1. **Onboarding**: First install should detect existing Broadlink/ESPHome devices and suggest "Want to set up IR devices with these?"

2. **Migration from SmartIR**: Offer an import path for SmartIR JSON files. Thousands of users have curated device profiles there. Don't make them re-capture everything.

3. **The name "IR Admin" makes it sound like it's for admins only.** Consider something friendlier for the sidebar. "IR Devices" or "Remotes" might be more inviting.

---

## Action Items

| # | Item | Priority | Phase |
|---|---|---|---|
| 1 | Add `CaptureProvider` abstraction to architecture | High | MVP |
| 2 | Add command templates per device type | High | MVP |
| 3 | Streamline capture dialog to 2-phase flow (listen → confirm+test) | High | MVP |
| 4 | Add `source` field to Command data model | Medium | MVP |
| 5 | Add `database_id` field to Device for future code database | Low | v2 prep |
| 6 | Add duplicate signal detection in capture flow | Medium | MVP |
| 7 | Add "Re-learn" button on each command in detail view | High | MVP |
| 8 | Implement guided checklist capture (suggested commands per device type) | High | MVP |
| 9 | Design climate entity as preset-based (not slider) for v1 | Medium | MVP |
| 10 | Add receiver resource locking (concurrency protection) | Medium | MVP |
| 11 | Plan SmartIR import path for v1.1 | Low | v1.1 |
| 12 | Consider sidebar name: "IR Devices" or "Remotes" instead of "IR Admin" | Medium | MVP |
| 13 | Add storage schema migration strategy | Medium | MVP |
| 14 | Plan Phase 0 → 1 → 2 release cadence | High | Planning |
| 15 | Re-evaluate integration name/branding | Low | Pre-launch |
| 16 | Add onboarding detection for existing IR hardware | Medium | MVP |

---

## Consensus Decisions

1. **Ship in phases**: Phase 0 (capture only) → Phase 1 (admin panel + remote entity) → Phase 2 (media_player + climate)
2. **Capture UX is king**: Streamlined dialog with auto-suggested commands, instant test, and capture loop
3. **Climate v1 is preset-based**: Honest about limitations, functional for real use
4. **CaptureProvider abstraction**: Required from day one, supports ESPHome + Broadlink initially
5. **Command templates**: Built-in suggested commands per device type, checklist-style UX
6. **Data model**: Add `source` and prepare for code database integration in v2
7. **Sidebar name**: "IR Devices" (friendlier than "IR Admin")

---

*Review complete. Proceeding to v2 iteration incorporating all action items.*
