# Generic ESP32 doit Dev Kit

A minimal IR TX + RX configuration for the ESP32 doit DevKit v1 (esp32doit-devkit-v1). This is a DIY path -- you wire your own IR LED and IR receiver module to the board.

## Hardware

The config targets the `esp32doit-devkit-v1` board definition. Compatible with most ESP32 DevKit v1 boards from various manufacturers.

Typical sources: AliExpress, Amazon. Search "ESP32 doit DevKit v1".

You will also need an IR LED (with a transistor driver for better range) and a 38kHz IR receiver module (e.g., TSOP38238, VS1838B).

## GPIO Map

| GPIO | Function | Notes |
|---|---|---|
| GPIO4 | IR TX | Connect to IR LED (via transistor recommended) |
| GPIO14 | IR RX | Connect to IR receiver module data pin (inverted, pull-up) |
| GPIO21 | IR power enable | Must be HIGH for IR to work (see Known Quirks) |

## Known Quirks

**GPIO21 power gating (critical):** On this board, GPIO21 gates power to the IR LED and receiver. The config includes a switch entity set to `ALWAYS_ON` that keeps GPIO21 HIGH. Without it, no IR activity will work at all. If your IR hardware seems dead, check that this switch has not been turned off in HA.

This is a board-specific quirk, not an ESPHome or HAIR issue. Other ESP32 boards do not require this.

## Flashing

1. Copy `generic-esp32-doit-minimal.yaml` to your ESPHome config directory
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

Only the minimal variant is provided. It includes IR TX, IR RX with the HAIR event bridge, the GPIO21 power enable switch, and the HA infrared platform entries. Nothing else.
