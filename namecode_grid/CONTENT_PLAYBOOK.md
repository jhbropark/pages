# namecode — Content Playbook (@namecode_original)

*Operationalizes `.agents/product-marketing.md` and the brand rules in
`CLAUDE.md` into a repeatable posting system. Built with the `social` +
`content-strategy` skills. Read `product-marketing.md` first; brand rules in
`CLAUDE.md` override anything here.*

*Last updated: 2026-07-15*

---

## North Star

**Phase-1 goal:** grow to **10K followers** (then editions/commissions — see
the business model in `product-marketing.md`).
**Primary signals, in order:** **sends → saves → non-trivial comments →
follows.** Sends + saves are the 2026 IG ranking signals we design every post
around. Likes are vanity; do not optimize for them.

**Positioning in one line:** *the only place where today's actual sky becomes a
consistent, cinematic artwork you can save, send, and revisit as a series.*
The wedge = daily-APOD demand (proven by @astronomypicturesdaily ~865K) ×
studio-tier visual authorship (fuse\*/Zhestkov/Anadol) at a daily cadence
neither side offers.

---

## Content Pillars

Five pillars. Percentages are a rolling 20-post cycle, not a daily rule.

| Pillar | Share | What it is | Primary format |
|--------|-------|-----------|----------------|
| **Daily Sky** | 55% | The APOD-of-the-day work + label. The core ritual. | Feed 4:5 |
| **Explain the Sky** | 20% | "What is this?" — decode the phenomenon (occultation, zodiacal light, magnitude). Answers the #1 comment type and earns saves. | Carousel 8–10 |
| **In Motion** | 15% | Highlight reels — particle loops of a standout work. Highest-reach format. | Reel 9:16 |
| **The System** | 7% | Behind the method: how a sky becomes code, the label convention, the CUBE trilogy. Builds authorship + the "serious medium" JTBD. | Carousel / Reel |
| **The Archive** | 3% | Look-backs — "this week in the sky," monthly grids, most-saved works. Reinforces the collectible-series value. | Carousel |

**Why these:** they map 1:1 to the three Jobs-to-be-Done (daily awe →
Daily Sky; something smart to save/send → Explain + Archive; code as a serious
medium → The System + In Motion).

---

## Format Role Separation

Per `CLAUDE.md` — each format has one job, don't blur them:

- **Feed (Daily Sky):** 4:5 portrait **1080×1350**. Mono label top-left safe
  zone. The permanent, dated archive tile.
- **Carousel (Explain / System / Archive):** 4:5, **8–10 slides**. Slide 1 sets
  the ratio and carries the hook. Built for **saves**.
- **Reel (In Motion):** 9:16 **1080×1920**, **30–90s**, loop/stitch the Krea
  seed in an editor. Built for **reach + sends**.
- **Story (support, not a pillar):** re-share the day's feed post, polls
  ("comet or meteor?"), "guess the magnitude." Drives profile visits.

---

## Caption System

The current template is solid but runs identically every day. Keep the
skeleton, **rotate the hook**, and **answer the phenomenon** — research shows
"What is this?" is a top art-comment type, and naming the phenomenon converts
curiosity into a save.

### Rules (from CLAUDE.md + customer-language research)
- **Front-load the hook** in the first ~125 chars (before the "more" fold).
- **Lead with the sky + the data, never the AI tooling** — labeling work
  "AI-made" measurably lowers perceived awe. Medium is not the message.
- **3–5 hashtags.** Not 30. `HASHTAGS_BASE` + one topical tag per work.
- English only. No emoji walls (the single ✦ is on-brand; keep it to one).
- Every caption ends on a **send/save CTA**.

### Skeleton
```
<HOOK — rotate, ≤125 chars, front-loaded>
<APOD title>. <one-line "what it is" — the phenomenon decoded>

Source: NASA APOD · <date>. · <label value, e.g. mag -4.2>
<save/send CTA>

#namecode #newmediaart #generativeart #creativecodeart #<work-topic>
```

### Hook rotation (cycle, don't repeat two days running)
- **Ritual:** "Today's sky, rendered in code."
- **Curiosity / phenomenon:** "Two bands crossed the desert last night. Only
  one is our galaxy."
- **Data-forward:** "Magnitude −4.2. Bright enough to cast a shadow."
- **Contrarian/awe:** "You looked up and missed it. Here it is, slowed down."
- **Series:** "Sky no. 214 in the archive."

### Example — upgrading 2026-07-06 (COMET / "Dueling Bands over the Atacama")
> **Before:** `COMET — today's sky, rendered in code. / Dueling Bands over the
> Atacama Desert. / Source... / Save this sky ✦ send it to someone who looks
> up.`
>
> **After (curiosity hook + decoded + data):**
> `Two glowing bands over the Atacama — and only the left one is the Milky Way.
> The right is zodiacal light: sunlight scattered off dust in our own solar
> system. / Dueling Bands over the Atacama Desert · NASA APOD 2026-07-06. /
> Save this sky ✦ send it to someone who looks up. /
> #namecode #newmediaart #generativeart #creativecodeart #zodiacallight`

---

## Hashtag Strategy

- **Base (every post):** `#namecode #newmediaart #generativeart
  #creativecodeart`
- **+1 topical** per work: the phenomenon (`#zodiacallight`, `#occultation`,
  `#milkyway`) — this is the discovery lever, so make it *accurate to the
  subject*, not the (sometimes mismatched) work name.
- Rotate a **reach tag** occasionally on reels: `#satisfying`, `#spaceart`.
- Never exceed 5. Never reuse a stale 30-tag block.

---

## Weekly Cadence

Daily feed is non-negotiable (it's the ritual + the archive). Layer the other
formats on top:

| Day | Feed (Daily Sky) | Extra |
|-----|------------------|-------|
| Mon | ✓ | — |
| Tue | ✓ | **Reel** (In Motion — best of last week) |
| Wed | ✓ | **Carousel** (Explain the Sky) |
| Thu | ✓ | Story poll |
| Fri | ✓ | **Reel** or **The System** carousel |
| Sat | ✓ | — |
| Sun | ✓ | **Archive** carousel ("this week in the sky") |

**Batch weekly (~2h):** the pipeline (`apod_namecode.py`) auto-produces the
daily feed; spend the batch time on the 2 reels + 1–2 carousels + rotating the
week's caption hooks.

---

## Growth Engine (toward 10K)

Content alone won't compound — pair it with distribution.

### Daily engagement routine (~20 min)
1. Reply to **every** comment on our posts (esp. answer "what is this?" — it
   trains the algorithm and models the behavior).
2. Leave 5–10 substantive comments on target accounts (below).
3. Reply to 2–3 Stories from the space/art community.

### Accounts to engage (from the competitive landscape)
- **Demand pool:** @astronomypicturesdaily, @nasa, @nasa_apod and their
  commenters — this is exactly our audience, already gathered.
- **Peer/aspirational:** @refikanadol, Zhestkov, fuse\*, generative-art
  hashtag leaders — comment with craft, not promotion.
- **Collab targets (Phase-1.5):** mid-size creative-coding / astro-art
  accounts open to a "sky of the week" cross-post or a shared reel.

### Compounding loops
- **Saveable carousels** → saves → reach → follows.
- **"Answer the phenomenon" replies** → comment threads → non-trivial-comment
  signal.
- **Monthly grid** (Archive) → shows the series is worth following for the
  *collection*, not just one post.

---

## Metrics Loop

- **Weekly:** run `python namecode_grid/ig_insights.py` → snapshots follower
  count + per-post saves/sends/reach into `namecode_grid/metrics/`. Read the
  top-5 by saves+sends.
- **Ask each week:** which 3 posts got the most *sends*? What did their hooks /
  phenomena have in common? Do more of that. Which format is pulling reach?
- **Log the headline numbers** into `product-marketing.md` → Goals.
- As comments accumulate, harvest verbatim audience phrases into
  `product-marketing.md` → Customer Language.

---

## Pre-Publish QA Checklist

- [ ] **Work name matches the actual subject.** *(Known drift: 07-05 "Iapetus"
      was labeled METEOR; 07-06 "Dueling Bands/Milky Way" was labeled COMET.
      The topical hashtag and the decoded line MUST describe the real
      phenomenon even if the auto-name is off.)*
- [ ] Label value is a **real astronomical figure** from the APOD text (not a
      hash fallback) — `apod_namecode.py::astro_value()`.
- [ ] Hook is front-loaded (≤125 chars) and **not** identical to yesterday's.
- [ ] Caption **decodes the phenomenon** (answers "what is this?").
- [ ] Leads with the sky/data, **not** the AI tooling.
- [ ] 3–5 hashtags; topical tag is accurate to the subject.
- [ ] Correct format spec (feed 1080×1350 / carousel 4:5 8–10 / reel 9:16
      30–90s).
- [ ] Red `#9B1313` under 10% (currently: absent).
- [ ] Ends on a send/save CTA.
- [ ] NASA APOD credited + dated.

---

## Related

- `.agents/product-marketing.md` — positioning, audience, competitive landscape
- `CLAUDE.md` — brand rules (override this doc on conflict)
- `.claude/skills/social`, `.claude/skills/content-strategy`,
  `.claude/skills/copywriting`, `.claude/skills/marketing-psychology`
- `namecode_grid/ig_insights.py` — metrics snapshots
