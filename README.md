<p align="center">
  <img src="custom_components/hair/frontend/hair-header.png" alt="HAIR - Home Assistant IR" width="600" />
</p>

# HAIR - Home Assistant IR

A custom Home Assistant integration that provides a full admin interface for infrared device management. Built on HA's native `infrared` platform (2026.4+), HAIR handles capturing, organizing, and controlling IR commands through a single sidebar panel at `/hair`.

No YAML. No code. Works with any IR proxy hardware (ESPHome, Broadlink, etc.).

## Features

**Signal Sniffer** - Real-time IR signal monitor that captures and fingerprints every IR transmission your receivers pick up. Signals are grouped by source device, deduplicated, and tracked with hit counts and timing.

**Device Management** - Create profiles for your IR-controlled devices (TVs, ACs, soundbars, projectors, fans). Assign captured signals as named commands. Each device gets HA entities automatically.

**Multi-Emitter TX** - Assign one or more IR emitters to each device. Commands broadcast to all assigned emitters simultaneously, so a single "TV Power" button can fire through emitters in multiple rooms.

**Command Templates** - Guided setup suggests which commands to capture based on device type, so you don't have to guess naming conventions.

**Entity Platforms** - Devices automatically get native HA entities based on their type:

| Type | HA Entity | Controls |
|------|-----------|----------|
| Media Player | `media_player` | Power, volume, mute, source, channels, navigation, transport |
| AC | `climate` | HVAC modes, temperature presets, fan modes |
| Fan | `fan` | Power, speed stepping, oscillate |
| Light | `light` | On/off, brightness stepping |
| Switch | `switch` | On/off |
| Screen | `cover` | Open, close, stop |
| Other | `remote` | Generic IR command sender |

All devices also get `button` entities (one per learned command) and a `remote` entity as a fallback for sending arbitrary Pronto hex codes. Entity features are driven by explicit action mappings, so a media_player only exposes volume control if you map commands to the volume actions.

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

HAIR sits between you and HA's IR platform. It does not replace your IR hardware integrations. It complements them by providing the admin experience those integrations lack.

### Capture Providers

HAIR discovers capture-capable hardware automatically:

- **ESPHome** - Devices with `remote_receiver` component
- **Broadlink** - RM series devices

### Signal Fingerprinting

Captured IR signals are converted to Pronto hex and fingerprinted using pulse-duration analysis. This produces a short/long (S/L) pattern that identifies the signal regardless of minor timing variations between presses.

### Architecture

```
Remote Control
      |
  IR Receiver (ESPHome / Broadlink)
      |
  HA Event Bus (ir_command_captured)
      |
  HAIR Signal Monitor --> Signal Store (fingerprint + dedup)
      |
  HAIR Admin Panel (Sniffer view)
      |
  Assign to Device --> Device Manager --> Entity Factory
      |
  HA Entities (media_player, climate, fan, remote, button)
      |
  IR Emitter (infrared.send_command) --> Hardware TX
```

## Configuration

After installation, HAIR has two configurable options (Settings > Devices & Services > HAIR > Configure):

- **Capture timeout** - How long to wait for an IR signal during capture (5-60 seconds, default 15)
- **Default repeat count** - Number of times to repeat each IR transmission (1-10, default 3)

## Development

```bash
# Clone the repo
git clone https://github.com/DAB-LABS/HAIR.git
cd HAIR

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -e ".[test,lint]"

# Run tests
pytest

# Lint
ruff check .
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT. See [LICENSE](LICENSE) for details.
