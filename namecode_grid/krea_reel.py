#!/usr/bin/env python3
"""Generate a 9:16 reel from the daily still via Krea image-to-video.

The daily artwork (with its mono label already baked in) is the start_image, so
the label rides along in the motion. Mirrors apod_namecode.py's Krea calls:
POST /generate/video/{path} -> job_id, then poll /jobs/{id} -> result url.
Whatever aspect Krea returns is normalized to 1080x1920 with a blurred fill via
ffmpeg, so the output is always a clean vertical reel.

Env:
  KREA_API_KEY      required (unless --dry-run)
  KREA_BASE         default https://api.krea.ai
  KREA_VIDEO_PATH   model path under /generate/video/ (default "kling")

Usage:
  python krea_reel.py --image-url https://.../art.png \
      --brief daily/brief_DATE.json --out daily/reel_DATE.mp4
"""
import argparse, json, os, subprocess, sys, time
import requests

REEL_W, REEL_H = 1080, 1920
STYLE = ("Dark astronomical scene, fine white particles like stars, high-contrast "
         "monochrome, cinematic film grain. Vertical 9:16.")
# One motion per day, chosen by date seed — never the same slow zoom twice in a row.
MOTIONS = [
    "Slow orbital drift around the subject, background stars sliding in parallax.",
    "Lateral dolly glide with layered depth parallax, foreground dust drifting past.",
    "A sweep of light crosses the scene, particles igniting and fading in its wake.",
    "Particles surge inward, converge on the subject, then disperse outward.",
    "Slow pull-back reveal from an extreme close-up detail to the full composition.",
    "The subject rotates almost imperceptibly while star trails arc around it.",
    "Rising vertical drift, as if ascending past the subject through falling dust.",
]
DEFAULT_PROMPT = MOTIONS[0] + " " + STYLE


def krea_video(image_url, prompt):
    base = os.environ.get("KREA_BASE", "https://api.krea.ai")
    key = os.environ["KREA_API_KEY"]
    body = {"prompt": prompt, "start_image": image_url}
    hdr = {"Authorization": f"Bearer {key}"}
    # Model slugs are provider/version, per vendor/krea-mcp-server VIDEO_MODELS
    # (e.g. "kling/kling-1.6", "minimax/hailuo"). Allow an env override, else
    # try known slugs and use the first the API routes (404 -> next).
    env_path = os.environ.get("KREA_VIDEO_PATH")
    candidates = [env_path] if env_path else [
        "kling/kling-1.6", "kling/kling-2.5", "minimax/hailuo"]
    last = None
    for path in candidates:
        r = requests.post(f"{base}/generate/video/{path}", json=body,
                          headers=hdr, timeout=60)
        if r.ok:
            print(f"[info] krea video model path: {path}", file=sys.stderr)
            return r.json()["job_id"]
        last = f"{r.status_code} {r.text}"
        print(f"[warn] krea video path '{path}' -> {last}", file=sys.stderr)
        if r.status_code not in (400, 404, 422):
            break  # auth/balance/server errors won't be fixed by another path
    raise RuntimeError(f"krea video POST failed: {last}")


def krea_wait(job_id, timeout=900):
    base = os.environ.get("KREA_BASE", "https://api.krea.ai")
    key = os.environ["KREA_API_KEY"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get(f"{base}/jobs/{job_id}",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        r.raise_for_status()
        j = r.json()
        st = j.get("status")
        if st == "completed":
            # tolerate a few result shapes: {result:{urls:[..]}} / {urls:[..]} /
            # {result:[..]} / {result:{url:..}}
            res = j.get("result")
            urls = []
            if isinstance(res, dict):
                urls = res.get("urls") or ([res["url"]] if res.get("url") else [])
            elif isinstance(res, list):
                urls = res
            urls = urls or j.get("urls") or []
            if not urls:
                raise RuntimeError(f"krea completed but no result url: {j}")
            return urls[0]
        if st == "failed":
            raise RuntimeError(f"krea video failed: {j}")
        time.sleep(5)
    raise TimeoutError("krea video timed out")


def ffmpeg_exe():
    """Prefer a system ffmpeg; fall back to the imageio-ffmpeg static binary."""
    from shutil import which
    return which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


def normalize_vertical(src, out, min_seconds=30):
    """Fit any aspect into 1080x1920 over a blurred fill (no subject cropping),
    boomerang (forward+reverse) for a seamless loop, then repeat the boomerang
    until the reel is at least `min_seconds` (brand spec: reels run 30-90s)."""
    vf = (f"[0:v]scale={REEL_W}:{REEL_H}:force_original_aspect_ratio=increase,"
          f"crop={REEL_W}:{REEL_H},boxblur=22:8[bg];"
          f"[0:v]scale={REEL_W}:{REEL_H}:force_original_aspect_ratio=decrease[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v];"
          f"[v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[out]")
    boom = out + ".boom.mp4"
    subprocess.run([ffmpeg_exe(), "-y", "-i", src, "-filter_complex", vf,
                    "-map", "[out]", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", boom], check=True)
    # measure the boomerang and loop it enough times to clear min_seconds
    import re as _re
    probe = subprocess.run([ffmpeg_exe(), "-i", boom], capture_output=True, text=True)
    m = _re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
    dur = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else 10.0
    import math
    loops = max(0, math.ceil(min_seconds / dur) - 1)  # extra repeats beyond the first
    subprocess.run([ffmpeg_exe(), "-y", "-stream_loop", str(loops), "-i", boom,
                    "-c", "copy", "-movflags", "+faststart", out], check=True)
    try:
        os.remove(boom)
    except OSError:
        pass


def main():
    import random
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-url", required=True, help="public URL of the daily still (start_image)")
    ap.add_argument("--still", help="local path to the labeled 9:16 still (enables the DECODE hook)")
    ap.add_argument("--brief", help="brief JSON (label/date + scene guidance)")
    ap.add_argument("--prompt", help="override motion prompt")
    ap.add_argument("--out", required=True, help="output mp4 path (normalized 1080x1920)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    label, seed = "", "namecode"
    brief = {}
    if a.brief and os.path.exists(a.brief):
        try:
            brief = json.load(open(a.brief, encoding="utf-8"))
            label = brief.get("label", "")
            seed = brief.get("date", seed)
        except Exception:
            pass
    # date-seeded motion: a different camera/particle move every day
    motion = random.Random(seed).choice(MOTIONS)
    prompt = a.prompt or f"{motion} {STYLE}"
    if brief.get("prompt"):
        prompt = f"{prompt} Scene: {brief['prompt']}".strip()
    print(f"[info] motion: {motion}", file=sys.stderr)

    if a.dry_run:
        print(f"[dry-run] would generate video from {a.image_url}", file=sys.stderr)
        return

    job = krea_video(a.image_url, prompt)
    print(f"[info] krea video job: {job}", file=sys.stderr)
    url = krea_wait(job)
    print(f"[info] krea video url: {url}", file=sys.stderr)

    raw = a.out + ".krea.mp4"
    with open(raw, "wb") as fh:
        fh.write(requests.get(url, timeout=120).content)

    if a.still and os.path.exists(a.still) and label:
        # DECODE 3-act assembly: glyph-decode hook -> motion + glitch beats -> end card
        boom = a.out + ".boom.mp4"
        normalize_vertical(raw, boom, min_seconds=0)  # single boomerang, no plain loop
        import reel_fx
        reel_fx.assemble(a.still, boom, label, a.out, seed=seed)
        for f in (boom,):
            try:
                os.remove(f)
            except OSError:
                pass
    else:
        normalize_vertical(raw, a.out)  # fallback: plain 30s boomerang loop
    try:
        os.remove(raw)
    except OSError:
        pass
    print(f"[ok] reel: {a.out}")


if __name__ == "__main__":
    main()
