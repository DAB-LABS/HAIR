# Seeed Studio XIAO Smart IR Mate

A commercial off-the-shelf IR transceiver based on the Seeed XIAO ESP32-C3. No soldering required -- the IR LED, IR receiver, touch sensor, RGB status LED, and vibration motor are all built in. This is the easiest hardware path to get HAIR running.

## Hardware

Purchase: [Seeed Studio XIAO Smart IR Mate](https://www.seeedstudio.com/Seeed-XIAO-Smart-IR-Mate.html)

The device ships as a complete unit. Plug it in via USB-C, flash via ESPHome, and it is ready to use with HAIR.

## GPIO Map

| GPIO | Function | Notes |
|---|---|---|
| GPIO3 | IR TX | Built-in IR LED |
| GPIO4 | IR RX | Built-in IR receiver (inverted) |
| GPIO5 | Touch sensor | D3, capacitive touch pad (full variant only) |
| GPIO6 | Vibration motor | D4, haptic feedback (full variant only) |
| GPIO7 | RGB LED | D5, WS2812, WiFi status indicator (full variant only) |

## Flashing

1. Copy your chosen variant to your ESPHome config directory
2. Update the `substitutions` block with your preferred device name
3. Add required entries to your `secrets.yaml` (see below)
4. Flash via the ESPHome Dashboard or CLI

## Required secrets.yaml entries

For the minimal variant:

```yaml
api_encryption_key: "<your-api-encryption-key>"
ota_password: "<your-ota-password>"
wifi_ssid: "<your-wifi-ssid>"
wifi_password: "<your-wifi-password>"
ap_password: "<your-fallback-ap-password>"
```

For the full variant, replace `#ENCRYPTION_KEY#` and `#PASSWORD#` placeholders directly in the YAML, or switch them to `!secret` references (recommended).

Generate an API encryption key with: `python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`

## Compatibility

| Component | Version |
|---|---|
| HAIR | 0.1.2 |
| HA Core | 2026.5.2 |
| ESPHome | 2026.4.5 |

## Variants

**Minimal** (`xiao-ir-mate-minimal.yaml`): Smallest config that gets IR TX + RX working with HAIR. Touch sensor, RGB LED, and vibration motor are not configured. Start here if you just want HAIR working.

**Full** (`xiao-ir-mate-full.yaml`): Preserves all XIAO IR Mate hardware features -- touch sensor with haptic feedback, RGB LED for WiFi status, factory reset and restart buttons. Contributed by [@Didgeridrew](https://community.home-assistant.io/u/Didgeridrew) on the HA Community Forum, blending the official [esphome/infrared-proxies](https://github.com/esphome/infrared-proxies) config with Seeed Studio's stock XIAO features.

## Attribution

The full variant is based on work by [@Didgeridrew](https://community.home-assistant.io/u/Didgeridrew), shared in the [HAIR forum thread](https://community.home-assistant.io/t/1010610/12) and contributed with permission. Thank you, Drew.
