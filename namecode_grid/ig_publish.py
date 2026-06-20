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
    base = os.environ.get("GRAPH_BASE", "https://graph.facebook.com")
    ver = os.environ.get("GRAPH_VERSION", "v21.0")
    uid = os.environ.get("IG_USER_ID")
    tok = os.environ.get("IG_ACCESS_TOKEN")
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


def publish_image(image_url, caption, dry=False):
    base, ver, uid, tok = cfg()
    container = _post(f"{base}/{ver}/{uid}/media",
                      {"image_url": image_url, "caption": caption, "access_token": tok}, dry)
    cid = container["id"]
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
    # reels need processing; poll status_code until FINISHED
    for _ in range(30):
        st = _get(f"{base}/{ver}/{cid}", {"fields": "status_code", "access_token": tok}, dry)
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"reel processing error: {st}")
        time.sleep(5)
    res = _post(f"{base}/{ver}/{uid}/media_publish",
                {"creation_id": cid, "access_token": tok}, dry)
    return res["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-url")
    ap.add_argument("--reel", action="store_true")
    ap.add_argument("--video-url")
    ap.add_argument("--cover-url")
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

    if a.reel:
        if not a.video_url:
            sys.exit("ERROR: --reel requires --video-url")
        mid = publish_reel(a.video_url, caption, a.cover_url, a.dry_run)
    else:
        if not a.image_url:
            sys.exit("ERROR: provide --image-url (or --reel --video-url)")
        mid = publish_image(a.image_url, caption, a.dry_run)
    print(f"[ok] published media id: {mid}")


if __name__ == "__main__":
    main()
