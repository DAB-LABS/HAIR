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
| GPIO7 | RGB LED | D5, WS2812, blinks dim red while WiFi is down (full variant only) |

## Flashing

1. Copy your chosen variant to your ESPHome config directory
2. Update the `substitutions` block with your preferred device name
3. Add required entries to your `secrets.yaml` (see below)
4. Flash via the ESPHome Dashboard or CLI

## Required secrets.yaml entries

Both variants use the same entries:

```yaml
api_encryption_key: "<your-api-encryption-key>"
wifi_ssid: "<your-wifi-ssid>"
wifi_password: "<your-wifi-password>"
ap_password: "<your-fallback-ap-password>"
```

Generate an API encryption key with: `python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`

Already running this config with an OTA password? If the device's firmware was built with ESPHome 2026.9.0 or newer (Home Assistant shows the version on the device page), install the new config as usual and take `ota_password` out of your secrets. If it is older, install your current config once more with ESPHome 2026.9.1 or newer first, then the new one; ESPHome refuses to send the new config to older firmware and says so. ESPHome stops accepting that route in 2027.3.0, after which an older device has to be flashed over USB.

## Compatibility

| Component | Version |
|---|---|
| HAIR | 0.1.2 |
| HA Core | 2026.5.2 |
| ESPHome | 2026.9.1 |

## Variants

**Minimal** (`xiao-ir-mate-minimal.yaml`): Smallest config that gets IR TX + RX working with HAIR. Touch sensor, RGB LED, and vibration motor are not configured. Start here if you just want HAIR working.

**Full** (`xiao-ir-mate-full.yaml`): Preserves all XIAO IR Mate hardware features -- touch sensor with haptic feedback, RGB LED for WiFi status, factory reset and restart buttons. The LED stays dark while connected, blinks dim red while WiFi is down, and is hidden from Home Assistant. Contributed by [@Didgeridrew](https://community.home-assistant.io/u/Didgeridrew) on the HA Community Forum, blending the official [esphome/infrared-proxies](https://github.com/esphome/infrared-proxies) config with Seeed Studio's stock XIAO features.

## The status LED and areas

The full variant's LED is internal. If you remove `internal: true`, it becomes a light entity, and once the IR Mate is in an area, area-wide light commands (`light.turn_on` with `area_id`, occupancy automations, voice commands, the area card) turn it on too. Target light entities instead of `area_id`, or leave the LED internal.

## Attribution

The full variant is based on work by [@Didgeridrew](https://community.home-assistant.io/u/Didgeridrew), shared in the [HAIR forum thread](https://community.home-assistant.io/t/1010610/12) and contributed with permission. Thank you, Drew.
