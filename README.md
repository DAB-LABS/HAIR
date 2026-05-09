# HAIR - Home Assistant IR Device Manager

A custom Home Assistant integration that provides a unified admin interface for infrared (IR) device management. Built on HA's native infrared platform (2026.4+), HAIR acts as the management layer for capturing, organizing, and controlling IR commands through a polished UI.

No YAML required. Works with any IR proxy (ESPHome, Broadlink, etc.).

## Requirements

- Home Assistant 2026.4 or later
- Python 3.12+
- At least one IR transmitter/receiver (ESPHome, Broadlink, or compatible hardware)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to Integrations
3. Click the three-dot menu and select "Custom repositories"
4. Add `https://github.com/DAB-LABS/HAIR` as an Integration
5. Search for "HAIR" and install
6. Restart Home Assistant

### Manual

1. Copy `custom_components/hair` into your HA `custom_components` directory
2. Restart Home Assistant

## Setup

1. Go to Settings > Devices & Services
2. Click "Add Integration" and search for "HAIR"
3. The config flow auto-detects your IR hardware
4. Once added, find "IR Devices" in the sidebar

## What It Does

HAIR sits between you and HA's IR platform. It does not replace your IR hardware integrations (Broadlink, ESPHome, etc.). It complements them by providing the admin experience those integrations lack.

**Device management** - Create profiles for your IR-controlled devices (TVs, ACs, soundbars, projectors, fans). Each device gets its own set of learned IR commands.

**Command capture** - Point-and-shoot IR learning with real-time feedback. Aim your remote at the receiver and press a button. HAIR captures the signal and saves it.

**Entity creation** - Devices automatically get HA entities. A TV becomes a media_player with volume, power, and source control. An AC becomes a climate entity with preset-based temperature control.

**Command templates** - Guided setup suggests which commands to capture based on device type, so you do not have to guess what to name things.

## Supported Device Types

| Type | HA Entity | Features |
|------|-----------|----------|
| TV | media_player | Power, volume, mute, source select |
| AC | climate | HVAC modes, temperature presets, fan modes |
| Soundbar | media_player | Power, volume, mute |
| Projector | media_player | Power, volume, source select |
| Fan | fan | Power, speed stepping, oscillate |
| Other | remote | Generic IR command sender |

All devices also get a `remote` entity as a fallback for sending arbitrary commands.

## Capture Providers

HAIR discovers capture-capable hardware automatically:

- **ESPHome** - Devices with `remote_receiver` component
- **Broadlink** - RM series devices

## Development

```bash
# Install dev dependencies
pip install -e ".[test,lint]"

# Run tests
pytest

# Lint
ruff check .
```

## License

MIT. See [LICENSE](LICENSE) for details.
