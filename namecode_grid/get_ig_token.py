#!/usr/bin/env python3
"""Turn a short-lived Meta token into IG_ACCESS_TOKEN + IG_USER_ID.

Run this on YOUR machine (it needs to reach graph.facebook.com /
graph.instagram.com, and the short token must come from your own login).

Instagram-login app ("Instagram messaging & content" use case, IGAA… token):
  python get_ig_token.py --type instagram \
      --app-secret  $APP_SECRET \
      --short-token $SHORT_TOKEN

Facebook-login app (EAA… token):
  python get_ig_token.py --type facebook \
      --app-id $APP_ID --app-secret $APP_SECRET --short-token $SHORT_TOKEN

Prints the two values to paste into GitHub Secrets:
  IG_ACCESS_TOKEN, IG_USER_ID
"""
import argparse, json, sys, urllib.parse, urllib.request

V = "v21.0"


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def instagram(app_secret, short):
    # short -> long-lived (60d)
    q = urllib.parse.urlencode({"grant_type": "ig_exchange_token",
                                "client_secret": app_secret, "access_token": short})
    tok = get(f"https://graph.instagram.com/access_token?{q}")["access_token"]
    me = get(f"https://graph.instagram.com/{V}/me?"
             + urllib.parse.urlencode({"fields": "user_id,username", "access_token": tok}))
    return tok, str(me.get("user_id") or me.get("id")), me.get("username")


def facebook(app_id, app_secret, short):
    q = urllib.parse.urlencode({"grant_type": "fb_exchange_token", "client_id": app_id,
                                "client_secret": app_secret, "fb_exchange_token": short})
    long_user = get(f"https://graph.facebook.com/{V}/oauth/access_token?{q}")["access_token"]
    accts = get(f"https://graph.facebook.com/{V}/me/accounts?"
                + urllib.parse.urlencode({"access_token": long_user, "fields":
                                          "name,access_token,instagram_business_account"}))
    for page in accts.get("data", []):
        iba = page.get("instagram_business_account")
        if iba:
            return page["access_token"], iba["id"], page.get("name")
    sys.exit("No Page with a linked instagram_business_account found. "
             "Link @namecode_original to a Facebook Page first.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=["instagram", "facebook"], required=True)
    ap.add_argument("--app-id")
    ap.add_argument("--app-secret", required=True)
    ap.add_argument("--short-token", required=True)
    a = ap.parse_args()
    if a.type == "instagram":
        tok, uid, name = instagram(a.app_secret, a.short_token)
    else:
        if not a.app_id:
            sys.exit("--app-id is required for --type facebook")
        tok, uid, name = facebook(a.app_id, a.app_secret, a.short_token)
    print(f"\n# account: {name}")
    print(f"IG_USER_ID={uid}")
    print(f"IG_ACCESS_TOKEN={tok}\n")
    print("→ Paste these into GitHub → Settings → Secrets → Actions "
          "(do NOT commit them).")


if __name__ == "__main__":
    main()
