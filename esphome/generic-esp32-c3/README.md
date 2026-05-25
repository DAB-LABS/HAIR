# Generic ESP32-C3 Dev Kit

A minimal IR TX + RX configuration for the Espressif ESP32-C3-DevKitM-1 (or compatible ESP32-C3 boards). This is a DIY path -- you wire your own IR LED and IR receiver module to the board.

## Hardware

Any ESP32-C3 development board should work. The config targets the `esp32-c3-devkitm-1` board definition.

Typical sources: Espressif's official store, AliExpress, Amazon. Search "ESP32-C3 dev board".

You will also need an IR LED (with a transistor driver for better range) and a 38kHz IR receiver module (e.g., TSOP38238, VS1838B).

## GPIO Map

| GPIO | Function | Notes |
|---|---|---|
| GPIO9 | IR TX | Connect to IR LED (via transistor recommended) |
| GPIO8 | IR RX | Connect to IR receiver module data pin (inverted, pull-up) |

## Flashing

1. Copy `generic-esp32-c3-minimal.yaml` to your ESPHome config directory
2. Update the `substitutions` block with your preferred device name
3. Add required entries to your `secrets.yaml` (see below)
4. Flash via the ESPHome Dashboard or CLI

## Required secrets.yaml entries

```yaml
api_encryption_key: "<your-api-encryption-key>"
ota_password: "<your-ota-password>"
wifi_ssid: "<your-wifi-ssid>"
wifi_password: "<your-wifi-password>"
ap_password: "<your-fallback-ap-password>"
```

Generate an API encryption key with: `python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`

## Compatibility

| Component | Version |
|---|---|
| HAIR | 0.1.2 |
| HA Core | 2026.5.2 |
| ESPHome | 2026.4.5 |

## Variants

Only the minimal variant is provided. It includes IR TX, IR RX with the HAIR event bridge, and the HA infrared platform entries. Nothing else.
