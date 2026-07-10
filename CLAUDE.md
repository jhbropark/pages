# Project memory — namecode

Working notes Claude should honor across sessions for the **namecode** brand
assets (mostly under `namecode_grid/`).

## Brand
- **Direction:** dark, cinematic (FUSE\*-style: white particles on black).
- **Palette:** `#1A1A1A` Ink Black (base) · `#FAFAF8` Paper White (particles/text)
  · `#9B1313` Signature Red — **red is optional and must stay well under 10%**
  of any composition (currently removed from the grid entirely).
- **Font:** JetBrains Mono (monospace) — reinforces the "translate into code" identity.
- **Content language:** **English only** (all captions, labels, copy).
- **Flagship:** CUBE as a living trilogy (CUBE I / II / III).

## Artwork label convention
Format: `namecode - <WORK_NAME> | <value>` (top-left, mono, FUSE\*-style).

- **`<value>` = real astronomical data** (decision: option 🅓). Pull a genuine
  measured quantity from the day's APOD text — e.g. `mag -4.2`, `4.2 ly`,
  `12 deg`. Implemented in `apod_namecode.py::astro_value()`; falls back to a
  deterministic hash only when no astronomical figure is found.
- Do **not** use meaningless decorative numbers for the value.

## Daily content
- Source of daily inspiration: **NASA APOD** (https://apod.nasa.gov/apod/).
- Pipeline: `apod_namecode.py` (APOD → Krea → duotone + mono label) →
  `ig_publish.py` (Meta Graph API → @namecode_original).

## Instagram formats (2026) — format role separation
- **Feed (daily APOD):** 4:5 portrait **1080×1350** (`apod_namecode.py`, default `FEED_SIZE`). Mono label top-left safe zone.
- **Carousel (explainer):** 4:5, **8–10 slides** (`carousel.py`). First slide sets the ratio.
- **Reel (daily):** 9:16 **1080×1920**, **30–90s**, built by `krea_reel.py` + `reel_fx.py`
  as the **DECODE 3-act structure**: glyph-noise decode hook (~2.5s, label typewriter +
  value count-up) → Kling image-to-video motion (date-seeded motion library, never the
  same move twice in a row) → glitch beats at loop boundaries → 2s labeled end card.
  Hooks are deterministic PIL/ffmpeg — never rely on the video model for the hook.
- **Caption:** front-load the hook in the first ~125 chars; **3–5 hashtags** (`HASHTAGS_BASE` + one per-work topical tag). Not 30.
- Optimize for **sends + saves** (the top 2026 signals), then non-trivial comments.
