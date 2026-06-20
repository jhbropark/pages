# APOD → namecode daily pipeline

Integrates the **NASA APOD API** ([nasa/apod-api](https://github.com/nasa/apod-api))
with the namecode generative pipeline. One command turns the Astronomy Picture
of the Day into an on-brand monochrome artwork:

```
APOD API  ->  brief (work name + prompt)  ->  Krea image  ->  duotone + mono label
```

## Setup

```bash
pip install requests Pillow
# JetBrains Mono font for the label (or set NAMECODE_FONT):
curl -sL -o /tmp/fnt/JetBrainsMono.ttf \
  https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Regular.ttf

export NASA_API_KEY=...      # get one free at https://api.nasa.gov (DEMO_KEY works for light use)
export KREA_API_KEY=...
```

## Usage

```bash
python apod_namecode.py                    # today's APOD -> finished post
python apod_namecode.py --date 2026-06-20  # a specific date
python apod_namecode.py --dry-run          # print the brief only (no Krea call)
python apod_namecode.py --subject "lunar occultation of Venus" --name OCCULTATION
                                           # skip NASA, drive Krea directly
```

Output: `namecode_apod_<date>.png` (1080×1080) plus a JSON brief on stdout
(`work_name`, `label`, `prompt`, `source`).

## How it maps APOD → namecode

| step | logic |
|------|-------|
| work name | salient words of the APOD title, uppercased & dotted (`Daytime Moon Meets Evening Star` → `MOON.STAR`; override with `--name`) |
| prompt | `build_prompt()` injects the title + a trimmed explanation into the fixed namecode dark-monochrome style string |
| value | deterministic `NN.NNN` from `sha1(date:name)` (stable per day) |
| render | Krea `flux` (swap with `--model imagen-4 / nano-banana`) |
| finish | grayscale → duotone (`#0C0C0C`/`#F5F5F3`) + top-left mono label |

## Config (env)

| var | default | notes |
|-----|---------|-------|
| `NASA_API_KEY` | `DEMO_KEY` | api.nasa.gov key |
| `NASA_APOD_BASE` | `https://api.nasa.gov/planetary/apod` | point at a **self-hosted** [nasa/apod-api](https://github.com/nasa/apod-api) (e.g. `http://localhost:5000/v1/apod`) to avoid rate limits |
| `KREA_API_KEY` | — | required unless `--dry-run` |
| `KREA_BASE` | `https://api.krea.ai` | |
| `NAMECODE_FONT` | `/tmp/fnt/JetBrainsMono.ttf` | label font |

## Self-hosting nasa/apod-api

```bash
git clone https://github.com/nasa/apod-api && cd apod-api
pip install -r requirements.txt && python application.py   # serves /v1/apod on :5000
export NASA_APOD_BASE=http://localhost:5000/v1/apod
```

## Environment note

In Claude Code on the web, `api.nasa.gov` / `apod.nasa.gov` must be added to the
**network egress allowlist** for the NASA half to run; the Krea half
(`api.krea.ai`) already works. `--subject` bypasses NASA entirely and was used to
verify the pipeline end-to-end (see `apod_pipeline_test.png`).
