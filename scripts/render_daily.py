#!/usr/bin/env python3
"""Render and queue one day of content — with no model call at all.

This is the script the daily workflow runs. It takes copy that was written
ahead of time into ``content/buffer.json`` and turns it into cards and queue
entries. It never touches the Anthropic API, so a lapsed key, an empty credit
balance or an API outage cannot stop the day's post: only an empty buffer can,
and that is visible days in advance.

``scripts/generate_content.py`` is the other half — it writes into the buffer,
runs weekly rather than daily, and is the only part that needs a model.

Exit codes:
  0  a day was rendered, or the slots were already present
  2  the buffer is empty (the refill workflow has not run, or has fallen behind)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import editorial_cards as cards  # noqa: E402
from visual_direction_renderer import render_direction  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
BUFFER_FILE = REPO_ROOT / "content" / "buffer.json"
TOPICS_FILE = REPO_ROOT / "content" / "topics.json"
QUEUE_FILE = REPO_ROOT / "queue" / "queue.json"
LINKEDIN_QUEUE_FILE = REPO_ROOT / "linkedin" / "queue.json"
IMAGES_DIR = REPO_ROOT / "images" / "daily"

KST = timezone(timedelta(hours=9))
RAW_BASE_URL = "https://raw.githubusercontent.com/jhbropark/pages/main"

# The six content types the brand already ships in images/channel-six-types/.
# The daily slot walks this list instead of emitting single_image every day.
FORMAT_CYCLE = [
    ("single_image", 1),
    ("carousel", 4),
    ("single_image", 1),
    ("story", 1),
    ("single_image", 1),
    ("carousel", 4),
]

# The order of roles a carousel walks. Each role is a different composition,
# so a deck alternates picture, type, figure and list rather than repeating one
# layout — see docs/editorial-direction.md.
CAROUSEL_ROLES = ["cover", "statement", "evidence", "vertical", "detail", "close"]

# A single card is a cover when there is a picture to carry it, and a statement
# when there is not; the renderer falls back on its own if the image is missing.
SINGLE_ROLE = "cover"

# LinkedIn stays landscape (1200x627) and keeps the art directions from
# images/concepts/visual-directions-v3/ that the old pipeline already wired up.
# Only the Instagram card changed shape and design.
VISUAL_DIRECTIONS = (
    "insight", "moa-craft", "industry-solution",
    "methodology", "portfolio", "philosophy",
)


# ---------------------------------------------------------------------------
# Buffer
# ---------------------------------------------------------------------------

def load_buffer() -> dict:
    if not BUFFER_FILE.exists():
        return {"items": []}
    with open(BUFFER_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_buffer(buffer: dict) -> None:
    with open(BUFFER_FILE, "w", encoding="utf-8") as f:
        json.dump(buffer, f, ensure_ascii=False, indent=2)
        f.write("\n")


def unused(buffer: dict) -> list[dict]:
    return [item for item in buffer.get("items", []) if not item.get("consumed_at")]


# ---------------------------------------------------------------------------
# Queues
# ---------------------------------------------------------------------------

def _read_queue(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_queue(path: Path, queue: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")


def slot_exists(post_id: str) -> bool:
    return any(item.get("id") == post_id for item in _read_queue(QUEUE_FILE)["items"])


def _image_keys(fmt: str, urls: list[str]) -> dict:
    """The image key an Instagram post carries, which names its format.

    `instagram_upload.py` reads the format off the key rather than off
    `format`: anything holding `image_urls` goes down the carousel path, and a
    carousel of one is not a legal carousel. Writing both keys sent the
    2026-09-21 morning card there and Graph rejected it before it ever posted
    ("image_urls는 2~10장의 이미지여야 합니다"). So the keys are exclusive, as
    every hand-written entry in the queue already had them.
    """
    if fmt == "carousel":
        return {"image_urls": urls}
    return {"image_url": urls[0]}


def compute_scheduled_time(now_kst: datetime, time_str: str) -> datetime:
    """Today at ``time_str``, or tomorrow if that has already passed.

    The old rule pushed to the next day whenever the target was less than two
    hours out, which meant a runner that started forty minutes late silently
    moved the 09:00 LinkedIn post to the following day. Only an already-past
    time rolls over now, so ordinary scheduler drift no longer changes the day.
    """
    hour, minute = (int(x) for x in time_str.split(":"))
    target = now_kst.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now_kst:
        target += timedelta(days=1)
    return target


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_post(item: dict, post_id: str, slide_count: int) -> list[str]:
    """Render the card(s) for one post and return their filenames.

    Fewer cards than asked for is possible: an item with no ``slides`` has
    nothing to build a deck from. render_slot downgrades the format when that
    happens, so the queue never labels a single card as a carousel.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    slides = item.get("slides") or []
    names: list[str] = []

    if slide_count == 1:
        name = f"{post_id}.jpg"
        cards.render(
            cards.Slide(
                role=item.get("role", SINGLE_ROLE),
                kicker=item.get("kicker", ""),
                headline=item["image_headline"],
                sub=item.get("note", ""),
                stat=item.get("stat", ""),
                stat_note=item.get("stat_note", ""),
                image=item.get("image", ""),
                index=1,
                total=1,
            ),
            IMAGES_DIR / name,
        )
        return [name]

    # A carousel: the buffered slides if they were written, otherwise the
    # headline as a cover followed by whatever supporting lines exist.
    if not slides:
        slides = [{"headline": item["image_headline"], "note": item.get("note", "")}]
        slides += [{"headline": line} for line in item.get("points", [])]
    slides = slides[:slide_count]

    total = len(slides)
    for index, slide in enumerate(slides):
        name = f"{post_id}-{index + 1:02d}.jpg"
        # The last slide of a carousel is always the close, whatever its
        # position in the role order, so a deck ends on the ask.
        if index == total - 1 and total > 1:
            default_role = "close"
        else:
            default_role = CAROUSEL_ROLES[index % (len(CAROUSEL_ROLES) - 1)]
        cards.render(
            cards.Slide(
                role=slide.get("role", default_role),
                kicker=slide.get("kicker", item.get("kicker", "") if index == 0 else ""),
                headline=slide.get("headline", ""),
                sub=slide.get("note", slide.get("body", "")),
                stat=slide.get("stat", ""),
                stat_note=slide.get("stat_note", ""),
                items=slide.get("items", []),
                image=slide.get("image", item.get("image", "")),
                index=index + 1,
                total=total,
            ),
            IMAGES_DIR / name,
        )
        names.append(name)
    return names


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def render_slot(now_kst: datetime, config: dict, slot: dict, slot_index: int,
                buffer: dict) -> bool:
    slot_id = slot["id"]
    post_id = f"post_{now_kst:%Y%m%d}_{slot_id}"
    if slot_exists(post_id):
        print(f"[{post_id}] already queued; skipping.", flush=True)
        return False

    pending = unused(buffer)
    if not pending:
        print(f"[{slot_id}] buffer is empty — nothing to render.", flush=True)
        return False
    item = pending[0]

    day_index = now_kst.timetuple().tm_yday * len(config["daily_slots"]) + slot_index
    fmt, slide_count = FORMAT_CYCLE[day_index % len(FORMAT_CYCLE)]
    print(f"[{slot_id}] {fmt} ({slide_count} slide(s)) — {item['topic']}", flush=True)

    names = render_post(item, post_id, slide_count)
    if len(names) < slide_count:
        # The buffer item had no slides to build a deck from. Post it honestly
        # as what it is rather than sending one image out as a carousel.
        print(f"[{slot_id}] only {len(names)} card(s) available for a "
              f"{slide_count}-card {fmt}; posting as single_image instead",
              flush=True)
        fmt = "single_image"
    urls = [f"{RAW_BASE_URL}/images/daily/{name}" for name in names]

    direction = VISUAL_DIRECTIONS[day_index % len(VISUAL_DIRECTIONS)]
    li_names = {}
    for language, headline in (("ko", item["image_headline"]),
                               ("en", item["english_image_headline"])):
        li_name = f"{post_id}_linkedin_{language}.jpg"
        render_direction(direction, headline, language, IMAGES_DIR / li_name)
        li_names[language] = f"{RAW_BASE_URL}/images/daily/{li_name}"

    scheduled = compute_scheduled_time(now_kst, slot["instagram_time_kst"])
    queue = _read_queue(QUEUE_FILE)
    queue["items"].append({
        "id": post_id,
        "status": "pending",
        "topic": item["topic"],
        "format": fmt,
        "slot": slot_id,
        **_image_keys(fmt, urls),
        "alt_text": f"bbbb.beauty 카드: {item['image_headline']}",
        "caption": item["caption"],
        "hashtags": item["hashtags"],
        "scheduled_time": scheduled.isoformat(),
        "created_at": now_kst.isoformat(),
        "generated_by": item.get("generated_by", "buffer"),
    })

    linkedin_scheduled = compute_scheduled_time(now_kst, slot["linkedin_time_kst"])
    pair_id = f"linkedin_{now_kst:%Y%m%d}_{slot_id}"
    common = {
        "pair_id": pair_id,
        "status": "pending",
        "topic": item["topic"],
        "slot": slot_id,
        "scheduled_time": linkedin_scheduled.isoformat(),
        "created_at": now_kst.isoformat(),
        "generated_by": item.get("generated_by", "buffer"),
        "dm_keyword": item["dm_keyword"],
    }
    linkedin = _read_queue(LINKEDIN_QUEUE_FILE)
    linkedin["items"].extend([
        {**common, "id": f"{pair_id}_ko", "language": "ko", "pair_order": 1,
         "commentary": item["linkedin_ko"], "hashtags": item["linkedin_ko_hashtags"],
         "image_url": li_names["ko"],
         "alt_text": f"bbbb.beauty 한국어 카드: {item['image_headline']}"},
        {**common, "id": f"{pair_id}_en", "language": "en", "pair_order": 2,
         "commentary": item["linkedin_en"], "hashtags": item["linkedin_en_hashtags"],
         "image_url": li_names["en"],
         "alt_text": f"bbbb.beauty English card: {item['english_image_headline']}"},
    ])

    # Both queues are written only once every render has succeeded, so a failure
    # part-way through cannot leave the Instagram queue advanced and the
    # LinkedIn queue behind.
    _write_queue(QUEUE_FILE, queue)
    _write_queue(LINKEDIN_QUEUE_FILE, linkedin)
    item["consumed_at"] = now_kst.isoformat()
    item["consumed_as"] = post_id

    print(f"[{slot_id}] queued {len(names)} card(s) for {scheduled.isoformat()}", flush=True)
    return True


def main() -> int:
    now_kst = datetime.now(tz=KST)
    with open(TOPICS_FILE, encoding="utf-8") as f:
        config = json.load(f)
    buffer = load_buffer()

    rendered = 0
    for slot_index, slot in enumerate(config["daily_slots"]):
        rendered += int(render_slot(now_kst, config, slot, slot_index, buffer))
    save_buffer(buffer)

    remaining = len(unused(buffer))
    days_left = remaining // max(len(config["daily_slots"]), 1)
    print(f"rendered {rendered}/{len(config['daily_slots'])} slot(s); "
          f"buffer holds {remaining} item(s) ≈ {days_left} day(s)", flush=True)

    # The workflow reads these to decide whether to warn.
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"rendered={rendered}\n")
            f.write(f"buffer_remaining={remaining}\n")
            f.write(f"buffer_days={days_left}\n")

    if rendered == 0 and remaining == 0:
        print("buffer exhausted — run the refill workflow.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
