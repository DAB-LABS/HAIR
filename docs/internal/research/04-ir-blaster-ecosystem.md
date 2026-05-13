# IR Blaster Ecosystem Analysis

**Date:** 2026-05-12
**Context:** Mapping every IR blaster platform in the HA ecosystem to determine which need conversion layers for HAIR TX support and which work out of the box.

---

## 1. Background

HAIR stores all IR commands as Pronto hex and transmits via the HA `infrared.*` entity platform (InfraredEntity, shipped in HA 2026.4). Any integration that exposes `infrared.*` entities works with HAIR natively. Integrations that only expose `remote.*` entities require either (a) the integration to adopt `infrared.*`, or (b) HAIR to build a conversion layer using `remote.send_command`.

RX (signal capture/learning) is ESPHome-only via the `on_pronto` event bridge. This document focuses on TX (transmit) compatibility.

---

## 2. Platform Inventory

### Works with HAIR today (infrared.* entities)

| Platform | HA Integration | Entity Type | Est. Users | Notes |
|---|---|---|---|---|
| ESPHome ir_rf_proxy | `esphome` (core) | `infrared.*` | ~40K IR users | Day-one launch partner in 2026.4. Native Pronto support. Cheapest DIY option ($5-15). |
| Broadlink RM series | `broadlink` (core) | `infrared.*` | ~75K | Adopted in 2026.5. RM4 Pro, RM Mini, etc. $25-50. Largest installed base of dedicated IR blasters. |
| SMLIGHT SLZB-06IR | `smlight` (core) | `infrared.*` | niche, growing | Adopted in 2026.5. Combined Zigbee coordinator + IR. |

**Coverage estimate:** ~115K of ~125-175K total HA IR users.

### Needs conversion layer (remote.* entities only)

| Platform | HA Integration | Entity Type | IR Format | Conversion Needed | Est. Relevance |
|---|---|---|---|---|---|
| Tuya WiFi IR blasters | `tuya-local` (HACS) | `remote.*` | base64-encoded u16le raw timings (microseconds) | Pronto to/from base64 u16le | High -- large ecosystem, cheap hardware ($8-15) |
| Xiaomi Mijia Universal Remote | `xiaomi_miio` (core) | `remote.*` | Raw timing arrays via miio protocol | Pronto to/from miio raw timings | Medium -- large base in Asia |
| Tuya/Moes Zigbee IR (ZS06, UFO-R11) | `zha` (core) or `zigbee2mqtt` | `remote.*` via ZHA quirk | NEC/RC5 protocol codes or raw hex | Protocol-specific encode/decode | Medium -- cheap ($10-15), battery-powered option |
| LinknLink eRemote HA | MQTT (manual) | `remote.*` via MQTT discovery | MQTT payload (proprietary) | MQTT payload to/from Pronto | Medium -- MQTT-native, ~$13, growing as Harmony replacement |

### Not viable for HAIR

| Platform | Reason |
|---|---|
| SwitchBot Hub (Hub 2, Hub 3, Hub Mini) | Cloud-only integration. No local raw IR access. Users who care about local control are already migrating away. |
| Logitech Harmony Hub | Discontinued (2021). Cloud EOL approaching. Users actively migrating to other platforms. |
| LOOKin Remote | Tiny user base (~1K). Cloud-dependent. Proprietary JSON format. |
| SofaBaton X2 | No HA integration. Standalone remote only. |

### ESPHome-based (same as row 1)

These are ESPHome devices at their core and appear as the same `infrared.*` entities:

- Seeed XIAO IR Mate -- $10, pre-flashed ESPHome
- KinCony AG8 -- $40, requires adding IR LEDs
- Any DIY ESP32 + IR LED build

---

## 3. Tuya Local Deep Dive

### Current state (tuya-local 2026.3.x)

The tuya-local integration exposes Tuya WiFi IR blasters (e.g., Moes UFO-R1, ZemiSmart ZM-IR02) as `remote.*` entities. TX uses `remote.send_command` with the following interface:

```
service: remote.send_command
data:
  command: "b64:<base64-encoded-data>"
  device: "tv"
  num_repeats: 1
```

The IR code format is:
- Base64-encoded binary blob
- Decoded binary contains unsigned 16-bit little-endian (u16le) values
- Each u16 value is a pulse duration in microseconds
- Alternating mark/space pattern (first value is mark, second is space, etc.)
- Sometimes FastLZ compressed for long codes

### Pronto to Tuya conversion

Converting between Pronto hex and Tuya's format is straightforward:

**Pronto to Tuya (TX direction):**
1. Parse Pronto hex header to extract carrier frequency word
2. Compute period: `period_us = 1000000 / (freq_word * 0.241246)`
3. For each timing word pair: `duration_us = word * period_us`
4. Pack as u16le array
5. Base64-encode

**Tuya to Pronto (RX direction -- future use):**
1. Base64-decode
2. Unpack u16le array to get microsecond timings
3. Assume 38kHz carrier (or detect from timing patterns)
4. Compute frequency word: `freq_word = round(1000000 / (carrier_hz * 0.241246))`
5. Convert microsecond timings to Pronto timing words: `word = round(duration_us / period_us)`
6. Assemble Pronto hex string with header

### Tuya Local infrared.* entity adoption

There is evidence that tuya-local 2026.4.x versions may have added `infrared.*` entity support (release notes mention infrared-related changes and HA 2026.4 as a minimum requirement). However, the repo README as of May 2026 still only documents `remote.*` entities for IR blasters.

**If tuya-local adopts infrared.* entities:** HAIR works with Tuya blasters out of the box. No conversion layer needed. This is the preferred outcome.

**If tuya-local does NOT adopt infrared.* entities:** HAIR would need to support `remote.send_command` as a TX fallback with the Pronto-to-Tuya codec described above.

**Action item:** Test with David's Tuya blaster to determine which entity types it currently exposes after updating tuya-local.

---

## 4. Xiaomi Mijia Deep Dive

The `xiaomi_miio` core integration exposes ChuangMi IR controllers as `remote.*` entities. TX uses `remote.send_command` with raw timing arrays sent over the miio protocol.

The format is similar to Tuya's -- raw microsecond pulse durations -- but transported differently (miio local API vs. Tuya local API). The Pronto conversion math is the same.

No evidence of `infrared.*` entity adoption plans for `xiaomi_miio`.

---

## 5. Architecture Implications for HAIR

### Option A: infrared.* only (current approach)

Support only `infrared.*` entities as TX endpoints. Wait for integrations to adopt the new platform.

**Pros:** Simple, clean, forward-looking. Already covers ~115K users.
**Cons:** Excludes Tuya, Xiaomi, LinknLink users until those integrations adopt `infrared.*`.

### Option B: infrared.* preferred, remote.* fallback

Support `infrared.*` entities natively. Additionally allow `remote.*` entities as TX endpoints with pluggable format codecs.

**Pros:** Maximum hardware compatibility. Honors the user's existing blaster investment.
**Cons:** More code to maintain. Each `remote.*` integration has a different format. Testing burden.

### Option C: Pluggable IRCodec interface

Define an `IRCodec` ABC with `to_pronto()` / `from_pronto()` methods. Implement one codec per integration format. The device model stores the codec type alongside the emitter entity ID.

```python
class IRCodec(ABC):
    @abstractmethod
    def to_pronto(self, raw_data: str) -> str: ...
    @abstractmethod
    def from_pronto(self, pronto_hex: str) -> str: ...

class TuyaCodec(IRCodec): ...
class XiaomiCodec(IRCodec): ...
```

**This is the recommended approach if we pursue Option B.** It keeps the conversion logic isolated, testable, and extensible.

### Decision (2026-05-12)

**We are going with Option A: infrared.* only. No remote.send_command fallback.**

Rationale:

- The `infrared.*` entity platform is the HA-blessed standard going forward. Three major platforms (ESPHome, Broadlink, SMLIGHT) adopted it within two months of launch. This covers the vast majority of HA IR users (~115K of ~175K).
- The HA core team designed `infrared.*` specifically so that integrations can provide a standard emitter interface. The expectation is that integrations with IR hardware will adopt it over time, just as Broadlink and SMLIGHT did in 2026.5.
- Building `remote.send_command` fallback with per-integration format codecs would add maintenance burden for a gap that is actively closing at the integration/device level.
- HAIR's value proposition is being native to the HA platform. Leaning into `infrared.*` exclusively keeps the codebase clean and aligned with where the ecosystem is heading.
- For users with Tuya, Xiaomi, or other `remote.*`-only blasters: the path forward is for those integrations to adopt `infrared.*` entities. HAIR will work with them automatically when they do. There is evidence tuya-local 2026.4.x may have already started this.
- If a critical mass of users need support before their integration adopts `infrared.*`, we can revisit. But we are not building speculative conversion layers.

---

## 6. HA infrared.* Entity Adoption Timeline

| Date | Event |
|---|---|
| 2026-01-03 | Architecture discussion #1316 proposed |
| 2026-01-22 | Approved at HA core meeting |
| 2026-03-04 | Implementation PR #162251 merged |
| 2026-04-01 | HA 2026.4 ships with infrared entity platform. ESPHome ir_rf_proxy is launch partner. |
| 2026-05-06 | HA 2026.5 ships. Broadlink and SMLIGHT adopt infrared.* entities. |
| 2026-06/07 (est.) | InfraredReceiverEntity expected (RX side of the platform). |
| TBD | tuya-local, xiaomi_miio adoption status unclear. |

The HA core team has NOT announced any deprecation timeline for `remote.*` entities. The `infrared.*` platform is additive -- it coexists with `remote.*`. Integrations are not required to migrate.

---

## 7. Key Takeaways

1. HAIR targets `infrared.*` entities exclusively for TX. No `remote.send_command` fallback will be built. The ecosystem is converging on `infrared.*` and HAIR stays aligned with that direction.

2. The three biggest IR platforms (ESPHome, Broadlink, SMLIGHT) already support `infrared.*` entities, covering ~115K of ~175K HA IR users.

3. Tuya is the biggest uncovered platform. David has a Tuya blaster. The path forward is for tuya-local to adopt `infrared.*` entities (there is evidence 2026.4.x may have started this). When it does, HAIR works automatically.

4. Conversion layer research (Pronto to Tuya base64 u16le, Pronto to miio raw timings, etc.) is documented in Section 3-4 above for reference if we ever need to revisit.

5. RX (learning/capture) remains ESPHome-only. No other platform provides a viable local RX path. This is by design -- HAIR uses ESPHome's `on_pronto` event bridge for universal capture.

---

## Sources

- [HA Architecture Discussion #1316](https://github.com/home-assistant/architecture/discussions/1316)
- [HA Infrared Entity Developer Blog](https://developers.home-assistant.io/blog/2026/03/30/infrared-entity-platform/)
- [HA 2026.4 Release Notes](https://www.home-assistant.io/blog/2026/04/01/release-20264/)
- [HA 2026.5 Release Notes](https://www.home-assistant.io/blog/2026/05/06/release-20265/)
- [tuya-local GitHub](https://github.com/make-all/tuya-local)
- [xiaomi_miio HA Integration](https://www.home-assistant.io/integrations/xiaomi_miio/)
- [LinknLink eRemote HA](https://github.com/linknlink/python-linknlink)
- [HAIR Market Analysis (03-market-analysis.md)](./03-market-analysis.md)
