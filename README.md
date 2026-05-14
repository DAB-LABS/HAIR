<p align="center">
  <img src="custom_components/hair/frontend/hair-header.png" alt="HAIR - Home Assistant Infrared Registry" width="600" />
</p>

# HAIR - Home Assistant Infrared Registry

A custom Home Assistant integration that provides a full admin interface for infrared device management. Built on HA's native `infrared` platform (2026.4+), HAIR handles capturing, organizing, and controlling IR commands through a single sidebar panel at `/hair`.

No YAML. No code. Works with any IR proxy hardware (ESPHome, Broadlink, etc.).

## Why HAIR?

Home Assistant 2026.4 introduced the `infrared` platform, giving HA its first native foundation for IR transmit and receive. This was a big step forward, but out of the box, there is no admin UI for managing IR devices. You get entities for your hardware (emitters and receivers), but no way to capture signals, organize them into devices, or map them to HA controls without writing YAML or automations by hand.

Before the infrared platform, IR in HA was fragmented. Broadlink had its own integration with a basic learn-and-send flow. ESPHome users had to manually define raw timing arrays in YAML. There was no shared signal format, no device abstraction, and no way to assign an IR command to a media_player volume button without custom template entities.

The infrared platform solves the transport layer. HAIR solves everything above it: the admin experience for capturing signals, fingerprinting and deduplicating them, organizing them into device profiles, and automatically creating the right HA entities with proper feature mappings. Think of it like how the Z-Wave JS UI manages Z-Wave devices, but for IR.

HAIR also introduces signal fingerprinting using Pronto hex pulse-duration analysis. Every captured IR signal is reduced to a short/long (S/L) pattern that identifies it regardless of the minor timing jitter between presses. This works across all major consumer IR protocols including NEC, Samsung, JVC, LG, Sony, and RC-5/RC-6. The Sniffer groups signals by source remote, deduplicates repeated button presses, filters out repeat frames, and tracks how often each signal appears, all without needing to decode the specific IR protocol.

As HA's IR ecosystem matures (receiver entities are expected in 2026.6-2026.7), HAIR will grow alongside it. The goal is to be the go-to admin tool for anyone with IR-controlled devices in their home.

## Features

**Signal Sniffer** - Passive IR listener that runs in the background. Every IR transmission your receivers detect is captured, fingerprinted, and grouped by source device. Signals are deduplicated automatically: press the same button ten times and you see one signal with a hit count of ten. Repeat frames (sent when you hold a button down) are filtered out so only actual command signals appear. The Sniffer shows you what remotes are active in your home and which buttons are being pressed, all in real time.

**Device Management** - Create profiles for your IR-controlled devices (TVs, ACs, fans, lights, switches, screens). Assign captured signals as named commands from a device-type-aware template list, or enter custom names. Each device gets native HA entities automatically based on its type.

**Action Mapping** - Explicitly bind IR commands to HA entity features through a popover UI. When you map a command to "Volume Up," the media_player entity knows to call that command when the HA volume service is used. Features are only exposed when commands are mapped, so your entities stay clean.

**Multi-Emitter TX** - Assign one or more IR emitters to each device. Commands broadcast to all assigned emitters simultaneously, so a single "TV Power" button can fire through emitters in multiple rooms.

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

Entity features are driven by explicit action mappings. A media_player only exposes volume control if you map commands to the volume actions. This keeps your entities clean and avoids exposing features your remote doesn't support.

## Using HAIR

### The Devices Tab

The main view shows four sections:

**HAIR Devices** - Your managed IR device profiles. Each card shows the device name, type, command count, and how many emitters are assigned. Click a device to expand its detail view inline, where you can change the device type, manage emitters, and see all learned commands with their S/L diamond fingerprint patterns. From here you can test commands, delete them, re-learn them, or assign action mappings.

**Emitters** - Your IR transmitter hardware (e.g., ESPHome infrared entities). These are the physical IR LEDs that send commands. Each emitter card shows its entity ID and a TX badge.

**Receivers** - Your IR receiver hardware. These feed captured signals into the Sniffer. Each receiver card shows its source integration and an RX badge.

**Proxies** - Hardware devices that have both TX and RX capabilities. A single ESPHome board with an IR LED and an IR receiver shows up here with both TX and RX badges.

### The Sniffer Tab

The Sniffer is a passive listener that shows every IR signal your receivers pick up. Signals are grouped by source device (identified by carrier frequency and preamble fingerprint) and displayed with hit counts, signal counts, and last-seen timestamps.

Each source device row can be expanded to show individual signals with their S/L diamond fingerprint. From here you can assign a signal directly to a HAIR device as a named command, or promote an unknown source device into a full HAIR device profile.

Devices already managed by HAIR are tagged with a "HAIR Device" badge. You can dismiss noisy sources (like a neighbor's remote leaking through a window) and bring them back later with the "Show Dismissed" toggle.

### Adding a Device

Click the floating "Add Device" button on the Devices tab. Enter a name, pick a device type, and select which IR emitters should broadcast commands for this device. HAIR creates the device profile and the corresponding HA entities immediately.

### Learning Commands

Navigate to the Sniffer tab and press buttons on your physical remote. HAIR captures each signal in real time. Expand the source device row, then click on a signal to assign it to one of your HAIR devices. Pick a command name from the device-type-aware template list (e.g., "Power On," "Volume Up," "Mode: Cool") or enter a custom name.

### Action Mapping

After learning commands, open a device's detail view and click the "ACTIONS" badge on any command row. A popover shows all available actions for that device type. Pick an action to bind it to that command. For example, mapping "Power On" to the `turn_on` action means the HA media_player's power button will fire that IR command. Actions already mapped to other commands are shown with their current assignment so you can reassign with a single click.

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

Captured IR signals are converted to Pronto hex and fingerprinted using pulse-duration analysis. Each timing word in the Pronto data is classified as short (S) or long (L) relative to a threshold. The resulting S/L pattern identifies the signal regardless of minor timing variations between presses. In the UI, these patterns are shown as two-tone diamond sequences for quick visual identification.

This works across the full range of consumer IR protocols, including NEC-family protocols (NEC, Samsung, JVC, LG) whose lead-in marks are much longer than normal data pulses. HAIR recognizes these lead-in signatures and classifies them correctly rather than treating them as end-of-signal gaps. NEC-style repeat frames (short transmissions sent while a button is held) are filtered automatically so the Sniffer only shows actual command signals.

Signals are grouped by source device using the carrier frequency and protocol-aware preamble analysis. For NEC-family signals, HAIR extracts the device address portion of the S/L pattern to distinguish between remotes. For other protocols, the first burst pair serves as the preamble fingerprint. This is how the Sniffer knows which remote a signal came from without needing to decode the specific IR protocol.

### Architecture

```
Remote Control
      |
  IR Receiver (ESPHome / Broadlink)
      |
  HA Event Bus (esphome.remote_received)
      |
  HAIR Signal Monitor --> Signal Store (fingerprint + dedup)
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
