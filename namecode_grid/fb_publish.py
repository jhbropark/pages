#!/usr/bin/env python3
"""Publish a photo to a Facebook Page via the Graph API.

Companion to ig_publish.py — cross-posts the daily artwork to the namecode
Facebook page. Facebook posting uses a *Page* access token (EAA…), separate
from the Instagram-login token.

Env:
  FB_PAGE_ID      Facebook Page id (numeric, e.g. 61591212507178)
  FB_PAGE_TOKEN   Page access token with pages_manage_posts (ideally non-expiring)
  GRAPH_BASE      default https://graph.facebook.com
  GRAPH_VERSION   default v21.0

Usage:
  python fb_publish.py --image-url https://.../post.png --caption-file caption.txt
"""
import argparse, os, sys
import requests


def cfg():
    return (os.environ.get("GRAPH_BASE", "https://graph.facebook.com"),
            os.environ.get("GRAPH_VERSION", "v21.0"),
            os.environ.get("FB_PAGE_ID"),
            os.environ.get("FB_PAGE_TOKEN"))


def publish_photo(image_url, caption, dry=False):
    base, ver, pid, tok = cfg()
    if dry:
        print(f"POST {base}/{ver}/{pid}/photos  url={image_url}", file=sys.stderr)
        return "DRYRUN", ""
    r = requests.post(f"{base}/{ver}/{pid}/photos",
                      params={"url": image_url, "caption": caption, "access_token": tok},
                      timeout=60)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} {r.text}")
    j = r.json()
    post_id = j.get("post_id") or j.get("id")
    link = ""
    try:
        pl = requests.get(f"{base}/{ver}/{post_id}",
                          params={"fields": "permalink_url", "access_token": tok}, timeout=30).json()
        link = pl.get("permalink_url", "")
    except Exception:
        pass
    return post_id, link


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-url", required=True)
    ap.add_argument("--caption", default="")
    ap.add_argument("--caption-file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    caption = a.caption
    if a.caption_file:
        caption = open(a.caption_file, encoding="utf-8").read().strip()

    _, _, pid, tok = cfg()
    if not a.dry_run and (not pid or not tok):
        sys.exit("ERROR: set FB_PAGE_ID and FB_PAGE_TOKEN (or use --dry-run).")

    post_id, link = publish_photo(a.image_url, caption, a.dry_run)
    print(f"[ok] facebook post id: {post_id}")
    if link:
        print(f"permalink: {link}")


if __name__ == "__main__":
    main()
