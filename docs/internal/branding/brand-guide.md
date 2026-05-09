# HAIR — Brand Guide v1

**Project:** HAIR (Home Assistant IR)
**Author:** David Bailey
**Date:** 2026-05-08
**Status:** Living document

---

## 1. The Big Idea

**HAIR is the barbershop for your smart home's IR devices.**

A neighborhood shop. Walk-ins welcome. Old-school craft, new-school tech. Your TV, your AC, your soundbar — they all come in for a cut, walk out with personality.

The product gives every IR device in your home the control (and personality) it's been missing. The brand wraps that promise in a world that's instantly recognizable, warm, and a little bit cool.

---

## 2. Aesthetic Direction — "Neo-Tiki Barbershop"

Sailor Jerry tattoo flash × cyberpunk neon × tiki warmth × classic barbershop ritual.

A 1940s American barbershop and a Hong Kong night market had a baby in a Bali surf shack. Then it grew up watching Blade Runner. That's the visual world.

**The four ingredients:**

| Element | What it brings |
|---|---|
| **Sailor Jerry** | Bold black linework, limited palette, nautical/floral motifs, timeless craft, swallows and hibiscus and banners |
| **Cyberpunk** | Neon glow accents, holographic shimmer, the signal that this is *technology*, the night-shop atmosphere |
| **Tiki** | Carved wood textures, hibiscus and banana leaves, warmth, a sense of *place* — your home, hanging out |
| **Barbershop** | The pole, the chairs, the mirrors, the ritual of the visit, "walk-ins welcome" |

Together it reads as: **crafted, confident, a little dangerous, definitely not corporate, made by someone who gives a damn.**

---

## 3. Tagline & Voice

### Primary Tagline

> **Style Your HAIR.**

Three words. Pun, instruction, and brand promise in one. Use it everywhere — hero copy, t-shirts, the GitHub README's first line, every release announcement.

### Hero Lockup

> # HAIR
> ## Style Your HAIR.
> *Capture every IR command. Control every device. Local-first, always.*

### Supporting Taglines (Rotation)

For social posts, blog headers, easter eggs, release notes:

- **Walk-ins welcome.** *(the workhorse — use this one a lot)*
- Old school. New tricks.
- Open since 2026.
- By appointment, or whenever.
- Sharper than a YAML file.
- Every device deserves a chair.
- From the shop to your stack.
- Local-first. Always sharp.

### Voice — "The Old-School Barber Who's Been to the Future"

Confident, brief, doesn't waste words. Has seen everything. Slightly tattooed. Has opinions. The shop has been there a long time. It doesn't need to oversell.

**Voice principles:**

1. **Brief.** A barber doesn't narrate the haircut.
2. **Confident, not cocky.** We know what we're doing. We don't need to brag.
3. **Warm, not chatty.** The greeting matters. The small talk doesn't.
4. **Anti-cloud, pro-local.** Says it once, doesn't preach.
5. **Pun-curious, never pun-drunk.** The puns live in marketing. The product UI is clean.

**Voice in practice:**

| Surface | Don't say | Say |
|---|---|---|
| Empty state | "Looking a little plain. Let's give this thing some style." | "Empty shop. Let's get you a chair." |
| Capture error | "Hmm — couldn't catch that signal. Let's try again." | "Missed it. Take a seat, we'll go again." |
| Success | "Looking good. ✨" | "That'll do." |
| Welcome | "Welcome to the show!" | "Walk-ins welcome. Take any chair." |
| 404 | "Oops! This page doesn't exist." | "Closed for the day. Be right back." |

---

## 4. The Pun Budget

**Critical brand principle.** The HAIR/barbershop puns are seasoning, not the meal.

### Pun-encouraged surfaces ✓

- Marketing site hero copy
- Release announcement headlines
- HACS listing description
- Social media posts
- Easter eggs in empty states
- Stickers, t-shirts, posters
- Blog post titles

### Pun-forbidden surfaces ✗

- Error messages (be clear, not cute)
- Setup/config flow (be fast, not flashy)
- Documentation (be useful, not clever)
- Diagnostics (be precise)
- Anything safety-relevant

**Why:** Make the marketing fun. Make the product invisible. Users should feel clever for finding HAIR — not annoyed by us reminding them of the name every screen.

---

## 5. Visual Identity — The Logo System

### The Master Brand Mark: The Barber Pole

The **barber pole** is the brand mark. Iconic, scales to a favicon, instantly recognizable across cultures, and stable enough that AI image models render it consistently.

We use a **prompt-standardized, run-variable** approach: every logo asset is generated from the same master prompt family. We accept variation between runs as part of the brand — controlled inconsistency, unified by the prompt.

### Master Logo Prompt (v2 — LOCKED 2026-05-08)

This is the canonical prompt for the primary HAIR brand mark. All logo assets in the family are generated from this prompt or one of its named variants below.

> A Sailor Jerry American traditional tattoo flash design on a cream textured background. A traditional barber pole stands vertically — red, white, and navy spiral stripes in a glass cylinder, chrome cap and finial top, with hot pink and electric cyan neon glow along its edges. The pole is wrapped diagonally by a large, dominant cream-colored ribbon banner that takes up the central 50% of the composition. The banner reads "HAIR" in oversized bold serif tattoo-style letterforms — letters tall, thick, deep red with black outlines and subtle drop shadow, filling the entire banner. No subtitle, no secondary text. The banner has classic Sailor Jerry shading and curls at each end. Below the pole sits a carved wooden tiki totem with hibiscus flowers and ocean teal leaves on either side. Bold black outlines throughout. Palette: cream, deep red, navy blue, ocean teal, hot pink and cyan neon. Centered composition.

**Why this prompt won the v1 → v2 iteration:**
- HAIR wordmark dominates ~50% of vertical real estate (was ~15% in v1)
- Banner is the focal point with classic tattoo-style curls and shading
- Pole peeks through purposefully — supporting, not competing
- Tiki + hibiscus stays grounded as the base
- Cyberpunk neon glow reads cleanly against the warm palette
- "BARBER SHOP" subtitle dropped to keep the wordmark pure

### Logo Variant Prompts (Same Brand, Different Asset)

Each variant starts from the master prompt, with the noted modifications:

**Variant A — Wordmark-Only (cramped surfaces, headers)**
> [Master prompt] — but remove the barber pole, the tiki totem, and the hibiscus flowers. Show only the cream-colored ribbon banner with "HAIR" in oversized bold serif tattoo-style letterforms, deep red with black outlines and drop shadow, on a cream textured background. Sailor Jerry shading and ribbon curls at each end. No other elements.

**Variant B — Pole-Only (favicon, app icon, sidebar icon)**
> [Master prompt] — but remove the ribbon banner and the "HAIR" wordmark entirely. Show only the traditional barber pole with red, white, and navy spiral stripes, chrome cap and finial, hot pink and cyan neon glow along its edges, sitting on a small carved tiki totem base with hibiscus flowers and ocean teal leaves on either side. Bold black outlines. Cream textured background. Centered, vertical composition. Designed to read clearly at small sizes.

**Variant C — Horizontal Lockup (site headers, email signatures, social cards)**
> A Sailor Jerry American traditional tattoo flash design on a cream textured background, in a wide horizontal composition. On the left, a large cream-colored ribbon banner reads "HAIR" in oversized bold serif tattoo-style letterforms — deep red with black outlines and drop shadow, classic Sailor Jerry shading and curls at each end. On the right, a traditional barber pole with red, white, and navy spiral stripes glows softly with hot pink and electric cyan neon, mounted on a small carved tiki totem base flanked by hibiscus flowers and ocean teal leaves. Bold black outlines throughout. Palette: cream, deep red, navy blue, ocean teal, hot pink and cyan neon.

**Variant D — Shop Sign (full "HAIR — IR Stylists" version, formal contexts)**
> [Master prompt] — but add a smaller secondary banner curling beneath the main "HAIR" banner, reading "IR STYLISTS" in stencil-style condensed lettering. Both banners cream-colored, both with Sailor Jerry shading and curls. The pole is mostly hidden behind the two banners. Tiki and hibiscus remain at the base.

### Prompt Modifier Library (Optional Variations)

Append any of these to a base prompt for occasional thematic variations while staying on-brand:

- *"...with a small lightning bolt detail at the top of the pole"*
- *"...with a hibiscus flower replacing the top finial"*
- *"...with subtle holographic chrome shimmer on the spiral"*
- *"...with banana leaves framing the base"*
- *"...with a small swallow tattoo perched on top"*

### Logo Asset Family

Five marks, all generated from the prompt family above:

| # | Asset | Use |
|---|---|---|
| 1 | **Primary logo** | Barber pole + HAIR wordmark on banner — main brand mark |
| 2 | **Wordmark only** | "HAIR" in vintage barbershop serif — when the pole would be redundant |
| 3 | **Pole only** | Standalone pole — favicon, app icon, sidebar icon in HA |
| 4 | **Shop sign** | Full "HAIR — IR Stylists" hand-painted sign — site headers, merch |
| 5 | **Tattoo flash mark** | A single device-as-tattoo design — stickers, social secondary |

### Logo Placement Rules

- Always allow generous breathing room (logo height of clear space on all sides)
- Never recolor outside the brand palette
- Never stretch or distort
- Acceptable on: cream, bone white, deep navy backgrounds
- Avoid on: busy photographs, brand red (clashes with pole), any green
- Minimum size: 32px tall for digital, 0.5 inch for print
- For favicon use: simplified pole-only version, no wordmark

---

## 5.5 The Mascot — Hairy Hank

### Who He Is

**Hairy Hank** is the HAIR mascot. He is the warm, friendly, slightly mischievous face of the brand. The locked HAIR wordmark + barber pole is the *logo*; Hank is the *character*. They work together: the wordmark sells the brand, Hank sells the *feeling*.

Hank pays homage to the 1980s plastic troll dolls without infringing on the trademarked "Troll Doll" / "Good Luck Troll" IP. We use AI-generated assets only and **do not push merch** — Hank lives in marketing, social, and in-product illustrations.

### Hank's Locked Character Design

**Body:**
- Small, chubby cartoon proportions (classic troll silhouette)
- Warm tan plastic-toy skin tone
- **Round circular belly button visible on his stomach** — mandatory, this is the homage
- Bare feet (always)
- Short arms, stubby legs, slightly oversized head

**Face:**
- Big round expressive eyes
- Wide goofy grin
- Round nose
- Friendly and slightly mischievous

**Hair (the hero element):**
- Massive, voluminous, gravity-defying upright hair
- Tall — at least equal to body height
- **Rendered in classic Sailor Jerry tattoo color shading: deep barber red at the roots → warm orange in the middle → bright Sailor Jerry yellow at the tips**
- Color zones are **distinct flat color blocks (not soft gradients)** separated by bold black ink outlines
- Small white highlight pops at the peaks where light catches
- Looks like classic American traditional tattoo flames

**Clothing:**
- **Default: white t-shirt with "HAIR" across the chest** in our locked tattoo-flash serif red lettering
- Wardrobe variants permitted for scenarios (apron, hoodie, tank, holiday tee, tour tee)

**What Hank does NOT have:**
- ❌ No IR signal waves coming off his hair
- ❌ No hibiscus flowers around him
- ❌ No tattoo-flash banner curling at his feet (the wordmark lives on his shirt)
- ❌ No tiki carving as a base
- ❌ No props unless a scenario requires them

### Hair Color = Mood Indicator (Brand Mechanic)

Hank's flame hair changes "temperature" based on context. The flame is a built-in mood/state indicator:

| State / Context | Flame logic |
|---|---|
| **Default Hank** | Red → orange → yellow (warm flame) |
| **Capturing IR** | Pink → magenta → cyan (cyberpunk flame, hot at bottom, cold at top) |
| **AC / Cool scene** | Navy → teal → cyan (cool flame / icy fire) |
| **YAML defeated** | Default warm flame, but bigger and more aggressive |
| **Holiday / December** | Red → green → white (seasonal flame) |
| **Sleeping / idle** | Cream → tan → cream (the flame is "out") |
| **Greatest hits / celebration** | Multi-zone rainbow flame |

This is more visually interesting than a flat hair color swap and gives every scenario built-in narrative.

### Master Prompt — Hairy Hank (LOCKED v8 — FINAL)

**Canonical reference image:** [`assets/hank-master-v8-final.png`](./assets/hank-master-v8-final.png)

This is the canonical Hank prompt. Every Hank illustration starts here. Locked after iterating through 8 versions to land on the definitive character: an aged-up plastic troll doll with a magnificent towering Sailor Jerry flame mane, working as a barbershop barber in a tobacco-leather smock, dressed underneath like the suburban dad he is on weekends.

When evaluating any new Hank render, compare it against the canonical reference image above. Every defining element (towering hair, troll face, wireframes, smock with HAIR patch, dad outfit peeking through, New Balance + crew socks) must match.

> A friendly retro mascot character illustrated in Sailor Jerry American traditional tattoo flash style with bold black outlines and flat color fills, **rendered on a tall vertical canvas (2:3 portrait aspect ratio)**.
>
> **CRITICAL COMPOSITION RULE — read this first and treat it as the most important constraint of the entire image:**
>
> **The hair MUST occupy approximately 65-70% of the total vertical height of the image. The character's body (head + smock + legs + shoes) occupies only the BOTTOM 25-30% of the image. The remaining 5% is breathing room. This is non-negotiable. The hair is enormous, towering, dominant — at least 3 to 4 times the height of the entire body. Picture: if the body is 1 foot tall, the hair is 4 feet tall above it.**
>
> **DO NOT center the body in the canvas. DO NOT make the hair "tall but proportional." DO NOT balance the composition. The character looks like a tiny troll standing under a magnificent towering inferno of hair that dwarfs him completely.** This deliberate imbalance is the entire point — it pays homage to 1980s plastic troll dolls whose hair was always far taller than their bodies.
>
> ---
>
> The character is **Hairy Hank**, a small chubby cartoon figure that is unmistakably a 1980s plastic troll doll aged into middle age and working as a barbershop barber. Preserve all classic troll doll features: a slightly oversized round head with chunky troll proportions, large prominent ears that stick out from the sides of his head, a distinctive bulbous flat squashed troll nose taking up the center of his face, big round shiny expressive troll eyes with bright catchlights, warm tan plastic-vinyl-toy skin tone with that distinctive shiny plastic-doll quality, slightly chubby cheeks, and a slightly mischievous knowing smirk. Subtle laugh lines at the corners of his eyes suggest a middle-aged troll who's been doing this work for decades.
>
> He wears thin minimalist gold wireframe glasses with small oval lenses sitting low on his bulbous nose.
>
> He has a visibly receded mature hairline with a clearly pronounced bald forehead. The towering hair erupts from the back two-thirds of his scalp.
>
> ---
>
> **THE HAIR (the entire upper 65-70% of the canvas):**
>
> The hair is a magnificent, towering, gravity-defying flame mane that erupts from his head and rises massively upward — at least 3-4 times the height of his body, dominating the upper two-thirds of the entire composition. It is wider than his shoulders at the base and tapers into multiple flame tongues at the very top.
>
> The hair must look like actual furry voluminous troll-doll hair (like teased-up brushed synthetic doll fur with visible strand texture, fluffy soft edges with stray strands breaking free, and three-dimensional volume) styled into the SHAPE of a colossal Sailor Jerry tattoo flame. Every internal portion of the flame is rendered with hair texture — visible individual hair strands and tufts, internal linework throughout — not flat decorative flame icons, but real hair shaped like fire.
>
> Use classic Sailor Jerry tattoo color shading: deep barber red at the roots, transitioning to warm orange in the middle third, fading to bright Sailor Jerry yellow at the tips. The colors blend through the strand texture in distinct zones with bold black ink outlines defining the overall flame silhouette and finer black ink linework throughout the interior depicting individual strands. Small white highlight shapes at the peaks where light catches the hair.
>
> ---
>
> **THE BARBER BODY (the bottom 25-30% of the canvas):**
>
> Hank stands centered in the lower portion of the canvas. He wears a rich tobacco-brown weathered leather barber smock (apron style) tied at the neck and waist, hanging from his chest down to mid-thigh. The smock has visible brass rivets at the corners, brass eyelets at the neck strap, and two patch pockets across the front waist. The leather has subtle patina and faint working scuff marks. A small "HAIR" patch is stitched on the left chest in bold red thread serif lettering with black outlines.
>
> **Underneath the smock he is dressed like a suburban dad on a Saturday — a tucked-in white short-sleeve polo shirt with a small collar (the polo collar visible at his neck above the smock's neckline, the polo's HAIR-printed chest hidden behind the smock), tan cargo shorts visible peeking out below the smock hem with their characteristic side pocket detail, bright white chunky New Balance dad sneakers, and white crew socks pulled up at the ankles. The dad-outfit details — the polo collar, the cargo shorts hem with side pockets, the chunky white sneakers, the white crew socks — are all clearly visible around the edges of the smock, telling the viewer that under the professional barber gear is just a regular suburban dad.**
>
> A small round circular belly button is visible briefly where the smock pulls open at his bare midriff (subtle troll homage detail).
>
> He stands in a relaxed confident pose, arms slightly out at his sides — he's the barber waiting for his next walk-in.
>
> ---
>
> **OVERALL:**
>
> Clean cream textured background with subtle vintage paper texture filling the entire canvas. Bold black tattoo-style outlines defining all major shapes, with finer ink linework inside the hair for strand texture and on the leather smock for material detail. Limited palette: cream background, warm tan plastic-doll skin, deep red, warm orange, Sailor Jerry yellow flame hair, tobacco brown leather smock, white polo collar, tan/khaki cargo shorts, white New Balance sneakers, white crew socks, gold wireframe glasses, brass rivet accents, white highlight pops.
>
> No flowers, no banners, no signal waves, no other elements. Single character, vertical composition, hair dominates upper two-thirds, body in lower third.

### The Locked Hank Silhouette

The signature read of Hank, top to bottom, in 0.5 seconds:

1. **Top of frame:** "HOLY HAIR" — towering Sailor Jerry flame mane dominates the upper 2/3
2. **Middle:** "Oh, he's a barber" — tobacco leather smock, name patch, troll face with wireframes
3. **Bottom of frame:** "Wait — he's also just a dad" — cargo shorts hem, white New Balance, crew socks

Three-act visual storytelling in a single still image. Hank is a craftsman *and* one of us. The expert *and* the audience.

### Hank Wardrobe Variants

The default Hank is the locked Barber-with-Dad-Underneath. For specific scenarios, only the **outermost layer** changes — the dad outfit underneath is preserved (sometimes peeking, sometimes implied). The flame hair, troll face, and wireframes never change.

- **Default — Barber Hank** *(locked above)*: Tobacco leather smock over polo + cargo shorts + New Balance
- **Out of the Shop** — No smock, just the dad outfit (polo with HAIR on chest, cargo shorts, New Balance) for casual scenarios
- **Holiday Smock** — Smock over a red and green ringer tee, December version
- **Tour Smock** — Black smock variant for special editions
- **Rolled-Sleeve Working Hank** — Smock tied loosely, polo sleeves rolled, mid-job energy

### Hank Scenario Library

Each scenario starts with the locked v8 Master Prompt above. The character (towering flame hair, troll face, wireframes, leather smock with HAIR patch, dad outfit underneath, New Balance sneakers) stays exactly the same — only the pose, props, hair color, or background changes per scenario.

**Scenario 1 — Hank with the Remote** *(hero / about page)*
> [Master prompt v8] — but instead of a relaxed pose, he holds an oversized vintage TV remote control with both stubby troll hands, gripping it from the sides, pressing a large red button on the front with one thumb. His expression is focused but happy, mouth in a small "o" of concentration. The remote is rendered in matching Sailor Jerry tattoo flash style with bold black outlines, dark navy body with red, cream, and teal buttons. All other character details (towering flame hair, leather smock with HAIR patch, dad outfit peeking through) remain unchanged.

**Scenario 2 — Hank Captures a Signal** *(in-product capture state)*
> [Master prompt v8] — but his towering flame hair shifts to cyberpunk colors: hot pink at the roots, magenta in the middle, electric cyan at the tips. Same fur-strand texture and flame silhouette. He stands in a focused listening pose with his stubby troll hands cupped near his prominent ears like he's straining to hear something faint. Eyes wide and alert, mouth slightly open in concentration. Cream background with a very subtle radial cyan glow behind his head.

**Scenario 3 — Hank on the Mini-Split** *(climate marketing)*
> [Master prompt v8] — but his towering flame hair shifts to cool colors: navy at the roots, ocean teal in the middle, electric cyan at the tips (icy fire). He's perched on top of a wall-mounted ductless mini-split air conditioner, lounging casually with his New Balance sneakers dangling off the edge. Cool air visibly puffs from the AC vents below him. He gives a thumbs up. The mini-split is rendered in matching tattoo flash style.

**Scenario 4 — Hank vs. YAML** *(anti-config messaging)*
> [Master prompt v8] — but his warm flame hair is even bigger and more aggressive than usual. He stands triumphantly on top of a large crumpled piece of paper that has "YAML" written across it in distressed lettering. The paper looks defeated, wrinkled, with one corner torn. Confident victory pose, hands on his smock-clad hips, chin slightly raised, big mischievous smirk.

**Scenario 5 — Hank Family Portrait** *(home page hero)*
> A horizontal lineup of five Hairy Hank mascot characters in a row, each rendered as the locked v8 character: middle-aged plastic troll dolls with bulbous noses, big shiny eyes, wireframe glasses, receded hairlines, towering Sailor Jerry flame hair, tobacco-brown leather barber smocks with red "HAIR" patches, and dad outfits visible underneath (polo collars, cargo shorts hems, white New Balance, crew socks). **Each Hank has enormous towering flame hair in a different color scheme: (1) classic warm flame red→orange→yellow, (2) cyberpunk flame pink→magenta→cyan, (3) icy flame navy→teal→cyan, (4) sunset flame red→pink→yellow, (5) rainbow flame multi-color.** Each holds a different vintage remote: TV remote, AC remote, soundbar remote, ceiling fan remote, projector remote. All five stand evenly spaced on a clean cream textured background. Sailor Jerry tattoo flash style throughout, bold black outlines, flat color fills. No banners, no flowers.

**Scenario 6 — Sleeping Hank** *(idle / 404 / "be right back")*
> [Master prompt] — but his flame hair is "out" (faded cream → tan → cream, drooping slightly downward instead of standing tall). He is curled up asleep in a small vintage red barber chair, knees pulled up, head tilted to one side, eyes closed peacefully, mouth slightly open in a small smile. Three small "Z" letters float upward from his head in classic cartoon style. The barber chair is rendered in matching tattoo flash style — bold black outlines, deep red leather seat, chrome metal accents.

**Scenario 7 — Hank with the IR Blaster** *(setup / config flow)*
> [Master prompt] — but he's proudly displaying a small ESP32-style IR blaster device in his hands like a trophy, eyes wide with excitement. Standard warm flame hair.

**Scenario 8 — Hank vs. Cloud** *(local-first messaging)*
> [Master prompt] — but his flame hair shifts to icy fire (navy→teal→cyan). He's confidently pushing back a stormy navy cloud with both hands. The cloud has a small "X" through it.

**Scenario 9 — Greatest Hits Hank** *(release notes / blog)*
> [Master prompt] — but his flame hair is rainbow multi-color (all six brand neon colors mixed). He's on a small stage with a tiny microphone, wearing comically small sunglasses. A single spotlight on him.

**Scenario 10 — Holiday Hank** *(seasonal December)*
> [Master prompt] — but his flame hair shifts to seasonal colors: deep red at the roots, evergreen green in the middle, bone white at the tips. He's wearing a tiny Santa hat that comically can't sit flat on his enormous wild hair. He holds a small wrapped present labeled "v2.0."

### Hank Usage Rules

- **Hank is the mascot, not the logo.** The HAIR wordmark + pole is the brand mark. Hank is the character.
- **Always render Hank in the locked Sailor Jerry tattoo flash style.** Never photo-real, never 3D, never anime/chibi, never minimalist vector.
- **The hair-to-body ratio is mandatory.** Hair must occupy 65-70% of vertical canvas. If a render comes back with a "tall but balanced" composition, it's wrong.
- **The fur-textured flame is the signature.** Strand linework throughout the flame, fluffy soft edges, white highlight pops at the peaks. Flat decorative flame icons are wrong.
- **The troll face is non-negotiable.** Bulbous nose, big shiny eyes with catchlights, prominent ears, plastic-doll skin sheen, mischievous smirk. If he reads as "human cartoon dad," it's wrong.
- **The wireframes stay thin and minimalist.** Sitting low on the bulbous nose. Never horn-rims, never aviators (those were rejected during iteration).
- **The receded hairline is required.** Pronounced bald forehead, hair erupts from the back two-thirds. He's a middle-aged troll, not a young one.
- **The leather barber smock is the default outerwear.** Tobacco brown, brass rivets, two patch pockets, small red "HAIR" patch on the left chest.
- **The dad outfit underneath is mandatory.** Polo collar at neck, cargo shorts hem peeking, white New Balance, white crew socks. These details must be visible around the smock edges.
- **The belly button peek stays.** Visible where the smock pulls open at the midriff. It's the troll-doll homage.
- **Hank gets new poses, props, scenarios, and hair colors — he doesn't get redesigned.** No facial hair, no new glasses, no new body proportions, no different outfit philosophy. Lock the character, vary the context.
- **No merch.** AI-generated assets only. Hank lives in marketing, social, and in-product surfaces.

---

## 6. Color Palette

| Color | Hex | Role |
|---|---|---|
| **Cream Linen** | `#F4EBD9` | Primary background, paper, "shop wall" |
| **Barber Red** | `#C8102E` | Primary brand red, the pole stripe |
| **Deep Navy** | `#1A2B4A` | Primary text, ink lines, the pole stripe |
| **Bone White** | `#FBF8F1` | Surfaces, cards, the pole stripe |
| **Ocean Teal** | `#2A8B8B` | Secondary accent, tiki greenery |
| **Neon Pink** | `#FF2E88` | Cyberpunk glow, "live" indicator |
| **Electric Cyan** | `#00E5FF` | Cyberpunk glow, capture state |
| **Tiki Wood** | `#8B4513` | Carved details, frames |
| **Hank Orange** | `#F28C3F` | Middle band of Hank's flame hair, warm accents |
| **Sailor Jerry Yellow** | `#F2C14E` | Tattoo highlight, accent only, tip of Hank's flame hair |

### Palette Usage Rules

- **Cream Linen** is the default background. Treat it like the wall of the shop.
- **Barber Red + Deep Navy + Bone White** is the classic trio — these do the heavy lifting in any layout.
- **Ocean Teal + Tiki Wood** add warmth — use for secondary surfaces, tags, decorative elements.
- **Neon Pink + Electric Cyan** are *accents only* — like a single neon sign in a dim shop. Never use them for body text or large fills. They glow; they don't dominate.
- **Sailor Jerry Yellow** is the rarest — reserve for highlights inside tattoo-style illustrations.

### Avoid

- Tech blue (the default HA palette) — we are intentionally not that
- Pure black (#000000) — use Deep Navy instead, it's warmer
- Pure white (#FFFFFF) — use Bone White or Cream Linen, the warm tones matter
- Green (other than Ocean Teal) — clashes with the palette identity

---

## 7. Typography

### Display / Wordmark

A bold slab serif or western-style display font. Hand-painted barbershop window energy. Weathered, confident, doesn't apologize.

**Try:** Recoleta Bold, Playfair Display Black, Rosewood Std, or commission a custom hand-lettered "HAIR" wordmark for the long term.

### Sub-display / Tags / Signage

Stencil or condensed sans-serif. Reserved for short callouts: "OPEN," "WALK-INS WELCOME," "STYLE YOUR HAIR."

**Try:** DIN Condensed, United Sans, Compacta, Bebas Neue.

### UI / Body

Clean modern sans, gets out of the way. The vintage stays in the marketing; the product UI stays accessible and fast.

**Use:** Inter or Geist.

### Accent Script

A bold brush script for occasional flair — captions on illustrations, signed notes from the dev, neon-sign-style copy.

**Try:** Permanent Marker, Cookie, or a Sailor Jerry-style brush script.

---

## 8. Visual Asset System

The brand operates in **three visual modes**, each suited to different surfaces.

### Mode 1: The Photoreal Hero Image (Marketing)

**One cinematic photograph that sells the brand.**

> Nighttime exterior of a small storefront. Above the door, a hand-painted sign reads "HAIR — IR Stylists" in vintage barbershop lettering. A traditional red-white-navy barber pole spins beside the door — the stripes glow faintly with neon cyan and pink. Through the window: shadowy silhouettes of household devices (TV, AC unit, soundbar) sitting in barber chairs. A neon "OPEN" sign glows hot pink in the window. A potted palm beside the door. The street outside is wet pavement reflecting nearby neon signs. Atmospheric, cinematic, slightly noir.

**Tagline overlay:** *Style Your HAIR.*

**Use for:** Website hero, README header, HACS listing thumbnail, launch announcement, large posters.

### Mode 2: Sailor Jerry Tattoo Flash (Social, Merch, Stickers)

**Single devices rendered as American traditional tattoo designs.**

A "flash sheet" featuring devices with classic tattoo treatments:

- TV with a banner reading "MY ONE TRUE LOVE"
- AC unit with classic roses and "COOL FOREVER"
- Ceiling fan rendered like a ship's wheel
- Soundbar with classic swallow birds flanking it
- Mini-split with a hibiscus flower
- Projector with a lighthouse beam
- Remote with a dagger through it reading "FROM YAML"

Each device: bold black outlines, flat fills in brand palette, banners and decorative flourishes. Print-ready as posters and stickers.

**Use for:** Stickers, t-shirts, social posts, secondary marketing, fan art templates.

### Mode 3: Illustrated Barbershop Interiors (In-Product)

**Consistent illustration set for empty states, loading, errors, and success.**

Devices are *customers at the shop* — not characters with hair, but visitors getting service. The HAIR (the styling, the cut, the magic) is what the shop *provides*.

Scene library:

| Surface | Scene |
|---|---|
| Empty device list | Interior of the shop, four empty barber chairs facing a mirror. *"Slow day at the shop. Add your first device."* |
| Add device flow | A device walking through the door, hat in hand. *"Walk-ins welcome. What can we do for you today?"* |
| Capture in progress | Device in chair, cape on, scissors and comb hovering. Barber pole spins faster. Neon "LISTENING" sign glows. |
| Capture success | Device admiring itself in the mirror. *"That'll do."* |
| Capture error | Device in tilted chair, looking confused. Clippers unplugged. *"Something's not right. Take a seat, we'll go again."* |
| All commands learned | Device walking out the door, head held high. Shop bell rings. *"Come back anytime."* |
| Settings page | "Back of house" — supply shelves, cabinets, time clock. Neon "STAFF ONLY" sign. |
| 404 / error | Closed shop, "BE RIGHT BACK" sign in the door. A cat sleeps in the window. |

**Style:** Sailor Jerry-style ink lines, flat warm fills in brand palette. One clear visual idea per scene. Not cluttered.

**Use for:** All in-product illustrations.

### Mode Hierarchy

| Surface | Mode |
|---|---|
| Marketing hero, README, HACS thumbnail | Mode 1 (Photoreal shop window) |
| Social, stickers, t-shirts, fan-shareable assets | Mode 2 (Tattoo flash) |
| In-product UI states | Mode 3 (Illustrated interiors) |
| Logo marks (everywhere) | Logo system (Section 5) |

---

## 9. Voice in Context — Copy Templates

### Website Hero

> # Style Your HAIR.
>
> Capture every IR command. Control every device. Local-first, always.
>
> *Walk-ins welcome.*
>
> [Install on HACS] [See it in action]

### HACS Listing Description

> **HAIR — IR device management for Home Assistant, finally done right.**
>
> Built on HA's native infrared platform (2026.4+). No YAML. No JSON files. No cloud. Just a clean, fast, friendly admin panel for capturing and organizing IR commands.
>
> Walk-ins welcome.

### Release Announcement Format

> 🪒 **HAIR 1.0 — Open for business.**
>
> The shop is officially open. After [N] weeks of soundcheck, HAIR is on HACS.
>
> What's in this release:
> - Capture flow (the cut)
> - Device admin panel (the shop)
> - Remote entity platform (the chair)
>
> Walk in. Get a trim. Walk out with a device that just works.
>
> [Install] · [Docs] · [GitHub]

### About / Team Page

> We're not actually a barbershop.
>
> HAIR is an open-source Home Assistant integration that makes capturing and managing IR commands feel less like data entry and more like getting a haircut.
>
> Built by David Bailey. Available on HACS. MIT licensed. Local-first, always.
>
> *Walk-ins welcome.*

### Empty States (In-Product)

| State | Copy |
|---|---|
| No devices yet | Empty shop. Let's get you a chair. **[Add Device]** |
| No commands captured | Take a seat. Press a button on your remote. **[Start]** |
| No emitters available | Looks like there's no IR hardware connected yet. Set up an ESPHome or Broadlink device first. **[Setup Guide]** |

### Error States (In-Product)

| State | Copy |
|---|---|
| Capture timeout | Missed it. Move closer to the receiver and try again. |
| Hardware error | The chair's empty. Check your IR hardware. |
| Duplicate signal | Looks just like your "[X]" command. Save anyway, or try a different button? |

---

## 10. The Pun Lookup Table

Quick reference for "what do we call X in HAIR-speak?" (Marketing only.)

| Generic term | HAIR-speak |
|---|---|
| The product | The shop |
| Admin panel | The shop floor |
| Settings | Back of house |
| Diagnostics | The mirror (you check yourself out) |
| Installation | Opening day |
| Update | Fresh trim |
| New feature | New service on the menu |
| Bug fix | Cleanup |
| Major version | Grand reopening |
| Documentation | The price list / shop manual |
| GitHub Issues | Customer feedback |
| Contributors | Staff |
| Sponsors | Regulars |
| Beta testers | Walk-ins |
| HACS listing | Storefront |
| Roadmap | Coming soon (window posters) |

**Rule:** Use these in marketing. Translate back to plain language inside the product.

---

## 11. Easter Eggs

Discoverable details that turn a brand into a community.

- **Konami code** in the admin panel — the barber pole on the brand mark spins faster for 5 seconds
- **Time-of-day greeting** — between 9pm and 6am, the welcome text reads *"Open late tonight."*
- **Holiday touches** — the barber pole gets a small ornament in December, sunglasses in July
- **Achievement unlocks** — "First Cut" (capture 1 command), "Regular" (capture 50), "Master Stylist" (set up 10+ devices)
- **The cat** — a small sleeping cat illustration appears on the 404 page. She has a name. She is canon.
- **"Compliment" command** — if a user creates a custom command literally named "Compliment," the test button briefly shows a sparkle animation
- **Hidden device type "Cowbell"** — does nothing, but exists. Captures one command: *"More."*

---

## 12. What This Brand Is Not

To clarify the edges:

- **Not corporate.** No SaaS landing page energy. No stock photos.
- **Not nostalgic LARP.** The cyberpunk neon makes sure we don't read as a Pinterest mood board.
- **Not chaotic.** The system is consistent — the variation lives inside the system, not on top of it.
- **Not exclusive.** "Walk-ins welcome" means everyone — power users, newcomers, kids running their first HA setup.
- **Not the salon.** Salon implies precious. We're the barbershop. We work for a living.
- **Not the band.** No hair metal puns. No album metaphors. The shop is the world.

---

## 13. Asset Wishlist (To Generate / Commission)

Tracking what we need to actually produce:

### Logo system
- [ ] Master logo (barber pole + wordmark) — *iterating on prompt now*
- [ ] Wordmark only
- [ ] Pole only (favicon-ready)
- [ ] Shop sign (full "HAIR — IR Stylists" hand-painted)
- [ ] Tattoo flash mark (single device, secondary)

### Marketing
- [ ] Hero shop window photograph
- [ ] Tattoo flash sheet (8 devices on one poster)
- [ ] Sticker pack (single-device tattoos)
- [ ] One t-shirt design
- [ ] Social card template
- [ ] HACS thumbnail

### In-product
- [ ] Empty device list illustration
- [ ] Add device flow illustration
- [ ] Capture in progress (animated)
- [ ] Capture success
- [ ] Capture error
- [ ] All commands learned
- [ ] Settings / back of house
- [ ] 404 / closed shop with cat

### Type & color
- [ ] Final wordmark typeface decision
- [ ] Hex palette tested for accessibility (WCAG AA contrast)
- [ ] Dark mode palette variant

---

## 14. Versioning

This document evolves. Track major changes here.

| Version | Date | Changes |
|---|---|---|
| v1 | 2026-05-08 | Initial branding doc. Locks: Neo-Tiki Barbershop direction, "Style Your HAIR" tagline, "Walk-ins welcome" supporting line, color palette, logo prompt v1. Pending: pole prompt iteration with David. |
| v1.1 | 2026-05-08 | **Logo prompt v2 LOCKED.** Updated Section 5 with the canonical master prompt (HAIR-dominant banner, pole as supporting element, tiki + hibiscus base). Added four named variant prompts (Wordmark-Only, Pole-Only, Horizontal Lockup, Shop Sign) for the full asset family. The "BARBER SHOP" subtitle is dropped from the primary mark to keep the wordmark pure. |
| v1.2 | 2026-05-08 | **Hairy Hank LOCKED as mascot.** Added new Section 5.5 with full character design, locked master prompt, 10-scenario library, wardrobe variants, and usage rules. Hank's hair uses Sailor Jerry tattoo color shading (red→orange→yellow flame) as the default; flame color shifts function as a brand-wide mood indicator across scenarios. Added **Hank Orange (#F28C3F)** to the color palette as the middle band of the flame. AI-generated only, no merch posture confirmed. Pin and pole logo system unchanged — Hank is the *mascot*, the wordmark + pole is the *logo*. |
| v1.3 | 2026-05-08 | **Hank v8 LOCKED as final mascot.** After 8 iteration rounds, the canonical Hank is locked: middle-aged plastic troll doll with a pronounced receded hairline, towering 65-70%-of-canvas Sailor Jerry flame hair (with fluffy fur strand texture), thin gold wireframe glasses on a bulbous nose, working as a barbershop barber in a tobacco-brown leather smock with brass rivets and a small red "HAIR" patch — dressed underneath like a suburban dad on a Saturday (polo collar, cargo shorts, white New Balance, crew socks all visible peeking around the smock). Three-act visual storytelling: hair = "HOLY HAIR," middle = "he's a barber," bottom = "wait, he's a dad too." All scenarios and wardrobe variants updated to reference v8 as the locked baseline. Created `branding/assets/` folder with README pointing to the canonical reference render. Usage rules expanded to lock the hair-to-body ratio, fur texture, troll face, wireframes, hairline, smock, dad-outfit underneath, and belly-button peek as non-negotiable elements. |

---

*Branding by David Bailey. Opinions by an old-school barber who's been to the future.*

*Walk-ins welcome.*
