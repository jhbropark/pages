#!/usr/bin/env python3
"""Assemble the daily reel with digital-art hooks — the DECODE 3-act structure.

Act 1  HOOK   (~2.5s)  the artwork resolves out of mono glyph noise under a
                       scanline sweep while the label types on with a cursor
                       and the astro value counts up from zero.
Act 2  MOTION (~10s×3) the Kling boomerang clip, repeated —
Act 3  GLITCH BEATS    with 8-frame slice-shift glitches at every loop
                       boundary (hides the repeat, adds rhythm), closing on a
                       2s still card of the labeled artwork.

Everything here is deterministic PIL/ffmpeg — the hook never depends on what
the video model happened to generate. Seeded by the APOD date so a given day
always renders the same reel.
"""
import math, os, random, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
GLYPHS = "01<>[]{}#%&*+=-.:/\\|abcdefxyz"
CELL = 24          # glyph grid cell (px) at full res
PAPER = (250, 250, 248)


def ffmpeg_exe():
    from shutil import which
    return which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


def load_font(size):
    for path in (os.environ.get("NAMECODE_FONT"),
                 "/tmp/fnt/JetBrainsMono.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def _ease(t):
    return t * t * (3 - 2 * t)  # smoothstep


def _draw_label(d, label, font):
    """Same pill style as apod_namecode.compose()."""
    x, y, pad = 40, 40, 14
    tw = d.textlength(label, font=font)
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + font.size + 22],
                        radius=6, fill=(18, 18, 18, 230))
    d.text((x + pad, y + 11), label, font=font, fill=PAPER)


def _split_label(label):
    """'namecode - NAME | 73.498' -> ('namecode - NAME | ', '73.498')."""
    if "|" in label:
        head, _, val = label.rpartition("|")
        return head + "| ", val.strip()
    return label, ""


def _fmt_like(value, x):
    """Format x with the same decimal places as the target value string."""
    try:
        dec = len(value.split(".")[1]) if "." in value else 0
        num = float(value.replace(",", "").split()[0])
        unit = value[len(value.split()[0]):]
        return f"{x * num:.{dec}f}{unit}"
    except Exception:
        return value


def render_hook(still, label, outdir, rng, seconds=2.5):
    """Glyph-noise decode of the still + typewriter label + value count-up."""
    n = int(seconds * FPS)
    base = still
    font = load_font(max(22, W // 34))
    gfont = load_font(CELL - 4)
    head, value = _split_label(label)
    cols, rows = W // CELL, H // CELL
    # per-cell dissolve threshold so cells resolve in a fixed random order
    cell_thr = {(c, r): rng.random() for c in range(cols) for r in range(rows)}
    for i in range(n):
        t = _ease(i / max(1, n - 1))
        img = base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        sweep = int(H * t)  # scanline position: above = decoded
        for r in range(rows):
            y = r * CELL
            if y <= sweep:
                continue
            for c in range(cols):
                # cells below the sweep still show glyph noise until their
                # own dissolve threshold passes
                if cell_thr[(c, r)] < t * 0.8:
                    continue
                d.rectangle([c * CELL, y, c * CELL + CELL, y + CELL], fill=(12, 12, 12))
                if rng.random() < 0.55:
                    d.text((c * CELL + 3, y + 1), rng.choice(GLYPHS),
                           font=gfont, fill=(120, 120, 118))
        if sweep < H:  # bright scanline at the decode boundary
            d.rectangle([0, sweep, W, sweep + 3], fill=(250, 250, 248, 160))
        # typewriter label: type the head, then count the value up
        if t < 0.6:
            k = int(len(head) * (t / 0.6))
            txt = head[:k] + ("█" if i % 10 < 5 else "")
        else:
            v = _ease(min(1.0, (t - 0.6) / 0.38))
            txt = head + (_fmt_like(value, v) if value else "")
        _draw_label(d, txt, font)
        img.save(os.path.join(outdir, f"{i:05d}.png"))
    return n


def render_glitch(frame, outdir, rng, n=8):
    """Slice-shift glitch burst from a single frame (loop-boundary beat)."""
    for i in range(n):
        img = frame.copy()
        for _ in range(rng.randint(6, 12)):
            y = rng.randint(0, H - 40)
            h = rng.randint(8, 60)
            dx = rng.randint(-90, 90)
            band = img.crop((0, y, W, y + h))
            img.paste(band, (dx, y))
        if rng.random() < 0.4:  # occasional negative flash band
            y = rng.randint(0, H - 200)
            from PIL import ImageOps as _Ops
            band = _Ops.invert(img.crop((0, y, W, y + rng.randint(60, 180))))
            img.paste(band, (0, y))
        img.save(os.path.join(outdir, f"{i:05d}.png"))
    return n


def _encode_frames(outdir, seg_path):
    subprocess.run([ffmpeg_exe(), "-y", "-framerate", str(FPS),
                    "-i", os.path.join(outdir, "%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    seg_path], check=True, capture_output=True)


def _encode_still(still_path, seconds, seg_path):
    subprocess.run([ffmpeg_exe(), "-y", "-loop", "1", "-i", still_path,
                    "-t", str(seconds), "-r", str(FPS),
                    "-vf", f"scale={W}:{H},setsar=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    seg_path], check=True, capture_output=True)


def _last_frame(video, png):
    subprocess.run([ffmpeg_exe(), "-y", "-sseof", "-0.2", "-i", video,
                    "-frames:v", "1", png], check=True, capture_output=True)


def assemble(still_path, motion_mp4, label, out, seed="namecode", motion_repeats=3):
    """hook -> (motion -> glitch)×N -> end card, concatenated to `out`."""
    rng = random.Random(seed)
    still = Image.open(still_path).convert("RGB").resize((W, H))
    tmp = tempfile.mkdtemp(prefix="reelfx_")
    try:
        segs = []
        hookdir = os.path.join(tmp, "hook"); os.makedirs(hookdir)
        render_hook(still, label, hookdir, rng)
        seg = os.path.join(tmp, "seg_hook.mp4"); _encode_frames(hookdir, seg)
        segs.append(seg)

        lastpng = os.path.join(tmp, "last.png")
        _last_frame(motion_mp4, lastpng)
        last = Image.open(lastpng).convert("RGB").resize((W, H))
        for k in range(motion_repeats):
            segs.append(motion_mp4)
            gdir = os.path.join(tmp, f"g{k}"); os.makedirs(gdir)
            render_glitch(last if k < motion_repeats - 1 else still, gdir, rng)
            seg = os.path.join(tmp, f"seg_g{k}.mp4"); _encode_frames(gdir, seg)
            segs.append(seg)

        endpng = os.path.join(tmp, "end.png"); still.save(endpng)
        seg = os.path.join(tmp, "seg_end.mp4"); _encode_still(endpng, 2, seg)
        segs.append(seg)

        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w") as fh:
            for s in segs:
                fh.write(f"file '{os.path.abspath(s)}'\n")
        subprocess.run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "20", "-r", str(FPS),
                        "-movflags", "+faststart", "-an", out], check=True)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
