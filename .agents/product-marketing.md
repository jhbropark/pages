# Product Marketing Context — namecode

*Last updated: 2026-07-07*

> Scope: this document covers the **namecode** art brand (@namecode_original)
> only. The `content/` directory belongs to a separate brand (bbbb.beauty B2B)
> and is intentionally out of scope here.
> Items marked ⚠️ are assumptions drafted from the codebase — confirm or correct.

## Product Overview
**One-liner:** namecode translates the universe into code — the day's sky,
rendered as dark cinematic generative art, every day.

**What it does:** namecode is a daily generative-art project. Each day, NASA's
Astronomy Picture of the Day (APOD) is translated into an on-brand monochrome
artwork — fine white particles and light filaments on pure black — via an
automated pipeline (APOD API → Krea render → duotone + mono data label) and
published to Instagram @namecode_original. Each work carries a FUSE*-style
label with a real astronomical value (`namecode - COMET | mag -4.2`).

**Product category:** new media / generative art (audience discovers it via
#generativeart, #newmediaart, #creativecoding).

**Product type:** art brand / daily content project (Instagram-first).

**Business model:** ⚠️ audience-building phase; no monetization implemented in
the repo. Plausible later: prints, commissions, exhibitions, digital editions.

## Target Audience
**Primary audience:** generative art / new media art enthusiasts on Instagram;
creative coders (TouchDesigner, Processing, shader communities); space and
astronomy lovers who follow APOD-style content; design-minded people drawn to
minimal, dark, cinematic aesthetics.

**Jobs to be done:**
- Give me a moment of daily awe — today's sky as art, not a headline.
- Supply aesthetic, intelligent content worth *saving* and *sending* to a
  friend who looks up.
- Show me what code + AI can do as a serious artistic medium.

**Use cases:**
- Daily feed follow (4:5 APOD artwork with mono data label)
- Saves as mood/reference boards for designers and artists
- Sends: "send it to someone who looks up" — shareable cosmic moments
- Carousels: explainers on the process/series (e.g. CUBE trilogy)
- Reels: 30–90s particle loops from the Krea seed

## Problems & Pain Points
(For an art brand this is the *audience's* tension, not a business pain.)

**Core tension:** astronomy content is usually photographic and news-like;
generative art is usually abstract and placeless. There is little that fuses
*real, dated astronomical events* with a strict, collectible visual system.

**Why alternatives fall short:**
- Raw APOD reposts: informative but not aesthetic, no authorship.
- Generic AI-art accounts: prolific but inconsistent, no data grounding, no
  daily ritual.
- Classic generative artists: strong systems but rarely tied to *today's sky*.

**Emotional pull:** awe, calm, "the universe in my pocket," pride in sharing
something smart and beautiful.

## Competitive Landscape
⚠️ Drafted from category knowledge — validate against accounts you actually
benchmark.

**Direct:** daily generative/AI-art Instagram accounts — fall short on data
grounding and daily editorial concept.
**Secondary:** astronomy photo accounts (APOD reposters, NASA fan pages) —
fall short on visual authorship and brand system.
**Indirect:** FUSE*-style studio accounts (audiovisual/particle art) — post
infrequently; namecode's edge is the *daily* ritual.

## Differentiation
**Key differentiators:**
- **Real data, every piece:** the label value is a genuine measured quantity
  from that day's APOD (`mag -4.2`, `4.2 ly`) — never decorative numbers.
- **Daily ritual with provenance:** every work is dated and sourced (NASA APOD
  credit in caption) — a collectible archive of skies.
- **Strict visual system:** Ink Black `#1A1A1A` / Paper White `#FAFAF8`,
  JetBrains Mono labels, red `#9B1313` ≤10% and currently absent — instantly
  recognizable grid.
- **Automated but authored:** a reproducible pipeline (APOD → Krea → duotone +
  label) with human curation on top.

**Why customers choose us:** the only place where *today's actual sky* becomes
a consistent, cinematic artwork you can save, send, and revisit as a series.

## Anti-persona
People seeking scientific-photo accuracy or astro-photography tutorials;
followers who want colorful/maximalist AI art; anyone expecting Korean-language
content (namecode is English-only).

## Customer Language
⚠️ No verbatim audience quotes collected yet — mine IG comments/DMs and update.

**Words to use:** rendered in code · today's sky · particles · signal ·
translate · monochrome · negative space · orbit · magnitude · archive · series.
**Words to avoid:** "AI-generated" as the lead (medium, not message);
hype-words (stunning!, mind-blowing); emoji walls; more than 3–5 hashtags;
decorative fake numbers.

**Glossary:**
| Term | Meaning |
|------|---------|
| work name | Uppercased dotted title from APOD (`MOON.STAR`, `OCCULTATION`) |
| value | Real astronomical figure from the APOD text, shown in the label |
| label | `namecode - <WORK_NAME> \| <value>`, top-left, JetBrains Mono |
| CUBE I/II/III | Flagship living trilogy of works |

## Brand Voice
**Tone:** calm, precise, cinematic — an observatory logbook, not a hype feed.
**Style:** short declarative lines; data-flavored; English only.
**Personality:** minimal · cosmic · engineered · quietly poetic · consistent.
**Caption pattern (current):** `<WORK> — today's sky, rendered in code.` +
APOD title + `Source: NASA APOD · <date>` + save/send CTA + 3–5 hashtags
(`#namecode #newmediaart #generativeart #creativecodeart` + one topical tag).

## Proof Points
- Unbroken daily archive (briefs + captions + artworks in `namecode_grid/daily/`)
- Every piece traceable to a NASA APOD source and date
- Multi-format system already live: feed 1080×1350, carousel 8–10 slides,
  reels 9:16 30–90s
- ⚠️ Follower/engagement metrics not tracked in repo — add once available.

## Goals
**Business goal:** ⚠️ grow @namecode_original into a recognized generative-art
brand (audience first; monetization later).
**Conversion action:** follows; **sends + saves** are the primary engagement
signals to optimize (2026 IG algorithm), then non-trivial comments.
**Current metrics:** ⚠️ unknown — pull from IG Insights and record here.
