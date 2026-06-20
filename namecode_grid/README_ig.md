# namecode → Instagram auto-publish

`ig_publish.py` posts a finished namecode artwork (feed image or reel) to
**@namecode_original** via the Meta Graph API. It chains onto `apod_namecode.py`
so the full path is:

```
APOD API → Krea image → duotone + mono label → host (public URL) → IG publish
```

## One-time setup (account owner)

1. **Convert** @namecode_original to a **Business or Creator** account.
2. **Link** it to a **Facebook Page** (Instagram → Settings → linked Page).
3. In **Meta for Developers**: create an app, add *Instagram Graph API*, and
   issue a **long-lived access token** with the **`instagram_content_publish`**
   (and `pages_show_list`, `business_management`) permissions.
4. Get the numeric **IG user id** (`GET /me/accounts` → page → `instagram_business_account`).
5. Add **`graph.facebook.com`** to the environment **egress allowlist**.

```bash
export IG_USER_ID=178414...           # numeric Business account id
export IG_ACCESS_TOKEN=EAAG...        # long-lived token
```

## Hosting the image (required)

Graph API needs a **public https URL**, not a local file. Options for the
composited PNG (the one with the mono label):

- Commit it to a **public** repo and use the `raw.githubusercontent.com` URL.
- Upload to S3 / Cloudinary / imgur and use that URL.
- If you don't need the baked-in label, post the **Krea result URL** directly
  (already public).

## Usage

```bash
# feed image
python ig_publish.py --image-url https://.../namecode_apod_2026-06-20.png \
                     --caption-file caption_apod.txt

# reel
python ig_publish.py --reel --video-url https://.../reel.mp4 \
                     --cover-url https://.../cover.png --caption "..."

# preview the exact Graph calls without posting
python ig_publish.py --image-url https://.../post.png --caption "..." --dry-run
```

## Full daily chain (once everything is wired)

```bash
# 1) generate today's piece from APOD
python apod_namecode.py --out today.png          # also prints the brief JSON

# 2) host today.png somewhere public  ->  $URL

# 3) publish
python ig_publish.py --image-url "$URL" --caption-file caption_apod.txt
```

Schedule steps 1–3 with cron or a GitHub Action for a hands-off daily post.

## Status

- Flow verified with `--dry-run` (image 2-step, reel 3-step with status polling);
  the token is masked in logs.
- Live posting needs the setup above + `graph.facebook.com` on the allowlist.
