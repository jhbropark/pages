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
                         params={"fields": "id,name,access_token", "access_token": token},
                         timeout=30)
        if r.ok:
            pages = r.json().get("data", [])
            for pg in pages:
                if str(pg.get("id")) == str(page_id) and pg.get("access_token"):
                    print("[info] resolved page token from user token via /me/accounts",
                          file=sys.stderr)
                    return pg["access_token"]
            if pages:
                # A user token that administers pages, but none of them is
                # FB_PAGE_ID — usually FB_PAGE_ID holds the personal account id
                # instead of a Page id, which makes every post look like an
                # attempt to publish to a user timeline ("publish_actions").
                print(f"[warn] FB_PAGE_ID={page_id} is not one of the pages this "
                      "token administers. Set it to one of:", file=sys.stderr)
                for pg in pages:
                    print(f"         {pg.get('id')}  {pg.get('name')!r}", file=sys.stderr)
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
    # print the whole body: Meta packs the actual requirement into the tail of
    # the message ("...requires both pages_read_engagement and pages_manage_posts")
    print(f"[warn] /{edge} -> {r.status_code} {r.text}", file=sys.stderr)
    return None


def diagnose(base, ver, pid, tok):
    """Print who the token is and what it may do, so a (#200) is actionable.

    Never prints the token itself. The three questions a publish failure turns
    on: is this a *page* token or a *user* token, is it for the page we post
    to, and does it carry CREATE_CONTENT (pages_manage_posts).
    """
    print("--- facebook token diagnosis ---", file=sys.stderr)

    def _get(path, fields):
        try:
            r = requests.get(f"{base}/{ver}/{path}",
                             params={"fields": fields, "access_token": tok}, timeout=30)
            return r.json()
        except Exception as e:
            return {"error": {"message": str(e)}}

    me = _get("me", "id,name")
    me_id, me_name = me.get("id"), me.get("name")
    print(f"token identity: /me -> id={me_id} name={me_name!r}", file=sys.stderr)
    print(f"FB_PAGE_ID    : {pid}", file=sys.stderr)

    # A dead token fails *every* Graph call, so nothing below can say anything
    # about page identity — /me comes back empty and the page lookups look like
    # "not a Page you administer". Stop here instead of reporting that as a
    # conclusion; code 190 is about the token, never about FB_PAGE_ID.
    err = me.get("error") or {}
    if err.get("code") == 190:
        print(f"[!] token is INVALID/EXPIRED: {err.get('message')}", file=sys.stderr)
        print("    Re-issue FB_PAGE_TOKEN. Prefer a long-lived *user* token: a "
              "page token derived from one (which resolve_page_token does via "
              "/me/accounts) does not expire, so the daily run stops breaking "
              "every time a short-lived token lapses.", file=sys.stderr)
        print("    No conclusion about FB_PAGE_ID can be drawn while the token "
              "is dead — re-run the diagnosis after replacing it.", file=sys.stderr)
        print("--- end diagnosis ---", file=sys.stderr)
        return

    # /me/accounts only ever returns data for a *user* token, so a non-empty
    # list settles what kind of token this is — matching ids do not (if
    # FB_PAGE_ID holds the personal account id, /me matches it and the token
    # is still a user token).
    pages = _get("me/accounts", "id,name").get("data")
    if pages:
        print("token kind    : USER token (administers "
              f"{len(pages)} page(s))", file=sys.stderr)
        for pg in pages:
            print(f"  page: {pg.get('id')}  {pg.get('name')!r}", file=sys.stderr)
        if not any(str(pg.get("id")) == str(pid) for pg in pages):
            print("[!] FB_PAGE_ID is not any of those pages. If it equals the "
                  "/me id above, it is the personal account id — posting there "
                  "is what returns 'publish_actions is deprecated'. Set "
                  "FB_PAGE_ID to one of the page ids listed above; the page "
                  "token is then resolved automatically.", file=sys.stderr)
    else:
        print("token kind    : PAGE token (or /me/accounts unavailable)", file=sys.stderr)
        if me_id and str(me_id) != str(pid):
            print("[!] token does NOT belong to FB_PAGE_ID — set FB_PAGE_ID to "
                  f"{me_id}, or issue a token for the page you meant.",
                  file=sys.stderr)

    tasks = _get(pid, "tasks").get("tasks")
    print(f"page tasks    : {tasks}", file=sys.stderr)
    if tasks is None:
        print("[!] no `tasks` on FB_PAGE_ID — that id is not a Page you "
              "administer (a personal account has no tasks).", file=sys.stderr)
    elif "CREATE_CONTENT" not in tasks:
        print("[!] CREATE_CONTENT missing — this token cannot publish. Re-issue "
              "it with pages_read_engagement AND pages_manage_posts.",
              file=sys.stderr)

    perms = _get("me/permissions", "")
    granted = sorted(p["permission"] for p in perms.get("data", [])
                     if p.get("status") == "granted")
    if granted:
        print(f"granted scopes: {', '.join(granted)}", file=sys.stderr)
        for need in ("pages_read_engagement", "pages_manage_posts"):
            if need not in granted:
                print(f"[!] missing scope: {need}", file=sys.stderr)
    print("--- end diagnosis ---", file=sys.stderr)


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
        diagnose(base, ver, pid, tok)
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
        diagnose(base, ver, pid, tok)
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
    ap.add_argument("--diagnose", action="store_true",
                    help="report who FB_PAGE_TOKEN is and what it may do, then exit")
    a = ap.parse_args()

    caption = a.caption
    if a.caption_file:
        caption = open(a.caption_file, encoding="utf-8").read().strip()

    base, ver, pid, tok = cfg()
    if a.diagnose:
        if not pid or not tok:
            sys.exit("ERROR: set FB_PAGE_ID and FB_PAGE_TOKEN.")
        diagnose(base, ver, pid, tok)
        return
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
