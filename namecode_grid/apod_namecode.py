#!/usr/bin/env python3
"""
APOD -> namecode daily artwork pipeline.

Chains the NASA APOD API (https://github.com/nasa/apod-api) into the namecode
generative pipeline:

    APOD API  ->  brief (work name + prompt)  ->  Krea image  ->  duotone + mono label

Both endpoints are plain HTTP:
  - NASA APOD : https://api.nasa.gov/planetary/apod  (or a self-hosted nasa/apod-api)
  - Krea      : https://api.krea.ai/generate/image/...

Env vars:
  NASA_API_KEY   NASA key (default: DEMO_KEY)
  NASA_APOD_BASE APOD endpoint (default: https://api.nasa.gov/planetary/apod)
                 Point this at a self-hosted nasa/apod-api, e.g. http://localhost:5000/v1/apod
  KREA_API_KEY   Krea key (required unless --dry-run)
  KREA_BASE      Krea API base (default: https://api.krea.ai)

Usage:
  python apod_namecode.py                      # today's APOD -> finished post
  python apod_namecode.py --date 2026-06-20    # a specific date
  python apod_namecode.py --dry-run            # print brief only (no Krea call)
  python apod_namecode.py --subject "lunar occultation of Venus" --name OCCULTATION
                                               # skip NASA, drive Krea directly
"""
import argparse, hashlib, io, os, re, sys, time, json
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

PAPER = (245, 245, 243)
BLACK = (12, 12, 12)
FONT = os.environ.get("NAMECODE_FONT", "/tmp/fnt/JetBrainsMono.ttf")

STOPWORDS = {
    "the", "a", "an", "of", "and", "in", "on", "to", "from", "with", "at", "by",
    "meets", "near", "over", "as", "for", "its", "is", "are", "this", "that",
}


# ---------------------------------------------------------------- NASA APOD
def get_apod(date=None):
    base = os.environ.get("NASA_APOD_BASE", "https://api.nasa.gov/planetary/apod")
    params = {"api_key": os.environ.get("NASA_API_KEY", "DEMO_KEY"), "thumbs": "true"}
    if date:
        params["date"] = date
    r = requests.get(base, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def derive_name(title):
    """Turn an APOD title into a namecode work name, e.g.
    'Daytime Moon Meets Evening Star' -> 'MOON.STAR'."""
    words = [w for w in re.findall(r"[A-Za-z]+", title) if w.lower() not in STOPWORDS]
    words = sorted(set(words), key=lambda w: (-len(w), title.lower().index(w.lower())))[:2]
    words = sorted(words, key=lambda w: title.lower().index(w.lower()))
    return ".".join(w.upper() for w in words) or "APOD"


def sim_value(seed):
    h = int(hashlib.sha1(seed.encode()).hexdigest(), 16)
    return f"{h % 100:02d}.{h // 100 % 1000:03d}"


def build_prompt(subject, explanation=""):
    snippet = (explanation or "").strip().replace("\n", " ")
    if len(snippet) > 200:
        snippet = snippet[:200].rsplit(" ", 1)[0]
    return (
        f"Cinematic dark monochrome generative art inspired by {subject}. "
        f"{snippet} "
        "Rendered as fine white particles and light filaments on a pure black "
        "background, volumetric, dramatic, monochrome white on black, lots of "
        "negative space, high detail."
    )


# ---------------------------------------------------------------- Krea
def krea_generate(prompt, width=1024, height=1024, model="flux"):
    base = os.environ.get("KREA_BASE", "https://api.krea.ai")
    key = os.environ["KREA_API_KEY"]
    body = {"prompt": prompt, "width": width, "height": height}
    # model -> path map (subset; matches the patched krea-mcp-server fork)
    path = {"flux": "bfl/flux-1-dev", "imagen-4": "google/imagen-4",
            "nano-banana": "google/nano-banana-pro"}.get(model, "bfl/flux-1-dev")
    r = requests.post(f"{base}/generate/image/{path}", json=body,
                      headers={"Authorization": f"Bearer {key}"}, timeout=60)
    r.raise_for_status()
    return r.json()["job_id"]


def krea_wait(job_id, timeout=120):
    base = os.environ.get("KREA_BASE", "https://api.krea.ai")
    key = os.environ["KREA_API_KEY"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get(f"{base}/jobs/{job_id}",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        r.raise_for_status()
        j = r.json()
        if j["status"] == "completed":
            return j["result"]["urls"][0]
        if j["status"] == "failed":
            raise RuntimeError(f"Krea job failed: {j}")
        time.sleep(3)
    raise TimeoutError("Krea job timed out")


# ---------------------------------------------------------------- compose
def compose(img_bytes, name, value, out, size=1080):
    g = ImageOps.autocontrast(
        Image.open(io.BytesIO(img_bytes)).convert("L").resize((size, size)), cutoff=1)
    im = ImageOps.colorize(g, black=BLACK, white=PAPER).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    label = f"namecode - {name} | {value}"
    f = ImageFont.truetype(FONT, max(20, size // 36))
    tw = d.textlength(label, font=f)
    x, y, pad = 34, 34, 14
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + f.size + 22], radius=6, fill=(18, 18, 18, 170))
    d.text((x + pad, y + 11), label, font=f, fill=PAPER)
    im.save(out)
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--subject", help="skip NASA; use this subject directly")
    ap.add_argument("--name", help="override work name")
    ap.add_argument("--model", default="flux")
    ap.add_argument("--dry-run", action="store_true", help="print brief, no generation")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.subject:
        subject, explanation, date, src_url = a.subject, "", a.date or "manual", None
        title = a.subject
    else:
        apod = get_apod(a.date)
        if apod.get("media_type") != "image":
            print(f"[skip] APOD {apod.get('date')} is {apod.get('media_type')}, not an image.",
                  file=sys.stderr)
        title = apod.get("title", "APOD")
        subject = title
        explanation = apod.get("explanation", "")
        date = apod.get("date", a.date or "today")
        src_url = apod.get("hdurl") or apod.get("url")

    name = a.name or derive_name(title)
    value = sim_value(f"{date}:{name}")
    prompt = build_prompt(subject, explanation)
    brief = {"date": date, "apod_title": title, "work_name": name,
             "label": f"namecode - {name} | {value}", "source": src_url, "prompt": prompt}
    print(json.dumps(brief, ensure_ascii=False, indent=2))

    if a.dry_run:
        return
    job = krea_generate(prompt, model=a.model)
    url = krea_wait(job)
    img = requests.get(url, timeout=60).content
    out = a.out or f"namecode_apod_{date}.png"
    compose(img, name, value, out)
    print(f"[ok] saved {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
