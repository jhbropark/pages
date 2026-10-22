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
from datetime import date as Date, datetime, timezone
from html import unescape
from PIL import Image, ImageDraw, ImageFont, ImageOps
import krea

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
def _html_text(value):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


GENERIC_APOD_TITLES = {"", "apod", "nasa science", "astronomy picture of the day"}
PLAYER_PLACEHOLDER = re.compile(
    r"to view this video|please enable javascript|supports? html5 video|"
    r"javascript (?:is )?(?:required|disabled)", re.I)


def _subject_title(title):
    """Keep the source title, not a made-up astronomical subject or site label."""
    title = _html_text(title) if isinstance(title, str) else ""
    normalized = re.sub(r"[\W_]+", " ", title.casefold(), flags=re.UNICODE).strip()
    if normalized in GENERIC_APOD_TITLES or PLAYER_PLACEHOLDER.search(title):
        raise ValueError("Missing specific APOD subject; generic title/player text refused")
    return title


def _source_content_ok(title, explanation):
    try:
        _subject_title(title)
    except ValueError:
        return False
    return (isinstance(explanation, str) and len(_html_text(explanation)) >= 80
            and not PLAYER_PLACEHOLDER.search(explanation))


def visual_context(explanation, max_chars=800, max_sentences=3):
    """Bound source context at sentence boundaries, never at character 200.

    This is source text, not an automatic claim that the generated scene matches
    it. If no whole sentence fits, omit the context instead of inventing or
    splicing a sentence fragment into the rendering instructions.
    """
    text = _html_text(explanation or "")
    if PLAYER_PLACEHOLDER.search(text):
        raise ValueError("Video player placeholder is not APOD scene context")
    if len(text) <= max_chars:
        return text
    selected = []
    used = 0
    for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“])', text):
        if not re.search(r'[.!?]["”)]?$', sentence):
            continue
        if len(sentence) > max_chars:
            continue
        if used + len(sentence) + bool(selected) > max_chars:
            break
        selected.append(sentence)
        used += len(sentence) + (1 if len(selected) > 1 else 0)
        if len(selected) >= max_sentences:
            break
    return " ".join(selected)


def parse_apod_html(html, date):
    """Parse both the legacy APOD template and NASA's newer archive article."""
    expected = Date.fromisoformat(date)
    rows = re.findall(r'<th\b[^>]*>(.*?)</th>\s*<td\b[^>]*>(.*?)</td>', html, re.S)
    meta = {_html_text(k).rstrip(":"): _html_text(v) for k, v in rows}
    date_row = re.search(
        r'<th\b[^>]*>\s*Date\s*:?[\s]*</th>\s*<td\b[^>]*>.*?</td>',
        html, re.S | re.I)
    if not date_row:
        raise ValueError("APOD article date missing")
    actual = datetime.strptime(meta.get("Date", ""), "%B %d, %Y").date()
    if actual != expected:
        raise ValueError(f"APOD article date mismatch: {actual} != {expected}")
    heading = re.search(r'<h1\b[^>]*>(.*?)</h1>', html, re.S | re.I)
    title = _html_text(heading.group(1)) if heading else ""

    # NASA's newer image-article pages render the label as plain text instead
    # of <strong>Explanation:</strong>. Scope extraction to the article between
    # its title and verified date metadata; never consume site chrome.
    body_start = heading.end() if heading else 0
    body = html[body_start:date_row.start()]
    label = re.search(
        r'(?:<strong\b[^>]*>\s*)?Explanation\s*:\s*(?:</strong>\s*)?',
        body, re.S | re.I)
    explanation_html = body[label.end():] if label else ""
    if explanation_html:
        boundary = re.search(
            r'(?:<br\s*/?>\s*){2}|</p\s*>|</article\s*>|</main\s*>|'
            r'Tomorrow[’\']s\s+picture\s*:|<h[23]\b',
            explanation_html, re.S | re.I)
        if boundary:
            explanation_html = explanation_html[:boundary.start()]
    text = _html_text(explanation_html)
    if not _source_content_ok(title, text):
        raise ValueError("APOD article missing verified title/explanation")
    # Keep only media in the article hero, never the page's NASA logo.
    hero = html[body_start:body_start + label.start()] if label else ""
    image = re.search(r'<img\b[^>]*\bsrc="([^"]+)"', hero, re.S | re.I)
    credit = next((v for k, v in meta.items() if "Credit" in k), None)
    return {"date": date, "title": title, "explanation": text,
            "media_type": "video" if "Video Credit" in meta else "image",
            "url": unescape(image.group(1)) if image else None,
            "copyright": credit}


def get_apod_html(date):
    # Legacy apYYMMDD.html now redirects to *today*, dropping the requested date.
    url = "https://science.nasa.gov/apod/?date=" + Date.fromisoformat(date).strftime("%y%m%d")
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return parse_apod_html(r.text, date)
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def get_apod(date=None, retries=2):
    date = date or datetime.now(timezone.utc).date().isoformat()
    if Date.fromisoformat(date) > datetime.now(timezone.utc).date():
        raise ValueError("Future APOD dates are unavailable")
    base = os.environ.get("NASA_APOD_BASE", "https://api.nasa.gov/planetary/apod")
    params = {"api_key": os.environ.get("NASA_API_KEY", "DEMO_KEY"), "thumbs": "true", "date": date}
    for i in range(retries):
        try:
            r = requests.get(base, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if (data.get("date") != date
                    or not _source_content_ok(data.get("title"), data.get("explanation"))):
                break  # Known upstream parser corruption: use the dated article.
            return data
        except (requests.RequestException, ValueError):
            if i < retries - 1:
                time.sleep(2 ** i)
    print("[APOD] API unavailable/invalid; reading date-verified NASA article", file=sys.stderr)
    return get_apod_html(date)

APOD_ARCHIVE = "https://science.nasa.gov/apod/?date={yy}{mm}{dd}"
ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def apod_article_url(date):
    """The APOD article page for an ISO date, or None when the date is not a
    real APOD day ('manual', 'today', a --subject run).

    Use NASA's date-fixed query because the legacy apYYMMDD.html endpoint
    redirects to today's page, dropping the date. A non-ISO date returns
    None and the caption simply omits the link."""
    m = ISO_DATE.match((date or "").strip())
    if not m:
        return None
    y, mm, dd = m.groups()
    return APOD_ARCHIVE.format(yy=y[2:], mm=mm, dd=dd)


# Recognizable astronomical phenomena make punchier work names than generic
# title words.
#
# Two rules keep the name honest:
#   1. the TITLE is scanned first — the title is what the APOD is *about*.
#      The explanation is only a fallback for the (rare) title with no subject
#      in it. Scanning "title + explanation" as one blob is what used to turn
#      'The Cocoon Nebula Wide Field' into COMET, because a comet happened to
#      be mentioned three sentences into the write-up.
#   2. within the title, the list order decides. It runs specific -> generic,
#      so 'Tycho: A Lunar Crater' resolves to CRATER (the subject) rather than
#      LUNAR (a modifier), while 'Lunar Farside' still resolves to LUNAR.
# (stem matched with a word boundary -> clean display name; stems catch plurals)
PHENOMENA = [
    # named events / optical phenomena — always the subject when present
    ("occult", "OCCULTATION"), ("analemma", "ANALEMMA"),
    ("zodiacal", "ZODIACAL"), ("gegenschein", "GEGENSCHEIN"),
    ("noctilucent", "NOCTILUCENT"), ("airglow", "AIRGLOW"),
    ("sundog", "SUNDOG"), ("sun dog", "SUNDOG"), ("parhelion", "SUNDOG"),
    ("eclipse", "ECLIPSE"), ("transit", "TRANSIT"),
    ("conjunction", "CONJUNCTION"), ("opposition", "OPPOSITION"),
    ("libration", "LIBRATION"), ("terminator", "TERMINATOR"),
    # surface / structural features
    ("crater", "CRATER"), ("caldera", "CALDERA"), ("canyon", "CANYON"),
    ("pillar", "PILLAR"), ("filament", "FILAMENT"), ("prominence", "PROMINENCE"),
    ("sunspot", "SUNSPOT"), ("flare", "FLARE"),
    # objects and events
    ("supernova", "SUPERNOVA"), ("comet", "COMET"), ("asteroid", "ASTEROID"),
    ("meteor", "METEOR"), ("aurora", "AURORA"), ("eruption", "ERUPTION"),
    ("solstice", "SOLSTICE"), ("equinox", "EQUINOX"),
    ("corona", "CORONA"), ("halo", "HALO"), ("rainbow", "RAINBOW"),
    ("nova", "NOVA"), ("quasar", "QUASAR"), ("pulsar", "PULSAR"),
    ("nebula", "NEBULA"), ("galax", "GALAXY"), ("cluster", "CLUSTER"),
    ("milky way", "MILKYWAY"),
    # generic bodies — last, so they only win when nothing sharper is in the title
    ("lunar", "LUNAR"), ("moon", "MOON"), ("solar", "SOLAR"), ("sun", "SUN"),
]


# Words that look like a phenomenon but are place or constellation names.
# 'The Corona Australis Molecular Cloud' is not the solar corona.
FALSE_FRIENDS = {
    "CORONA": r"\bcorona\s+(?:australis|borealis)",
    "NOVA": r"\bnova\s+scotia",
    "SUN": r"\bsun\s+(?:valley|city)",
}


def _phenomenon(text):
    """First PHENOMENA entry (specific -> generic) whose stem is in `text` and
    is not a known false friend."""
    low = (text or "").lower()
    for stem, name in PHENOMENA:
        m = re.search(rf"\b{re.escape(stem)}", low)
        if not m:
            continue
        trap = FALSE_FRIENDS.get(name)
        if trap and re.search(trap, low) and len(re.findall(rf"\b{re.escape(stem)}", low)) == \
                len(re.findall(trap, low)):
            continue  # every occurrence is the place name
        return name
    return None


def _title_words(title):
    """The salient words of a title: the two longest non-stopwords, kept in the
    order they appear ('Daytime Moon Meets Evening Star' -> DAYTIME.EVENING)."""
    words = [w for w in re.findall(r"[A-Za-z]+", title or "") if w.lower() not in STOPWORDS]
    words = sorted(set(words), key=lambda w: (-len(w), title.lower().index(w.lower())))[:2]
    return sorted(words, key=lambda w: title.lower().index(w.lower()))


def derive_name(title, explanation=""):
    """Turn an APOD into a namecode work name.

    Priority, highest first:
      1. a known phenomenon in the TITLE  ('Cocoon Nebula Wide Field' -> NEBULA)
      2. the salient words of the title   ('Daytime Moon ...' -> DAYTIME.EVENING)
      3. a known phenomenon in the EXPLANATION — only when the title carries no
         subject at all (empty title, or nothing but stopwords)
      4. 'APOD'
    """
    from_title = _phenomenon(title)
    if from_title:
        return from_title
    words = _title_words(title)
    if words:
        return ".".join(w.upper() for w in words)
    return _phenomenon(explanation) or "APOD"


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


# ---------------------------------------------------------------- caption
# 3-5 targeted hashtags, all of which describe what the post actually is.
# (#creativecodeart is gone: nothing here is hand-written creative code — the
# frame comes out of an image model and is then duotoned.)
HASHTAGS_BASE = ["#namecode", "#nasaapod", "#generativeart"]

CHANNELS = ("instagram", "facebook")
FORMATS = ("image", "reel")

# per surface: Instagram carries the tag load, Facebook keeps it minimal.
CHANNEL_TAGS = {
    ("instagram", "image"): ["#namecode", "#nasaapod", "#aiart", "#generativeart"],
    ("instagram", "reel"): ["#namecode", "#nasaapod", "#aiart"],
    ("facebook", "image"): ["#namecode", "#nasaapod"],
    ("facebook", "reel"): ["#namecode", "#nasaapod"],
}

# filename suffix -> (channel, format). "" is the legacy caption_<date>.txt.
CAPTION_VARIANTS = (
    ("", "instagram", "image"),
    ("_facebook", "facebook", "image"),
    ("_reel_instagram", "instagram", "reel"),
    ("_reel_facebook", "facebook", "reel"),
)


def topical_tag(name):
    word = re.split(r"[.\s]", name)[0].lower()
    return "#" + re.sub(r"[^a-z0-9]", "", word)


def _tags(channel, fmt, work_name):
    """3-5 tags: the surface's base set plus one topical tag, deduped."""
    tags = list(CHANNEL_TAGS[(channel, fmt)])
    topical = topical_tag(work_name or "namecode")
    if topical not in tags and len(topical) > 1:
        tags.append(topical)
    for filler in HASHTAGS_BASE:  # never fall under three
        if len(tags) >= 3:
            break
        if filler not in tags:
            tags.append(filler)
    return " ".join(tags[:5])


def _credit(brief):
    """Photographer credit for the source image, when APOD supplied one."""
    who = (brief.get("attribution") or "").strip()
    return f"Original image: {who} / NASA APOD" if who else None


def _lines(*parts):
    """Join non-empty caption blocks with a single blank line between them."""
    return "\n\n".join(p for p in parts if p)


def build_caption(brief, channel="instagram", format="image"):
    """The post caption for one surface.

    Backwards compatible: build_caption(brief) is unchanged in signature and
    still returns the Instagram feed-image caption (the text that lands in
    caption_<date>.txt).

    What the text may and may not say:
      - the APOD title comes first; it is the subject of the post
      - the picture is described for what it is — an AI image made from the
        APOD description, then reduced to two tones. It is not presented as a
        telescope photograph, and not as something "rendered in code"
      - the APOD article URL is derived from the ISO date and omitted entirely
        when there is no real APOD day behind the run
      - no invented science, no invented personal experience, no engagement
        bait ("save this", "send this to someone")
    """
    fmt = format
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel: {channel!r} (expected one of {CHANNELS})")
    if fmt not in FORMATS:
        raise ValueError(f"unknown format: {fmt!r} (expected one of {FORMATS})")

    title = (brief.get("apod_title") or "APOD").strip()
    date = (brief.get("date") or "").strip()
    name = brief.get("work_name") or "APOD"
    label = brief.get("label") or f"namecode - {name}"
    url = brief.get("apod_url") or apod_article_url(date)
    credit = _credit(brief)
    dateline = f"NASA APOD {date}" if ISO_DATE.match(date) else "NASA APOD"
    tags = _tags(channel, fmt, name)

    if fmt == "image" and channel == "instagram":
        return _lines(
            f"{title} — {dateline}.\n{label}",
            "사진이 아니라, APOD 설명문에서 출발한 AI 이미지입니다. 두 개의 톤만 남겼습니다.\n"
            "Not the photograph: an AI image made from the APOD description, "
            "then reduced to two tones.",
            credit,
            f"APOD: {url}" if url else None,
            tags,
        )

    if fmt == "image" and channel == "facebook":
        return _lines(
            f"{title}\n{dateline} · {label}",
            "APOD 설명문을 읽고 AI로 다시 그린 이미지입니다. 원본 사진과 해설은 아래 링크에 있습니다.\n"
            "An AI reinterpretation of the APOD description. The original image "
            "and the full write-up are linked below.",
            credit,
            url,
            tags,
        )

    if fmt == "reel" and channel == "instagram":
        return _lines(
            f"{name} — {title}.\n{dateline}.",
            "APOD 설명문으로 만든 AI 이미지 한 장을 9:16으로 움직였습니다.\n"
            "One AI frame from today's APOD description, set in motion at 9:16.",
            credit,
            f"APOD: {url}" if url else None,
            tags,
        )

    # reel / facebook
    return _lines(
        f"{name} — {title}. {dateline}.",
        "AI 이미지 한 장에서 출발한 9:16 영상입니다. 망원경 사진이 아닙니다.\n"
        "A 9:16 clip built from a single AI frame — not from the telescope image.",
        credit,
        f"원본과 해설 / original and write-up: {url}" if url else None,
        tags,
    )


def caption_variant_path(caption_out, suffix):
    """caption_2026-09-24.txt + '_facebook' -> caption_2026-09-24_facebook.txt"""
    if not suffix:
        return caption_out
    root, ext = os.path.splitext(caption_out)
    return f"{root}{suffix}{ext}"


def write_captions(brief, caption_out):
    """Write every surface's caption next to --caption-out and return
    {path: (channel, format)}.

    The legacy path is written unchanged in name and meaning (Instagram feed
    image), so the workflow's --caption-file wiring keeps working; the three
    siblings are additive."""
    written = {}
    for suffix, channel, fmt in CAPTION_VARIANTS:
        path = caption_variant_path(caption_out, suffix)
        if os.path.exists(path):
            continue  # Preserve human-curated and previously committed captions.
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build_caption(brief, channel=channel, format=fmt))
        written[path] = (channel, fmt)
    return written


def build_prompt(subject, explanation=""):
    subject = _subject_title(subject)
    context = visual_context(explanation)
    return (
        f"Visual subject: {subject}.\n"
        f"Scene context from the APOD description: {context or 'No scene context supplied.'}\n"
        "Keep the named subject and its source-described distinguishing features "
        "visually legible; do not replace it with an unrelated generic space scene. "
        "This is an AI interpretation of text, not a reconstruction of a source photograph.\n"
        "Style: Cinematic dark monochrome generative art. "
        "Rendered as fine white particles and light filaments on a pure black "
        "background, volumetric, dramatic, monochrome white on black, lots of "
        "negative space, high detail."
    )


def build_brief(date, title, name, value, prompt, src_url=None,
                explanation="", attribution=None):
    """The brief JSON.

    'source' keeps its original meaning (the APOD image file). The additions
    are metadata only, and each is omitted when there is nothing true to put
    in it: 'apod_url' (the article page for that ISO date), 'explanation'
    (APOD's own text, the caption's only factual source) and 'attribution'
    (APOD's copyright line, when the image is not public domain)."""
    brief = {"date": date, "apod_title": title, "work_name": name,
             "label": f"namecode - {name} | {value}", "source": src_url,
             "prompt": prompt}
    # The title/context are explicit review targets, not a semantic QA pass.
    brief["visual_subject"] = _subject_title(title)
    brief["visual_context"] = visual_context(explanation)
    brief["visual_review"] = {
        "status": "pending", "required": True,
        "reason": "Check first-frame subject against source context and caption before publication"
    }
    url = apod_article_url(date)
    if url:
        brief["apod_url"] = url
    if explanation:
        brief["explanation"] = explanation
    if attribution:
        brief["attribution"] = attribution
    return brief


# ---------------------------------------------------------------- Krea
IMAGE_MODELS = {"flux": "bfl/flux-1-dev", "imagen-4": "google/imagen-4",
                "nano-banana": "google/nano-banana-pro"}


def krea_generate(prompt, width=1024, height=1280, model="flux"):  # 4:5 portrait
    path = IMAGE_MODELS.get(model, IMAGE_MODELS["flux"])
    return krea.submit(f"image/{path}", {"prompt": prompt, "width": width, "height": height})


def krea_wait(job_id, timeout=120):
    return krea.wait(job_id, timeout=timeout)


# ---------------------------------------------------------------- compose
def compose(img_bytes, name, value, out, size=FEED_SIZE):
    """Compose a finished post. Default 4:5 (1080x1350) for the IG feed."""
    W, H = size
    g = ImageOps.autocontrast(Image.open(io.BytesIO(img_bytes)).convert("L"), cutoff=1)
    g = ImageOps.fit(g, (W, H), method=Image.LANCZOS)          # cover-fit to 4:5
    im = ImageOps.colorize(g, black=BLACK, white=PAPER).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    label = f"namecode - {name} | {value}"
    # Instagram's grid/reels thumbnails center-crop the frame (a 4:5 cover shown
    # in the taller reels cell loses ~8-15% off each side), which was clipping
    # the "namecode" prefix. Inset the label into the crop-safe band [10%, 92%]
    # and shrink the font if a long name would push the value past the right edge.
    pad = 14
    x, y = round(W * 0.10), round(W * 0.05)
    right_safe = round(W * 0.92)
    fs = max(20, W // 34)
    f = ImageFont.truetype(FONT, fs)
    while fs > 18 and x + d.textlength(label, font=f) + pad * 2 > right_safe:
        fs -= 1
        f = ImageFont.truetype(FONT, fs)
    tw = d.textlength(label, font=f)
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + f.size + 22], radius=6, fill=(18, 18, 18, 190))
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
    ap.add_argument("--reel-out", help="also compose a 9:16 still (reel start_image)")
    ap.add_argument("--brief-out", help="write the brief JSON to this path")
    ap.add_argument("--caption-out", help="write the post captions to this path "
                                          "(plus _facebook / _reel_instagram / "
                                          "_reel_facebook siblings)")
    a = ap.parse_args()

    attribution = None
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
        attribution = apod.get("copyright")

    name = a.name or derive_name(title, explanation)
    value = astro_value(explanation) or astro_value(title) or sim_value(f"{date}:{name}")
    prompt = build_prompt(subject, explanation)
    brief = build_brief(date, title, name, value, prompt, src_url=src_url,
                        explanation=explanation, attribution=attribution)
    print(json.dumps(brief, ensure_ascii=False, indent=2))
    if a.brief_out:
        with open(a.brief_out, "w", encoding="utf-8") as fh:
            json.dump(brief, fh, ensure_ascii=False, indent=2)
    if a.caption_out:
        for path in write_captions(brief, a.caption_out):
            print(f"[ok] caption {path}", file=sys.stderr)

    if a.dry_run:
        return
    job = krea_generate(prompt, model=a.model)
    url = krea_wait(job)
    img = requests.get(url, timeout=60).content
    out = a.out or f"namecode_apod_{date}.png"
    compose(img, name, value, out)
    print(f"[ok] saved {out}", file=sys.stderr)
    if a.reel_out:  # full-bleed 9:16 start_image so the reel has no blur bars
        compose(img, name, value, a.reel_out, size=REEL_SIZE)
        print(f"[ok] saved {a.reel_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
