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


def resolve_page_token(base, ver, page_id, token):
    """Return a Page access token for `page_id`.

    Posting to /{page}/photos requires the *page* token, not a *user* token —
    a user token there fails with "(#200) ... publish_actions ... deprecated".
    User and page tokens look almost identical (same EAA… app prefix), so this
    accepts either: if `token` is a user token, look up the matching page token
    via /me/accounts; if it's already a page token (that call returns nothing),
    use it as-is.
    """
    try:
        r = requests.get(f"{base}/{ver}/me/accounts",
                         params={"fields": "id,access_token", "access_token": token},
                         timeout=30)
        if r.ok:
            for pg in r.json().get("data", []):
                if str(pg.get("id")) == str(page_id) and pg.get("access_token"):
                    print("[info] resolved page token from user token via /me/accounts",
                          file=sys.stderr)
                    return pg["access_token"]
    except Exception:
        pass
    return token


def permalink(base, ver, post_id, tok):
    try:
        pl = requests.get(f"{base}/{ver}/{post_id}",
                          params={"fields": "permalink_url", "access_token": tok}, timeout=30).json()
        return pl.get("permalink_url", "")
    except Exception:
        return ""


def _try_post(base, ver, pid, edge, params, timeout):
    """POST to /{page}/{edge}; return the parsed json, or None with a logged reason."""
    r = requests.post(f"{base}/{ver}/{pid}/{edge}", params=params, timeout=timeout)
    if r.ok:
        return r.json()
    print(f"[warn] /{edge} -> {r.status_code} {r.text[:300]}", file=sys.stderr)
    return None


def publish_photo(image_url, caption, dry=False):
    """Post the daily artwork to the Page.

    Tries the native photo edge first (best presentation: a real photo post),
    then falls back to /{page}/feed with the image as a `link`. Pages on the
    New Pages Experience reject /photos with "(#200) This endpoint is
    deprecated since the required permission publish_actions is deprecated",
    and /feed is the path that still works there.
    """
    base, ver, pid, tok = cfg()
    if dry:
        print(f"POST {base}/{ver}/{pid}/photos  url={image_url}", file=sys.stderr)
        print(f"  fallback: POST {base}/{ver}/{pid}/feed  link={image_url}", file=sys.stderr)
        return "DRYRUN", ""
    tok = resolve_page_token(base, ver, pid, tok)

    j = _try_post(base, ver, pid, "photos",
                  {"url": image_url, "caption": caption, "access_token": tok}, 60)
    if j is None:
        print("[info] falling back to /feed (New Pages Experience)", file=sys.stderr)
        j = _try_post(base, ver, pid, "feed",
                      {"link": image_url, "message": caption, "access_token": tok}, 60)
    if j is None:
        raise RuntimeError("facebook photo publish failed on both /photos and /feed")

    post_id = j.get("post_id") or j.get("id")
    return post_id, permalink(base, ver, post_id, tok)


def publish_video(video_url, caption, dry=False):
    """Post a video to the Page via /{page}/videos with a remote file_url.

    Same fallback shape as publish_photo: if the video edge is unavailable on
    this Page, post the video URL as a /feed link instead.
    """
    base, ver, pid, tok = cfg()
    if dry:
        print(f"POST {base}/{ver}/{pid}/videos  file_url={video_url}", file=sys.stderr)
        print(f"  fallback: POST {base}/{ver}/{pid}/feed  link={video_url}", file=sys.stderr)
        return "DRYRUN", ""
    tok = resolve_page_token(base, ver, pid, tok)

    j = _try_post(base, ver, pid, "videos",
                  {"file_url": video_url, "description": caption, "access_token": tok}, 120)
    if j is not None:
        vid = j.get("id")
        return vid, (f"https://www.facebook.com/{pid}/videos/{vid}" if vid else "")

    print("[info] falling back to /feed (New Pages Experience)", file=sys.stderr)
    j = _try_post(base, ver, pid, "feed",
                  {"link": video_url, "message": caption, "access_token": tok}, 60)
    if j is None:
        raise RuntimeError("facebook video publish failed on both /videos and /feed")
    post_id = j.get("post_id") or j.get("id")
    return post_id, permalink(base, ver, post_id, tok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-url")
    ap.add_argument("--video-url", help="post a video instead of a photo")
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

    if a.video_url:
        post_id, link = publish_video(a.video_url, caption, a.dry_run)
        print(f"[ok] facebook video id: {post_id}")
    elif a.image_url:
        post_id, link = publish_photo(a.image_url, caption, a.dry_run)
        print(f"[ok] facebook post id: {post_id}")
    else:
        sys.exit("ERROR: provide --image-url or --video-url")
    if link:
        print(f"permalink: {link}")


if __name__ == "__main__":
    main()
