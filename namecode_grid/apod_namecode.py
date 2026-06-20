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

# Instagram 2026 formats
FEED_SIZE = (1080, 1350)      # 4:5 portrait — daily APOD feed posts
CAROUSEL_SIZE = (1080, 1350)  # 4:5 — explainer carousels (8-10 slides)
REEL_SIZE = (1080, 1920)      # 9:16 — highlight reels

STOPWORDS = {
    "the", "a", "an", "of", "and", "in", "on", "to", "from", "with", "at", "by",
    "meets", "near", "over", "as", "for", "its", "is", "are", "this", "that",
}


# ---------------------------------------------------------------- config
def load_dotenv(path=None):
    """Minimal, dependency-free .env loader (namecode_grid/.env by default)."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------- NASA APOD
def get_apod(date=None):
    base = os.environ.get("NASA_APOD_BASE", "https://api.nasa.gov/planetary/apod")
    params = {"api_key": os.environ.get("NASA_API_KEY", "DEMO_KEY"), "thumbs": "true"}
    if date:
        params["date"] = date
    r = requests.get(base, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# Recognizable astronomical phenomena make punchier work names than generic
# title words; prefer them when present in the title or explanation.
# (stem matched with a word boundary -> clean display name; stems catch plurals)
PHENOMENA = [
    ("occultation", "OCCULTATION"), ("eclipse", "ECLIPSE"), ("transit", "TRANSIT"),
    ("conjunction", "CONJUNCTION"), ("opposition", "OPPOSITION"), ("comet", "COMET"),
    ("supernova", "SUPERNOVA"), ("nebula", "NEBULA"), ("galax", "GALAXY"),
    ("aurora", "AURORA"), ("eruption", "ERUPTION"), ("meteor", "METEOR"),
    ("solstice", "SOLSTICE"), ("equinox", "EQUINOX"), ("corona", "CORONA"),
    ("prominence", "PROMINENCE"), ("halo", "HALO"), ("nova", "NOVA"),
    ("cluster", "CLUSTER"),
]


def derive_name(title, explanation=""):
    """Turn an APOD into a namecode work name. Prefer a known phenomenon term
    (e.g. 'OCCULTATION'); otherwise fall back to the salient title words
    ('Daytime Moon Meets Evening Star' -> 'MOON.STAR')."""
    blob = f"{title} {explanation}".lower()
    for stem, name in PHENOMENA:
        if re.search(rf"\b{stem}", blob):
            return name
    words = [w for w in re.findall(r"[A-Za-z]+", title) if w.lower() not in STOPWORDS]
    words = sorted(set(words), key=lambda w: (-len(w), title.lower().index(w.lower())))[:2]
    words = sorted(words, key=lambda w: title.lower().index(w.lower()))
    return ".".join(w.upper() for w in words) or "APOD"


def sim_value(seed):
    h = int(hashlib.sha1(seed.encode()).hexdigest(), 16)
    return f"{h % 100:02d}.{h // 100 % 1000:03d}"


# Label value = real astronomical data pulled from the APOD text (option D).
# Ordered by preference; first match wins. Falls back to sim_value().
ASTRO_PATTERNS = [
    (r"magnitude[s]?\s+(?:of\s+)?(-?\d+(?:\.\d+)?)", "mag {0}"),
    (r"(-?\d+(?:\.\d+)?)\s*magnitude", "mag {0}"),
    (r"(\d+(?:\.\d+)?)\s*(million|billion)?\s*light[- ]?years?", "{0} ly"),
    (r"(\d+(?:\.\d+)?)\s*arc\s*minutes?", "{0}'"),
    (r"(\d+(?:\.\d+)?)\s*degrees?", "{0} deg"),
    (r"(\d+(?:\.\d+)?)\s*(?:million\s*)?km\b", "{0} km"),
    (r"(\d+(?:\.\d+)?)\s*AU\b", "{0} AU"),
    (r"(\d+(?:\.\d+)?)\s*[- ]?hours?\b", "{0} hr"),
    (r"hour[\s-]?long", "1 hr"),
]


def astro_value(text):
    """Return a real measured quantity from the APOD explanation, or None."""
    for pat, fmt in ASTRO_PATTERNS:
        m = re.search(pat, text or "", re.I)
        if m:
            return fmt.format(m.group(1)) if "{0}" in fmt else fmt
    return None


# Instagram 2026: 3-5 targeted hashtags (not 30). 4 base + 1 per-work topical.
HASHTAGS_BASE = ["#namecode", "#newmediaart", "#generativeart", "#creativecodeart"]


def topical_tag(name):
    word = re.split(r"[.\s]", name)[0].lower()
    return "#" + re.sub(r"[^a-z0-9]", "", word)


def build_caption(brief):
    """Front-load the hook in the first ~125 chars (visible before '…more');
    nudge sends + saves (the top 2026 signals)."""
    tags = " ".join(HASHTAGS_BASE + [topical_tag(brief["work_name"])])
    return (
        f"{brief['work_name']} — today's sky, rendered in code.\n"
        f"{brief['apod_title']}.\n\n"
        f"Source: NASA APOD · {brief['date']}.\n"
        f"Save this sky ✦ send it to someone who looks up.\n\n"
        f"{tags}"
    )


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
def krea_generate(prompt, width=1024, height=1280, model="flux"):  # 4:5 portrait
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
def compose(img_bytes, name, value, out, size=FEED_SIZE):
    """Compose a finished post. Default 4:5 (1080x1350) for the IG feed."""
    W, H = size
    g = ImageOps.autocontrast(Image.open(io.BytesIO(img_bytes)).convert("L"), cutoff=1)
    g = ImageOps.fit(g, (W, H), method=Image.LANCZOS)          # cover-fit to 4:5
    im = ImageOps.colorize(g, black=BLACK, white=PAPER).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    label = f"namecode - {name} | {value}"
    f = ImageFont.truetype(FONT, max(22, W // 34))
    tw = d.textlength(label, font=f)
    x, y, pad = 40, 40, 14                                     # top-left safe zone
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + f.size + 22], radius=6, fill=(18, 18, 18, 170))
    d.text((x + pad, y + 11), label, font=f, fill=PAPER)
    im.save(out)
    return out


# ---------------------------------------------------------------- main
def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--subject", help="skip NASA; use this subject directly")
    ap.add_argument("--name", help="override work name")
    ap.add_argument("--model", default="flux")
    ap.add_argument("--dry-run", action="store_true", help="print brief, no generation")
    ap.add_argument("--out")
    ap.add_argument("--brief-out", help="write the brief JSON to this path")
    ap.add_argument("--caption-out", help="write the post caption to this path")
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

    name = a.name or derive_name(title, explanation)
    value = astro_value(explanation) or astro_value(title) or sim_value(f"{date}:{name}")
    prompt = build_prompt(subject, explanation)
    brief = {"date": date, "apod_title": title, "work_name": name,
             "label": f"namecode - {name} | {value}", "source": src_url, "prompt": prompt}
    print(json.dumps(brief, ensure_ascii=False, indent=2))
    if a.brief_out:
        with open(a.brief_out, "w", encoding="utf-8") as fh:
            json.dump(brief, fh, ensure_ascii=False, indent=2)
    if a.caption_out:
        with open(a.caption_out, "w", encoding="utf-8") as fh:
            fh.write(build_caption(brief))

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
