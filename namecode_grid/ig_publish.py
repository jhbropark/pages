#!/usr/bin/env python3
"""
ig_publish.py — publish a namecode post to Instagram via the Meta Graph API.

Companion to apod_namecode.py. Once @namecode_original is a Business/Creator
account linked to a Facebook Page and you have a long-lived token with
`instagram_content_publish`, this posts a feed image or a reel.

Graph API publishing is a 2-step (image) / 3-step (reel) flow:
  image : create container (image_url, caption) -> media_publish
  reel  : create container (REELS, video_url)   -> poll status -> media_publish

IMPORTANT: Graph API only accepts a PUBLIC https URL (not a local file). Composite
the final artwork first (apod_namecode.py), then host it (GitHub raw on a public
repo, S3, Cloudinary, etc.) and pass that URL here. Krea result URLs are already
public and can be posted directly if you don't need the mono label baked in.

Env:
  IG_USER_ID        Instagram Business/Creator user id (numeric)
  IG_ACCESS_TOKEN   long-lived token with instagram_content_publish
  GRAPH_BASE        default https://graph.facebook.com
  GRAPH_VERSION     default v21.0

Usage:
  python ig_publish.py --image-url https://.../post.png --caption-file caption.txt
  python ig_publish.py --reel --video-url https://.../reel.mp4 --caption "..."
  python ig_publish.py --image-url https://.../post.png --caption "..." --dry-run
"""
import argparse, os, sys, time
import requests


def cfg():
    ver = os.environ.get("GRAPH_VERSION", "v21.0")
    uid = os.environ.get("IG_USER_ID")
    tok = os.environ.get("IG_ACCESS_TOKEN")
    # Auto-pick the API host from the token type unless GRAPH_BASE is set:
    #   Instagram-login tokens (IGAA…/IG…) -> graph.instagram.com
    #   Facebook-login tokens (EAA…)       -> graph.facebook.com
    base = os.environ.get("GRAPH_BASE")
    if not base:
        base = ("https://graph.instagram.com" if (tok or "").startswith("IG")
                else "https://graph.facebook.com")
    return base, ver, uid, tok


def _post(url, params, dry):
    if dry:
        safe = {k: ("<token>" if k == "access_token" else v) for k, v in params.items()}
        print(f"POST {url}\n     {safe}", file=sys.stderr)
        return {"id": "DRYRUN_ID"}
    r = requests.post(url, params=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} {r.text}")
    return r.json()


def _get(url, params, dry):
    if dry:
        print(f"GET  {url}", file=sys.stderr)
        return {"status_code": "FINISHED"}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def _wait_ready(base, ver, cid, tok, dry, tries=20, delay=3):
    """Poll a media container's status_code until FINISHED before publishing.
    Skipping this causes code 9007 'media is not ready for publishing'.
    Images are usually ready in seconds; reels take longer.

    The status GET can return a transient 403/429/5xx mid-poll (rate limiting or
    an IG-side blip) — those must NOT abort a multi-minute reel wait, so tolerate
    a run of consecutive errors and keep polling until FINISHED/ERROR/timeout."""
    errors = 0
    for _ in range(tries):
        try:
            st = _get(f"{base}/{ver}/{cid}", {"fields": "status_code", "access_token": tok}, dry)
        except Exception as e:
            errors += 1
            print(f"[warn] status poll transient error {errors}: {e}", file=sys.stderr)
            if errors >= 12:
                raise RuntimeError(f"status poll failed {errors}x: {e}")
            time.sleep(delay)
            continue
        errors = 0
        sc = st.get("status_code")
        if sc == "FINISHED":
            return
        if sc == "ERROR":
            raise RuntimeError(f"container processing error: {st}")
        time.sleep(delay)
    raise RuntimeError("container not ready (timed out)")


def publish_image(image_url, caption, dry=False):
    base, ver, uid, tok = cfg()
    container = _post(f"{base}/{ver}/{uid}/media",
                      {"image_url": image_url, "caption": caption, "access_token": tok}, dry)
    cid = container["id"]
    _wait_ready(base, ver, cid, tok, dry)
    res = _post(f"{base}/{ver}/{uid}/media_publish",
                {"creation_id": cid, "access_token": tok}, dry)
    return res["id"]


def publish_reel(video_url, caption, cover_url=None, dry=False):
    base, ver, uid, tok = cfg()
    params = {"media_type": "REELS", "video_url": video_url,
              "caption": caption, "access_token": tok}
    if cover_url:
        params["cover_url"] = cover_url
    container = _post(f"{base}/{ver}/{uid}/media", params, dry)
    cid = container["id"]
    # Reels transcode server-side and can take several minutes; 40x5s (200s) was
    # timing out ("container not ready"). Give it ~12 min (overridable) — the IG
    # container stays valid for ~24h, so a longer poll costs nothing on success.
    tries = int(os.environ.get("IG_REEL_WAIT_TRIES", "90"))
    delay = int(os.environ.get("IG_REEL_WAIT_DELAY", "8"))
    _wait_ready(base, ver, cid, tok, dry, tries=tries, delay=delay)
    res = _post(f"{base}/{ver}/{uid}/media_publish",
                {"creation_id": cid, "access_token": tok}, dry)
    return res["id"]


def publish_carousel(image_urls, caption, dry=False):
    """Carousel: each image as a child item -> CAROUSEL container -> publish."""
    base, ver, uid, tok = cfg()
    children = []
    for u in image_urls:
        c = _post(f"{base}/{ver}/{uid}/media",
                  {"image_url": u, "is_carousel_item": "true", "access_token": tok}, dry)
        children.append(c["id"])
    container = _post(f"{base}/{ver}/{uid}/media",
                      {"media_type": "CAROUSEL", "children": ",".join(children),
                       "caption": caption, "access_token": tok}, dry)
    _wait_ready(base, ver, container["id"], tok, dry)
    res = _post(f"{base}/{ver}/{uid}/media_publish",
                {"creation_id": container["id"], "access_token": tok}, dry)
    return res["id"]


def get_permalink(mid, dry=False):
    """Public instagram.com URL of a published media (for the Telegram button)."""
    if dry:
        return ""
    base, ver, _, tok = cfg()
    try:
        j = _get(f"{base}/{ver}/{mid}", {"fields": "permalink", "access_token": tok}, dry)
        return j.get("permalink", "")
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-url")
    ap.add_argument("--reel", action="store_true")
    ap.add_argument("--video-url")
    ap.add_argument("--cover-url")
    ap.add_argument("--carousel", help="comma-separated image URLs (2-10)")
    ap.add_argument("--caption", default="")
    ap.add_argument("--caption-file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    caption = a.caption
    if a.caption_file:
        caption = open(a.caption_file, encoding="utf-8").read().strip()

    _, _, uid, tok = cfg()
    if not a.dry_run and (not uid or not tok):
        sys.exit("ERROR: set IG_USER_ID and IG_ACCESS_TOKEN (or use --dry-run).")

    if a.carousel:
        urls = [u.strip() for u in a.carousel.split(",") if u.strip()]
        if len(urls) < 2:
            sys.exit("ERROR: --carousel needs 2-10 image URLs")
        mid = publish_carousel(urls, caption, a.dry_run)
    elif a.reel:
        if not a.video_url:
            sys.exit("ERROR: --reel requires --video-url")
        mid = publish_reel(a.video_url, caption, a.cover_url, a.dry_run)
    else:
        if not a.image_url:
            sys.exit("ERROR: provide --image-url, --reel --video-url, or --carousel")
        mid = publish_image(a.image_url, caption, a.dry_run)
    print(f"[ok] published media id: {mid}")
    link = get_permalink(mid, a.dry_run)
    if link:
        print(f"permalink: {link}")


if __name__ == "__main__":
    main()
