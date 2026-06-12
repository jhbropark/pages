#!/usr/bin/env python3
"""Diagnose Instagram Login API access without printing credentials."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"].strip()
BASE = "https://graph.instagram.com/v23.0"


def get(path: str, fields: str = "") -> tuple[int, dict]:
    params = {"access_token": TOKEN}
    if fields:
        params["fields"] = fields
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body[:500]}
        return exc.code, payload


def summarize(name: str, status: int, payload: dict) -> None:
    if status < 400:
        safe = {
            key: payload.get(key)
            for key in ("id", "user_id", "username", "account_type", "media_count")
            if key in payload
        }
        if "data" in payload:
            safe["data"] = payload["data"]
        print(f"{name}: HTTP {status} {json.dumps(safe, ensure_ascii=False)}")
        return

    error = payload.get("error", {})
    safe_error = {
        key: error.get(key)
        for key in ("message", "type", "code", "error_subcode", "is_transient")
        if key in error
    }
    print(f"{name}: HTTP {status} {json.dumps(safe_error, ensure_ascii=False)}")


for name, path, fields in (
    ("profile", "me", "id,user_id,username,account_type,media_count"),
    ("permissions", "me/permissions", ""),
    ("publishing_limit", "me/content_publishing_limit", "config,quota_usage"),
):
    summarize(name, *get(path, fields))
