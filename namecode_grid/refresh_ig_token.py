#!/usr/bin/env python3
"""Refresh the long-lived Instagram-login token and store it back as a secret.

Instagram-login (IGAA…) long-lived tokens last 60 days and can be refreshed
for another 60 (when 24h–60d old). Run this monthly so the token never lapses.

Env:
  IG_ACCESS_TOKEN  current long-lived token (IGAA…)
  GH_PAT           GitHub fine-grained PAT with "Secrets: write" on this repo
                   (only then is the refreshed token written back automatically)
  GITHUB_REPOSITORY  owner/repo (set by Actions)
"""
import base64, os, sys, requests
from nacl import public


def refresh(token):
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    r.raise_for_status()
    j = r.json()
    return j["access_token"], j.get("expires_in")


def update_secret(repo, pat, name, value):
    h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
    pk = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
                      headers=h, timeout=30).json()
    sealed = public.SealedBox(public.PublicKey(base64.b64decode(pk["key"]))).encrypt(value.encode())
    r = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/{name}", headers=h,
                     json={"encrypted_value": base64.b64encode(sealed).decode(),
                           "key_id": pk["key_id"]}, timeout=30)
    r.raise_for_status()


def main():
    tok = os.environ.get("IG_ACCESS_TOKEN")
    if not tok:
        sys.exit("IG_ACCESS_TOKEN not set")
    new, exp = refresh(tok)
    print(f"refreshed; expires_in≈{exp}s (~{int((exp or 0)/86400)}d)")
    pat = os.environ.get("GH_PAT")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if pat and repo:
        update_secret(repo, pat, "IG_ACCESS_TOKEN", new)
        print("IG_ACCESS_TOKEN secret updated.")
    else:
        print("GH_PAT not set — token refreshed but NOT stored. Set GH_PAT to auto-store.")


if __name__ == "__main__":
    main()
