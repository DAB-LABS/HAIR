# Market Analysis: IR in Home Assistant

**Researcher:** David Bailey
**Date:** 2026-05-08
**Sources:** HA Analytics, GitHub, Industry Reports, Community Forums

---

## 1. Current State of IR in Home Assistant

### Existing Solutions

| Integration | Type | GitHub Stars | Est. Users | Approach |
|---|---|---|---|---|
| SmartIR | Custom (HACS) | ~2,600 | 10,000+ | YAML-based device codes, requires manual JSON files |
| Broadlink | Core | N/A | ~61,000 (6.1% of ~1M) | Hardware-specific, learning via service calls |
| ESPHome IR | Via ESPHome | N/A | Part of ESPHome (~200K+) | DIY, requires ESPHome config YAML |
| LOOKin Remote | Custom | ~200 | 1,000+ | Cloud-dependent IR hub |
| HA Infrared (native) | Core (new) | N/A | Growing (2026.4+) | Platform abstraction, no admin UI |

### Key Pain Points (from community forums)
1. **SmartIR requires YAML** — Users must find or create JSON device code files manually
2. **No unified capture flow** — Each hardware integration has its own learning process
3. **Climate setup is painful** — Converting an IR AC to a proper climate entity requires deep HA knowledge
4. **No device management UI** — Everything is YAML or service call based
5. **Fragmented ecosystem** — Broadlink users, ESPHome users, and SmartIR users are in separate worlds

### Community Evidence of Demand
- SmartIR community forum thread: 1,400+ replies, one of the most active custom integration threads
- Multiple community threads asking for easier IR AC setup
- 120+ climate device codes contributed to SmartIR (community-maintained)
- 2026.4 IR release blog post was one of the most discussed releases

---

## 2. Target Market Size

### Home Assistant Installation Base
- **~1 million** active HA installations (estimated, as of 2026)
- **~250,000** installations opted into analytics
- Analytics opt-in rate: ~20%

### IR-Relevant Installations

| Integration | Analytics Users | Est. Total (÷ 0.2 opt-in) |
|---|---|---|
| Broadlink | ~15,000 | ~75,000 |
| ESPHome (total) | ~40,000 | ~200,000 |
| SmartIR (HACS) | ~2,000 (est.) | ~10,000 |
| **Total IR-adjacent** | **~57,000** | **~285,000** |

Note: Not all ESPHome users have IR, but many ESPHome setups include at least one IR component. Conservative estimate: 20% of ESPHome users = ~40,000 IR-capable.

**Estimated total addressable market within HA: ~125,000 - 175,000 installations**

### Growth Projection
With HA 2026.4 making IR a first-class platform, adoption will accelerate. The Broadlink-as-emitter addition in 2026.5 immediately unlocks ~75,000 existing Broadlink users.

---

## 3. Climate Control Market

### The Big Opportunity

**88% of U.S. households use air conditioning** (EIA, 2020 RECS). Of those:
- ~67% use central AC/heat pump (ducted — not IR controlled)
- ~23% use room/window AC units (many IR-controlled)
- ~10% use ductless mini-splits (virtually all IR-controlled)

### Mini-Split Growth
- **3+ million new mini-split units sold since 2022** in the US alone
- **20% of new residential construction** now includes pre-installed ductless systems
- **15%+ annual growth** in single-zone mini-split sales
- **40% concentration** in northeast/midwest US (older homes without ductwork)
- Mini-splits are the fastest-growing HVAC segment globally

### Why This Matters for HA IR Admin
Every mini-split comes with an IR remote. Every mini-split owner who also uses HA wants:
1. Thermostat scheduling (instead of using the remote)
2. Automation integration (turn off AC when nobody's home)
3. Energy monitoring and optimization
4. Multi-zone coordination

Currently, setting this up in HA requires SmartIR + YAML + finding the right device code file + manual climate entity creation. HA IR Admin makes this a 3-click process.

---

## 4. David's Hypothesis: IR > Bluetooth/Zigbee/Z-Wave?

### Protocol Comparison (within HA)

| Protocol | Est. HA Users | Primary Use Case | Hardware Needed |
|---|---|---|---|
| Z-Wave | ~97,000 (9.7%) | Switches, locks, sensors | Z-Wave stick ($35-50) |
| ZHA/Zigbee | ~150,000 (15%) | Lights, sensors, switches | Zigbee coordinator ($25-40) |
| Bluetooth | ~100,000 (est.) | Sensors, trackers | Built into most hardware |
| **IR (potential)** | **~125,000-175,000** | **TVs, ACs, fans, soundbars** | **IR blaster ($5-25)** |

### The Case FOR David's Hypothesis

1. **Lower hardware barrier**: An IR blaster costs $5-15 (ESP32 + IR LED DIY) or $25 (Broadlink RM Mini). Zigbee/Z-Wave sticks cost $25-50.

2. **Existing device density**: The average household has 5-10 IR-controlled devices (TVs, soundbars, AC units, fans, DVD/Blu-ray players, cable boxes). Compare: average Z-Wave network has 17 devices, but those had to be *purchased* as smart devices.

3. **Climate control is universal**: AC/heating is a top-3 smart home use case globally. Mini-splits (all IR) are the fastest-growing HVAC segment.

4. **Replacement cost**: IR control requires zero device replacement. Z-Wave/Zigbee typically requires buying new smart switches/sensors/locks.

5. **Global appeal**: IR-controlled devices are ubiquitous worldwide, especially in Asia where mini-splits dominate. Z-Wave has regional frequency issues.

### The Case AGAINST

1. **IR is one-directional** — No feedback, no state confirmation. Z-Wave/Zigbee are bidirectional.
2. **Line-of-sight requirement** — IR needs line of sight; wireless protocols don't.
3. **HA has treated IR as second-class** until 2026.4 — Zigbee/Z-Wave have years of polish.
4. **Enthusiast vs. mainstream** — IR control requires more user understanding than plug-and-play Zigbee devices.
5. **No device discovery** — IR devices can't be discovered on a network. Z-Wave/Zigbee auto-discover.

### Verdict

**David's hypothesis is plausible but nuanced.** IR's addressable market *within HA* may indeed be larger than any single wireless protocol — but the user experience gap has historically prevented realization of that potential. If HA IR Admin can make IR setup as frictionless as adding a Zigbee device, the thesis becomes very strong. The native IR platform in 2026.4 removed the infrastructure barrier. HA IR Admin would remove the UX barrier.

The climate control angle alone is compelling: there's no Zigbee thermostat for your mini-split. IR is the only path.

---

## 5. Competitive Landscape

### Standalone IR Apps

| Product | Price | IR Devices Supported | HA Integration | UX Quality |
|---|---|---|---|---|
| Broadlink App | Free (with hw) | 100,000+ | Yes (basic) | Medium |
| SwitchBot Hub | $20-55 | 80,000+ | Yes (cloud) | High |
| Tuya/Smart Life | Free (with hw) | 50,000+ | Yes (cloud) | Medium |
| Logitech Harmony | Discontinued | N/A | Legacy only | Was excellent |

### Key Observations
1. **Logitech Harmony's discontinuation** left a massive void for power users
2. SwitchBot has the best UX but is cloud-dependent — antithetical to HA users
3. Broadlink has the largest database but terrible learning UX
4. **No solution exists that is**: local-first, HA-native, UI-driven, and proxy-agnostic

### The Opportunity
HA IR Admin would be the **only** solution that is:
- Local-first (no cloud dependency)
- Built on HA's native IR platform
- Hardware-agnostic (works with any emitter)
- UI-driven (no YAML)
- Integrated into HA's device/entity model

This is an unoccupied niche with significant demand.

---

## 6. Adoption Trajectory Comparison

### Z-Wave in HA
- Z-Wave integration has been in HA for 8+ years
- Went through multiple rewrites (OZW → Z-Wave JS)
- Major admin UI overhaul with Z-Wave JS UI
- Currently ~97,000 users

### Zigbee (ZHA) in HA
- ZHA has been growing faster than Z-Wave
- ~150,000 users, 15% of installations
- Strong device support, good pairing UX

### Projected IR Trajectory
If HA IR Admin launches with a strong UX:
- **Month 1**: 1,000-2,000 HACS installs (early adopters, SmartIR migrants)
- **Month 3**: 5,000-8,000 installs (word of mouth, community reviews)
- **Month 6**: 15,000-25,000 installs (if featured in HA blog/podcast)
- **Year 1**: 30,000-50,000 installs (established as the IR management standard)

The ceiling is ~175,000 (total IR-capable HA installations), but realistic year-1 capture is 20-30% with strong UX.

---

## 7. Summary

| Factor | Assessment |
|---|---|
| Market size | Large (125K-175K HA installations, growing) |
| Competition within HA | Weak (SmartIR is YAML-only, no native admin) |
| Competition outside HA | Moderate (SwitchBot, Broadlink apps) but different audience |
| Technical foundation | Strong (2026.4 IR platform is solid) |
| User demand | High (most-requested HA improvement category for IR) |
| Timing | Excellent (just after IR platform launch, before alternatives emerge) |
| David's hypothesis | Plausible — IR addressable market may exceed Zigbee/Z-Wave within HA |

**Recommendation: Proceed. The market is ready, the platform is ready, and the UX gap is the only remaining barrier.**

---

## Sources

- [HA Analytics](https://analytics.home-assistant.io/)
- [SmartIR GitHub](https://github.com/smartHomeHub/SmartIR)
- [SmartIR Community Thread](https://community.home-assistant.io/t/smartir-control-your-climate-tv-and-fan-devices-via-ir-rf-controllers/100798)
- [HA 2026.4 Release](https://www.home-assistant.io/blog/2026/04/01/release-20264/)
- [EIA Residential Energy Survey](https://www.eia.gov/todayinenergy/detail.php?id=52558)
- [Ferguson Ductless HVAC Market](https://www.ferguson.com/content/ideas-and-learning-center/business-insider/ductless-hvac-market-growth/)
- [ZHA Analytics Discussion](https://community.home-assistant.io/t/home-assistant-founders-believe-there-is-currently-around-50-000-installations-of-zha-integration)
- [Z-Wave Is Not Dead](https://www.home-assistant.io/blog/2024/05/08/zwave-is-not-dead/)
- [SwitchBot Hub 2](https://www.switch-bot.com/products/switchbot-hub-2)
- [Smart Remote Controls 2026](https://www.smarthomeperfected.com/smart-remote-controls/)
