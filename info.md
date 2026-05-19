# HAIR

A full admin interface for infrared device management in Home Assistant.

Built on HA's native `infrared` platform (2026.4+), HAIR handles capturing, organizing, and controlling IR commands through a single sidebar panel at `/hair`. No YAML required.

## What you get

- **Signal Sniffer** - Real-time IR signal monitor with fingerprinting, deduplication, and hit tracking
- **Device Management** - Create profiles for TVs, ACs, fans, lights, switches, screens, and more
- **Multi-Emitter TX** - Broadcast commands to multiple IR emitters simultaneously
- **Action Mapping** - Bind captured IR commands to HA entity features via dropdown selection
- **Auto Entities** - Devices get native HA entities (`media_player`, `climate`, `fan`, `light`, `switch`, `cover`, `remote`, `button`)
- **Command Templates** - Device-type-aware guided setup with predefined command names

## Requirements

- Home Assistant 2026.4+
- **For capture:** an ESPHome device with the `remote_receiver` component (legacy event-bus bridge until HA's native IR receive entities ship in 2026.6 or 2026.7)
- **For send:** any integration on HA's native infrared platform (Broadlink RM series, ESPHome infrared entities, etc.)
