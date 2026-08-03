#!/usr/bin/env python3
"""Pull @namecode_original account + recent-media insights from the Graph API.

Writes/updates `namecode_grid/metrics/ig_metrics.json` (one snapshot per run,
appended) so growth is trackable in-repo, and prints a human summary.
The marketing context doc (.agents/product-marketing.md) references this file.

Env (same conventions as ig_publish.py):
  IG_USER_ID        Instagram Business/Creator user id (numeric)
  IG_ACCESS_TOKEN   long-lived token (instagram_manage_insights scope needed
                    on top of the publish scopes)
  GRAPH_BASE        default https://graph.facebook.com
  GRAPH_VERSION     default v21.0

Usage:
  python ig_insights.py             # snapshot account + last 25 media
  python ig_insights.py --media 50  # look further back
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

import requests

BASE = os.environ.get("GRAPH_BASE", "https://graph.facebook.com")
VER = os.environ.get("GRAPH_VERSION", "v21.0")
OUT = pathlib.Path(__file__).parent / "metrics" / "ig_metrics.json"

# saves + shares(=sends) are the two signals namecode optimizes for (2026).
MEDIA_METRICS = "saved,shares,reach,likes,comments,total_interactions"


def api(path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.get(f"{BASE}/{VER}/{path}", params=params, timeout=30)
    if not r.ok:
        sys.exit(f"Graph API {r.status_code}: {r.text[:300]}")
    return r.json()


def snapshot(media_limit: int) -> dict:
    uid = os.environ["IG_USER_ID"]
    account = api(uid, fields="username,followers_count,media_count")

    media = api(
        f"{uid}/media",
        fields="id,caption,media_type,timestamp,permalink",
        limit=media_limit,
    ).get("data", [])

    posts = []
    for m in media:
        try:
            ins = api(f"{m['id']}/insights", metric=MEDIA_METRICS)
            values = {d["name"]: d["values"][0]["value"] for d in ins.get("data", [])}
        except SystemExit:
            values = {}  # older media types can reject some metrics
        posts.append(
            {
                "id": m["id"],
                "timestamp": m.get("timestamp"),
                "type": m.get("media_type"),
                "permalink": m.get("permalink"),
                "caption_head": (m.get("caption") or "")[:80],
                **values,
            }
        )

    return {
        "taken_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "account": account,
        "posts": posts,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", type=int, default=25, help="media items to inspect")
    args = ap.parse_args()

    for var in ("IG_USER_ID", "IG_ACCESS_TOKEN"):
        if not os.environ.get(var):
            sys.exit(f"{var} is not set — see README_ig.md for token setup.")

    snap = snapshot(args.media)

    OUT.parent.mkdir(exist_ok=True)
    history = json.loads(OUT.read_text()) if OUT.exists() else []
    history.append(snap)
    OUT.write_text(json.dumps(history, indent=2, ensure_ascii=False))

    acc = snap["account"]
    print(f"@{acc.get('username')}: {acc.get('followers_count')} followers, "
          f"{acc.get('media_count')} posts")
    ranked = sorted(snap["posts"], key=lambda p: (p.get("saved", 0) + p.get("shares", 0)), reverse=True)
    print("top posts by saves+sends:")
    for p in ranked[:5]:
        print(f"  saves={p.get('saved', 0):>3} sends={p.get('shares', 0):>3} "
              f"reach={p.get('reach', 0):>5}  {p['caption_head']}")
    print(f"snapshot appended to {OUT}")


if __name__ == "__main__":
    main()
