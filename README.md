<p align="center">
  <img src="images/HAIR-readme-hero.png" alt="HAIR brand banner showing the HA Box mascot acting as barber to a row of IR devices" width="900" />
</p>

# HAIR

A custom Home Assistant integration that provides a full admin interface for infrared device management. Built on HA's native `infrared` platform (2026.4+), HAIR handles capturing, organizing, and controlling IR commands through a single sidebar panel at `/hair`.

No YAML. No code. Works with any IR proxy hardware (ESPHome, Broadlink, etc.).

## Why HAIR?

Home Assistant 2026.4 introduced the `infrared` platform, giving HA its first native foundation for IR transmit and receive. This was a big step forward, but out of the box, there is no admin UI for managing IR devices. You get entities for your hardware (emitters and receivers), but no way to capture signals, organize them into devices, or map them to HA controls without writing YAML or automations by hand.

Before the infrared platform, IR in HA was fragmented. Broadlink had its own integration with a basic learn-and-send flow. ESPHome users had to manually define raw timing arrays in YAML. There was no shared signal format, no device abstraction, and no way to assign an IR command to a media_player volume button without custom template entities.

The infrared platform solves the transport layer. HAIR solves everything above it: the admin experience for capturing signals, fingerprinting and deduplicating them, organizing them into device profiles, and automatically creating the right HA entities with proper feature mappings. Think of it like how the Z-Wave JS UI manages Z-Wave devices, but for IR.

HAIR also introduces signal fingerprinting using short/long (S/L) pulse-duration analysis. Every captured IR signal is reduced to an S/L pattern that identifies it regardless of timing jitter between presses. This works across all major consumer IR protocols including NEC, Samsung, JVC, LG, Sony, and RC-5/RC-6. The Sniffer groups signals by source remote, deduplicates repeated button presses, and tracks how often each signal appears, all in real time.

As HA's IR ecosystem matures (receiver entities are expected in 2026.6-2026.7), HAIR will grow alongside it. The goal is to be the go-to admin tool for anyone with IR-controlled devices in their home.

## Features

**Signal Sniffer** - Passive IR listener that runs in the background. Every IR transmission your receivers detect is captured, fingerprinted, and grouped by source device. Signals are deduplicated automatically: press the same button ten times and you see one signal with a hit count of ten. Repeat frames (sent when you hold a button down) are filtered out so only actual command signals appear. The Sniffer shows you what remotes are active in your home and which buttons are being pressed, all in real time.

**Device Management** - Create profiles for your IR-controlled devices (TVs, ACs, fans, lights, switches, screens). Assign captured signals as named commands from a device-type-aware template list, or enter custom names. Each device gets native HA entities automatically based on its type.

**Action Mapping** - Explicitly bind IR commands to HA entity features through a popover UI. When you map a command to "Volume Up," the media_player entity knows to call that command when the HA volume service is used. Features are only exposed when commands are mapped, so your entities stay clean.

**Triggers** - Turn any IR signal into a native HA event entity. Create a trigger from a learned device command or from an unknown signal in the Sniffer. Each trigger gets an `event` entity under a virtual "HAIR Triggers" device, firing an `ir_command_received` event whenever the matching signal is received. Use triggers to build HA automations that react to physical remote presses (e.g., pressing a TV power button also turns off the room lights). A configurable "min hits" threshold (minimum button presses) lets you require multiple presses within a 5-second window before the trigger fires, which is useful for preventing accidental activations. The Devices tab shows all active triggers with real-time fire animations.

**Emitter Routing & Broadcast Control** - Assign one or more IR emitters to each device with explicit control over how commands are broadcast. Lock a device to a single emitter for room-scoped control (an AC pinned to the bedroom emitter so commands never leak to the living room), or assign multiple emitters for a wide broadcast (a single "TV Power" command fires through emitters in every room simultaneously). Routing is configured per-device, so you can mix tight per-room targeting for some devices with whole-house broadcast for others.

**Command Templates** - Guided setup suggests which commands to capture based on device type. Select from predefined names (Power On, Volume Up, Mode: Cool, etc.) or enter custom names for anything not in the list.

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

## Screenshots

<p align="center">
  <img src="images/screenshots/devices-overview.png" alt="Devices overview showing HAIR Devices, Triggers, Emitters, Receivers, and Proxies" width="880" />
</p>

<p align="center">
  <img src="images/screenshots/device-detail.png" alt="Device detail with learned commands, S/L fingerprints, and trigger buttons" width="430" />
  <img src="images/screenshots/action-mapping.png" alt="Action mapping popover for binding commands to HA entity features" width="430" />
</p>

<p align="center">
  <img src="images/screenshots/sniffer-signals.png" alt="Sniffer showing captured signals with S/L diamond fingerprints, trigger buttons, and hit counts" width="880" />
</p>

<p align="center">
  <img src="images/screenshots/assign-dialog.png" alt="Assign dialog for mapping a captured signal to a device command" width="280" />
  <img src="images/screenshots/trigger-dialog.png" alt="Create Trigger dialog with S/L diamond pattern and min hits setting" width="280" />
  <img src="images/screenshots/promote-dialog.png" alt="Promote dialog for creating a new HAIR device from an unknown remote" width="280" />
</p>

## Using HAIR

### The Devices Tab

The main view shows five sections:

**HAIR Devices** - Your managed IR device profiles. Each card shows the device name, type, command count, and how many emitters are assigned. Click a device to expand its detail view inline, where you can change the device type, manage emitters, and see all learned commands with their S/L diamond fingerprint patterns. From here you can test commands, delete them, or assign action mappings.

**Triggers** - Active IR triggers that fire HA event entities when their signal is detected. Each trigger card shows the trigger name with a lightning bolt icon. When a trigger fires, the card flashes with an amber glow animation in real time.

**Emitters** - Your IR transmitter hardware (e.g., ESPHome infrared entities). These are the physical IR LEDs that send commands. Each emitter card shows its entity ID and a TX badge.

**Receivers** - Your IR receiver hardware. These feed captured signals into the Sniffer. Each receiver card shows its source integration and an RX badge.

**Proxies** - Hardware devices that have both TX and RX capabilities. A single ESPHome board with an IR LED and an IR receiver shows up here with both TX and RX badges.

### The Sniffer Tab

The Sniffer is a passive listener that shows every IR signal your receivers pick up. Signals are grouped by source device (identified by carrier frequency and preamble fingerprint) and displayed with hit counts, signal counts, and last-seen timestamps.

Each source device row can be expanded to show individual signals with their S/L diamond fingerprint. From here you can assign a signal directly to a HAIR device as a named command, or promote an unknown source device into a full HAIR device profile. Before promoting, click the pencil button on the source device row to give it a custom name — otherwise the new device inherits the auto-generated source name (e.g., "Unknown Remote 1"). Setting the name first means the promoted device lands in your Devices tab already labeled correctly.

Devices already managed by HAIR are tagged with a "HAIR Device" badge. You can dismiss noisy sources (like a neighbor's remote leaking through a window) and bring them back later with the "Show Dismissed" toggle.

### Adding a Device

There are two ways to add a device.

**From scratch:** Click the floating "Add Device" button on the Devices tab. Enter a name, pick a device type, and select which IR emitters should broadcast commands for this device. HAIR creates the device profile and the corresponding HA entities immediately.

**From the Sniffer (promote an unknown source):** When HAIR detects a remote it doesn't recognize, it appears in the Sniffer as an unknown source device. Click the pencil button on the source row to give it a custom name first, then promote it to a full HAIR device. Setting the name before promoting means your new device shows up in the Devices tab already labeled the way you want it, instead of carrying the auto-generated "Unknown Remote N" name forward. This path is ideal when you have the physical remote in hand and want to capture its signals first.

### Learning Commands

Navigate to the Sniffer tab and press buttons on your physical remote. HAIR captures each signal in real time. Expand the source device row, then click on a signal to assign it to one of your HAIR devices. Pick a command name from the device-type-aware template list (e.g., "Power On," "Volume Up," "Mode: Cool") or enter a custom name.

### Action Mapping

After learning commands, open a device's detail view and click the "ACTIONS" badge on any command row. A popover shows all available actions for that device type. Pick an action to bind it to that command. For example, mapping "Power On" to the `turn_on` action means the HA media_player's power button will fire that IR command. Actions already mapped to other commands are shown with their current assignment so you can reassign with a single click.

### Triggers

Triggers let you use incoming IR signals as automation triggers in Home Assistant. There are two ways to create a trigger.

From a device command: expand a device in the Devices tab and click the trigger button on any command row. This creates a trigger linked to that command's signal. If a trigger already exists for that command, the button opens the trigger in edit mode instead.

From the Sniffer: expand an unknown device and click the trigger button on any signal row. This creates a trigger from the raw signal fingerprint, which is useful for signals you want to react to without assigning them to a HAIR device.

Each trigger has a configurable "min hits" value (minimum button presses, 1 to 10) that controls how many times the signal must be received within a 5-second window before the trigger fires. Setting this to 2 or 3 is useful for preventing triggers from firing on stray or accidental presses.

Active triggers appear in the Triggers section at the bottom of the Devices tab. When a trigger fires, its card flashes with an amber glow animation. Each trigger creates an `event` entity (e.g., `event.hair_triggers_tv_power`) that you can use directly in HA's automation editor as a trigger condition.

## Requirements

- Home Assistant **2026.4** or later
- Python 3.12+
- At least one IR transmitter or receiver (ESPHome, Broadlink, or compatible hardware)

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

## How It Works

HAIR sits between you and HA's IR platform. It does not replace your IR hardware integrations (Broadlink, ESPHome, etc.). It complements them by providing the admin layer those integrations lack.

### Capture Providers

HAIR discovers capture-capable hardware automatically:

- **ESPHome** - Devices with `remote_receiver` component
- **Broadlink** - RM series devices

### Signal Fingerprinting

Captured IR signals are fingerprinted using S/L (short/long) pulse-duration classification. Each pulse in the signal is classified as short or long, producing a pattern that uniquely identifies the signal regardless of minor timing jitter between presses. In the UI, these patterns are shown as two-tone diamond sequences for quick visual identification.

S/L fingerprinting covers all major consumer IR protocols including NEC, Samsung, JVC, LG, Sony, and RC-5/RC-6. Repeat frames (sent while a button is held) are filtered automatically. Signals are grouped by source device using carrier frequency and preamble analysis, so the Sniffer knows which remote a signal came from without needing to decode the specific protocol.

### Architecture

```
Remote Control
      |
  IR Receiver (ESPHome / Broadlink)
      |
  HA Event Bus (esphome.remote_received)
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
  IR Emitter (infrared.send_command) --> Hardware TX
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT. See [LICENSE](LICENSE) for details.
