<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="HAIR Full Service barbershop banner with the TX mascot welcoming the new RX mascot at the shop entrance, RX IS HERE speech bubble overhead" width="900" />
</p>

# HAIR

IR control in Home Assistant used to mean picking your manufacturer's integration, hoping its code database had your device model, and either trusting a JSON file from a forum or hand-rolling template entities. The captured signals lived on the blaster. The user lived in YAML. The codes were ***trapped where they were learned***: a Broadlink app's cloud, a vendor hub, a config file on disk.

***HAIR moves IR into Home Assistant itself.*** Point any remote at an ESPHome IR receiver, press a button, and HAIR turns that signal into a native HA entity. A button you can fire from any dashboard. An event that ***triggers automations***. A command broadcast through any blaster on HA's native `infrared` platform, whether that is an ESPHome IR LED, a [Tuya Local](https://github.com/make-all/tuya-local) IR blaster, a Broadlink RM, an SMLIGHT SLZB, or anything else that adopts the platform.

No manufacturer picker. No model lookup. No code file downloads. No YAML. Just point, press, use.

## Platform state

Home Assistant's native `infrared` platform shipped transmit (TX) support in HA 2026.4 and receive (RX) support via `InfraredReceiverEntity` in HA 2026.6.

### Infrared platform compatibility

HAIR works with any integration that exposes HA's native `infrared` entity platform. These integrations have adopted it:

| Integration | Source | TX | RX | Status |
|---|---|---|---|---|
| [ESPHome](https://esphome.io/) | Core | Yes | Yes | Since 2026.4 (TX), 2026.6 (native RX) |
| [Tuya Local](https://github.com/make-all/tuya-local) | HACS | Yes | No | Since 2026.4 |
| [Broadlink](https://www.home-assistant.io/integrations/broadlink/) | Core | Yes | No | Since 2026.5 |
| [SMLIGHT](https://www.home-assistant.io/integrations/smlight/) | Core | Yes | No | Since 2026.5 |

On HA 2026.6+, HAIR subscribes to native `InfraredReceiverEntity` instances via `infrared.async_subscribe_receiver()`. Any integration that implements the receiver entity works as a HAIR receiver automatically. On HA 2026.4-2026.5, HAIR falls back to the legacy ESPHome event bus bridge (see [ESPHome Receiver Setup](#esphome-receiver-setup) below).

As more integrations adopt the `infrared` platform, HAIR picks them up with no changes needed on HAIR's side.

HAIR fingerprints every captured signal using short/long (S/L) pulse-duration analysis. Each pulse is classified short or long, producing a pattern that identifies the signal regardless of minor timing jitter between presses. S/L works across NEC, Samsung, JVC, LG, Sony, and RC-5/RC-6 without needing to decode the protocol. The Sniffer groups signals by source remote, deduplicates repeated presses, filters held-button repeat frames, and tracks hit counts, all in real time.

## Screenshots

| Devices Overview | Device Detail |
|:---:|:---:|
| ![Devices overview showing HAIR Devices, Triggers, Emitters, Receivers, and Proxies](images/screenshots/devices-overview.png) | ![Device detail with learned commands, S/L fingerprints, and trigger buttons](images/screenshots/device-detail.png) |

| Action Mapping | Sniffer |
|:---:|:---:|
| ![Action mapping popover for binding commands to HA entity features](images/screenshots/action-mapping.png) | ![Sniffer showing captured signals with S/L diamond fingerprints, trigger buttons, and hit counts](images/screenshots/sniffer-signals.png) |

| Assign Signal | Create Trigger | Promote Device |
|:---:|:---:|:---:|
| ![Assign dialog for mapping a captured signal to a device command](images/screenshots/assign-dialog.png) | ![Create Trigger dialog with S/L diamond pattern and min hits setting](images/screenshots/trigger-dialog.png) | ![Promote dialog for creating a new HAIR device from an unknown remote](images/screenshots/promote-dialog.png) |

## Requirements

- Home Assistant **2026.4** or later
- Python 3.12+
- **For capture (RX):** any integration that exposes HA's native `InfraredReceiverEntity` (HA 2026.6+) -- ESPHome IR receivers work day-one, and any other integration that adopts the receiver entity works automatically. On HA 2026.4-2026.5, HAIR falls back to the legacy ESPHome event-bus bridge (see [ESPHome Receiver Setup](#esphome-receiver-setup) for the YAML stub).
- **For send (TX):** at least one integration on HA's native infrared platform (ESPHome infrared entities, [Tuya Local](https://github.com/make-all/tuya-local) IR blasters, Broadlink RM series, SMLIGHT SLZB devices, etc.)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations**
3. Click the three-dot menu > **Custom repositories**
4. Add `https://github.com/DAB-LABS/HAIR` with category **Integration**
5. Search for "HAIR" and install
6. Restart Home Assistant

### Manual

1. Copy `custom_components/hair` into your HA `custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings > Devices & Services**
2. Click **Add Integration** and search for "HAIR"
3. The config flow auto-detects your IR hardware (emitters and receivers)
4. Once added, find **HAIR** in the sidebar

### ESPHome Receiver Setup

This setup is only needed if you are on HA 2026.4 or 2026.5 (before native `InfraredReceiverEntity` shipped), or if you are on 2026.6+ but have not yet migrated your ESPHome YAML to register the receiver entity on the `infrared` platform. In both cases, HAIR uses the legacy event-bus bridge below to receive signals from your ESPHome IR receiver.

If you are on HA 2026.6+ and your ESPHome YAML registers the receiver via the `infrared` platform, HAIR subscribes to it directly through `infrared.async_subscribe_receiver()` and this bridge is not needed. The Devices tab will show a `RX-NATIVE` badge on the receiver card when that path is active, or `RX-BRIDGE` when this legacy bridge is in use.

Add this to your ESPHome device's `remote_receiver` block to wire up the bridge:

```yaml
remote_receiver:
  id: ir_receiver
  pin:
    number: GPIO5   # your IR receiver data pin
    inverted: true
  dump: pronto
  on_pronto:
    then:
      - homeassistant.event:
          event: esphome.remote_received
          data:
            protocol: "PRONTO"
            code: !lambda 'return x.data;'
```

The `on_pronto` trigger catches every IR signal regardless of protocol (NEC, Samsung, Sony, RC-5, etc.) and fires it as a `homeassistant.event` on the HA bus. HAIR's Signal Monitor subscribes to these events automatically.

When you are ready to migrate to the native receiver path on HA 2026.6+, add the `infrared` platform receiver entry to your ESPHome YAML (canonical examples in [`esphome/`](esphome/)) and reflash. HAIR will detect the native receiver and switch over automatically. You can keep the legacy `on_pronto` bridge in place during the transition: HAIR will not double-process signals, and the panel will show both `RX-NATIVE` and `RX-BRIDGE` badges until you remove the bridge from your YAML.

For ready-made, HAIR-tested configurations for common ESP32 boards and IR devices (XIAO Smart IR Mate, Athom RF IR Remote, generic ESP32s), see [`esphome/`](esphome/) in this repo. Each device has two tiers: minimal (just the IR pieces) and full (preserves device-specific features like touch pads and status LEDs).

## Features

**Native Receiver Support (HA 2026.6+)** - HAIR subscribes to native `InfraredReceiverEntity` instances via `infrared.async_subscribe_receiver()`. Hardware-agnostic. Any integration that adopts the receiver entity works automatically. On HA 2026.4-2026.5, HAIR falls back to the legacy ESPHome event-bus bridge with no change required from you.

**Signal Sniffer** - Passive IR listener that runs in the background. Every IR transmission your receivers detect is captured, fingerprinted, and grouped by source device. Signals are deduplicated automatically: press the same button ten times and you see one signal with a hit count of ten. Repeat frames (sent when you hold a button down) are filtered out so only actual command signals appear. The Sniffer shows you what remotes are active in your home and which buttons are being pressed, all in real time. Use the Test button on any captured signal to fire it through an emitter picker before assigning it to a device, useful for spot-checking that the signal you captured actually controls the device you think it does.

**HAIR Clips** - Build virtual remotes by pasting Pronto hex codes, for when you have a code from an online converter, a vendor datasheet, or an ESPHome log but no live signal to sniff. Create a named remote on the Clips tab, then add a button by pasting its Pronto code. The dialog validates the code as you paste it (the detected carrier frequency, the burst pair count, an S/L diamond preview, and specific error messages when something is off) so you know it is well-formed before you save. A pasted signal behaves exactly like a sniffed one: test it through an emitter, turn it into a trigger, assign it to a device, or promote the whole remote.

**Signal Aliases** - Give any signal a nickname by clicking its S/L diamond pattern and typing. The alias replaces the diamonds in the list so you can tell your signals apart at a glance, in both the Sniffer and Clips. An alias is a label on the signal, not a command name, so the same signal can still become differently-named commands on different devices.

**Device Management** - Create profiles for your IR-controlled devices (TVs, ACs, fans, lights, switches, screens). Assign captured signals as named commands from a device-type-aware template list, or enter custom names. Assigning a signal copies it into the device and leaves the original in place, so the same signal can be assigned to more than one device or as more than one command. Each device gets native HA entities automatically based on its type. One-click duplicate clones an existing device with all its commands, action mappings, and emitter assignments preserved, useful when you have several remotes of the same model or a stack of similar AC units.

**Drag-to-Reorder** - Reorder the commands inside a device by dragging them. The new order persists across reloads and is reflected in the dashboard button entities. Helpful for putting power and mode commands at the top of the list where you actually use them.

**Action Mapping** - Explicitly bind IR commands to HA entity features through a popover UI. When you map a command to "Volume Up," the media_player entity knows to call that command when the HA volume service is used. Features are only exposed when commands are mapped, so your entities stay clean.

**Triggers** - Turn any IR signal into a native HA event entity. Create a trigger from a learned device command or from an unknown signal in the Sniffer. Each trigger gets an `event` entity under a virtual "HAIR Triggers" device, firing an `ir_command_received` event whenever the matching signal is received. Use triggers to build HA automations that react to physical remote presses (e.g., pressing a TV power button also turns off the room lights). A configurable "min hits" threshold (minimum button presses) lets you require multiple presses within a 5-second window before the trigger fires, which is useful for preventing accidental activations. The Devices tab shows all active triggers with real-time fire animations.

**Emitter Routing & Broadcast Control** - Assign one or more IR emitters to each device with explicit control over how commands are broadcast. Lock a device to a single emitter for room-scoped control (an AC pinned to the bedroom emitter so commands never leak to the living room), or assign multiple emitters for a wide broadcast (a single "TV Power" command fires through emitters in every room simultaneously). Routing is configured per-device, so you can mix tight per-room targeting for some devices with whole-house broadcast for others.

**Command Templates** - Guided setup suggests which commands to capture based on device type. Select from predefined names (Power On, Volume Up, Mode: Cool, etc.) or enter custom names for anything not in the list.

**Migration Visibility** - `RX-NATIVE` and `RX-BRIDGE` badges on receiver and proxy cards show at a glance which receive path each piece of hardware is using. If you have multiple ESPHome devices and you have migrated some YAML but not others, the badges make the partial-migration state obvious so you know which devices still need attention.

**Mobile Navigation** - The HAIR panel includes a navigation button on phone and tablet viewports so you can return to the HA sidebar without relying on the edge-swipe gesture. Hidden on desktop.

## Using HAIR

### The Devices Tab

The main view shows five sections:

**HAIR Devices** - Your managed IR device profiles. Each card shows the device name, type, command count, and how many emitters are assigned. Each card also carries two small corner actions: a duplicate icon in the top-right to clone the device with all its commands and emitter assignments preserved, and a delete icon in the bottom-right for removing the device without opening its detail view. Click anywhere else on the card to expand its detail view inline, where you can change the device type, manage emitters, drag-to-reorder commands, and see every learned command with its S/L diamond fingerprint pattern. From the detail view you can test commands, delete them, or assign action mappings.

**Triggers** - Active IR triggers that fire HA event entities when their signal is detected. Each trigger card shows the trigger name with a lightning bolt icon. When a trigger fires, the card flashes with an amber glow animation in real time.

**Emitters** - Your IR transmitter hardware (e.g., ESPHome infrared entities, Tuya Local IR blasters, Broadlink RM series, SMLIGHT SLZB devices). These are the physical IR LEDs that send commands. Each emitter card shows its entity ID and a TX badge, plus a `TX-NATIVE` badge once the device exposes the transmitter on HA's native infrared platform.

**Receivers** - Your IR receiver hardware. These feed captured signals into the Sniffer. Each receiver card shows its source integration, its entity ID, and one of two RX badges. `RX-NATIVE` means the device is exposing the receiver via HA's native `InfraredReceiverEntity` (HA 2026.6+) and HAIR is subscribing through the official API. `RX-BRIDGE` means HAIR is consuming `esphome.remote_received` events from the legacy event-bus bridge. Both work; the badge tells you which path is active. Devices on the bridge path that also have a native receiver registered will show both badges side by side during the migration window.

**Proxies** - Hardware devices that have both TX and RX capabilities. A single ESPHome board with an IR LED and an IR receiver shows up here with TX and RX badges plus their NATIVE / BRIDGE state, so you can see the full migration picture for that device in one card.

### The Sniffer Tab

The Sniffer is a passive listener that shows every IR signal your receivers pick up. Signals are grouped by source device (identified by carrier frequency and preamble fingerprint) and displayed with hit counts, signal counts, and last-seen timestamps.

Each source device row can be expanded to show individual signals with their S/L diamond fingerprint. From here you can assign a signal directly to a HAIR device as a named command, or promote an unknown source device into a full HAIR device profile. Before promoting, click the pencil button on the source device row to give it a custom name -- otherwise the new device inherits the auto-generated source name (e.g., "Unknown Remote 1"). Setting the name first means the promoted device lands in your Devices tab already labeled correctly.

The Test button on any captured signal opens an emitter picker so you can choose which IR emitter to fire the test signal through, and broadcast through multiple emitters at once if you want. The picker remembers your selection for the session so subsequent Tests skip straight to Send.

Devices already managed by HAIR are tagged with a "HAIR Device" badge. You can dismiss noisy sources (like a neighbor's remote leaking through a window) and bring them back later with the "Show Dismissed" toggle (hover tooltip: "Restore previously hidden remotes"). When dismissed remotes are still firing in the background, the button quietly glows blue and shows a small dot indicator, so you can tell at a glance that there is still activity arriving from remotes you have hidden, without re-exposing those signals in the live feed. Clicking the button clears the dot and reveals the dismissed remotes so you can restore the ones you actually want back.

You can give any signal an alias by clicking its diamond pattern and typing a name. The alias replaces the diamonds in the row, which makes it easy to tell signals apart before you assign them. Assigning a signal no longer removes it from the Sniffer either. The signal is copied into the device and stays in the list, so you can assign the same signal to several devices, or as several commands, and reuse it later. Only Delete, Dismiss, and Clear All take a signal out of the Sniffer.

### The Clips Tab

The Clips tab is for building remotes by hand, for when you cannot or do not want to sniff them live. Instead of pointing a remote at a receiver, you paste a Pronto hex code for each button.

Click "+ Create" to make a named remote, then expand it and click "+ Create" again to add a signal. Paste the Pronto code into the dialog. As you paste, HAIR validates the code and shows a green or red check, the detected carrier frequency, the burst pair count, and the same S/L diamond fingerprint you see in the Sniffer, along with a specific message if anything is wrong (a header that is not `0000`, a truncated code, non-hex characters, or an unusual carrier frequency). Press Enter or click Create once it validates, and give it an alias up front if you like.

From there a clipped signal is identical to a sniffed one. Test it through an emitter, create a trigger from it, assign it to an existing HAIR device, or promote the whole remote into a new device. Clipped remotes are never aged out automatically, so anything you build here stays until you delete it.

Pronto is the only paste format for now. Raw timings, Broadlink base64, and protocol-plus-command entry are not supported. A device database picker that pre-fills commands is planned for a future release and will live alongside the paste field on this same tab.

### Adding a Device

There are three ways to add a device.

**From scratch:** Click the "Add Device" button in the tab bar on the Devices tab. Enter a name, pick a device type, and select which IR emitters should broadcast commands for this device. HAIR creates the device profile and the corresponding HA entities immediately.

**From the Sniffer (promote an unknown source):** When HAIR detects a remote it doesn't recognize, it appears in the Sniffer as an unknown source device. Click the pencil button on the source row to give it a custom name first, then promote it to a full HAIR device. Setting the name before promoting means your new device shows up in the Devices tab already labeled the way you want it, instead of carrying the auto-generated "Unknown Remote N" name forward. This path is ideal when you have the physical remote in hand and want to capture its signals first.

**From an existing device (duplicate):** Click the duplicate icon in the top-right corner of any device card. HAIR opens a dialog pre-filled with `<original name> (Copy)` so you can rename the clone before it lands. All of the original device's commands, action mappings, and emitter assignments are copied across; triggers stay attached to the original. This path is ideal when you have several remotes of the same model (a stack of similar AC units, two identical TVs in different rooms) or when you want a sandbox copy to experiment with action mappings without breaking the working device.

### Learning Commands

Navigate to the Sniffer tab and press buttons on your physical remote. HAIR captures each signal in real time. Expand the source device row, then click on a signal to assign it to one of your HAIR devices. Pick a command name from the device-type-aware template list (e.g., "Power On," "Volume Up," "Mode: Cool") or enter a custom name.

You can also start from a device. A device's detail view has two add-command buttons, "+ Sniffed Signal" and "+ Clipped Signal", which take you to the Sniffer or the Clips tab so you can capture or paste the signal and assign it back to the device.

### Action Mapping

After learning commands, open a device's detail view and click the "ACTIONS" badge on any command row. A popover shows all available actions for that device type. Pick an action to bind it to that command. For example, mapping "Power On" to the `turn_on` action means the HA media_player's power button will fire that IR command. Actions already mapped to other commands are shown with their current assignment so you can reassign with a single click.

### Triggers

Triggers let you use incoming IR signals as automation triggers in Home Assistant. There are two ways to create a trigger.

From a device command: expand a device in the Devices tab and click the trigger button on any command row. This creates a trigger linked to that command's signal. If a trigger already exists for that command, the button opens the trigger in edit mode instead.

From the Sniffer: expand an unknown device and click the trigger button on any signal row. This creates a trigger from the raw signal fingerprint, which is useful for signals you want to react to without assigning them to a HAIR device.

Each trigger has a configurable "min hits" value (minimum button presses, 1 to 10) that controls how many times the signal must be received within a 5-second window before the trigger fires. Setting this to 2 or 3 is useful for preventing triggers from firing on stray or accidental presses.

Active triggers appear in the Triggers section at the bottom of the Devices tab. When a trigger fires, its card flashes with an amber glow animation. Each trigger creates an `event` entity (e.g., `event.hair_triggers_tv_power`) that you can use directly in HA's automation editor as a trigger condition.

## Entity Platforms

Devices automatically get native HA entities based on their type:

| Type | HA Entity | Controls |
|------|-----------|----------|
| Media Player | `media_player` | Power, volume, mute, source, channels, navigation, transport |
| AC | `climate` | HVAC modes, temperature presets, fan modes |
| Fan | `fan` | Power, speed stepping, oscillate |
| Light | `light` | On/off, brightness stepping |
| Switch | `switch` | On/off |
| Screen | `cover` | Open, close, stop |
| Other | `remote` | Generic IR command sender |

Every device also gets a `remote` entity for sending arbitrary Pronto hex codes and a `button` entity for each learned command. The button entities give you one-tap access to any IR command from dashboards, automations, or scripts, regardless of device type.

Triggers create `event` entities under a shared "HAIR Triggers" device. Each trigger entity fires an `ir_command_received` event when its signal is detected, making it available as an automation trigger in HA's automation editor.

Entity features are driven by explicit action mappings. A media_player only exposes volume control if you map commands to the volume actions. This keeps your entities clean and avoids exposing features your remote doesn't support.

## How It Works

HAIR sits between you and HA's IR platform. It does not replace your IR hardware integrations (ESPHome, Tuya Local, Broadlink, etc.). It complements them by providing the admin layer those integrations lack.

### Capture (RX)

HAIR uses a dual-path receive architecture. On HA 2026.6 and later, HAIR subscribes to native `InfraredReceiverEntity` instances via `infrared.async_subscribe_receiver()`. This is hardware-agnostic: any integration that exposes a receiver entity on the `infrared` platform works automatically, no per-vendor code in HAIR. On HA 2026.4-2026.5, HAIR falls back to the legacy ESPHome event-bus bridge (see [ESPHome Receiver Setup](#esphome-receiver-setup) above for the YAML stub). Both paths feed the same signal-processing pipeline so fingerprinting, deduplication, and trigger matching behave identically regardless of which path is active. The Devices tab surfaces which path each receiver is using via `RX-NATIVE` and `RX-BRIDGE` badges.

### Transmit (TX)

HAIR transmits IR signals via any integration that exposes HA's native `infrared` platform. Currently ESPHome, [Tuya Local](https://github.com/make-all/tuya-local), Broadlink, SMLIGHT, and other integrations that adopted the platform.

### Signal Fingerprinting

Captured IR signals are fingerprinted using S/L (short/long) pulse-duration classification. Each pulse in the signal is classified as short or long, producing a pattern that uniquely identifies the signal regardless of minor timing jitter between presses. In the UI, these patterns are shown as two-tone diamond sequences for quick visual identification.

S/L fingerprinting covers all major consumer IR protocols including NEC, Samsung, JVC, LG, Sony, and RC-5/RC-6. Repeat frames (sent while a button is held) are filtered automatically. Signals are grouped by source device using carrier frequency and preamble analysis, so the Sniffer knows which remote a signal came from without needing to decode the specific protocol.

### Architecture

```
Remote Control
      |
  IR Receiver Hardware
      |
  +--------------------------+---------------------------+
  | Native (HA 2026.6+)      | Legacy (HA 2026.4-2026.5) |
  | InfraredReceiverEntity   | ESPHome remote_receiver   |
  | async_subscribe_receiver | esphome.remote_received   |
  +--------------------------+---------------------------+
      |
  HAIR Signal Monitor --> Signal Store (fingerprint + dedup)
      |                         |
      |                   Trigger Manager --> Event Entities (HA automations)
      |
  HAIR Admin Panel (Sniffer view)
      |
  Assign to Device --> Device Manager --> Entity Factory
      |
  HA Entities (media_player, climate, fan, light, switch, cover, remote, button)
      |
  HA infrared Platform (infrared.send_command) <-- TX path: any platform integration
      |
  IR Emitter Hardware (ESPHome, Tuya Local, Broadlink, SMLIGHT, etc.)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT. See [LICENSE](LICENSE) for details.
