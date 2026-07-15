#!/usr/bin/env python3
"""Assemble the daily reel as a continuous, non-repeating particle piece.

The hook — and the through-line of the whole reel — is a field of fine white
particles on black (the namecode / FUSE* signature). One unified particle
simulation runs across the entire timeline, so nothing ever visibly loops:

  Act 1  REVEAL (~2.6s)  particles scattered across frame converge onto the
                         artwork's bright regions, "painting" the sky into
                         existence as it fades up; label types on, value
                         counts up.
  Act 2  DRIFT  (~25s)   the settled particles keep drifting — continuous
                         sinusoidal parallax, every position a function of
                         absolute time, so the field never repeats — over a
                         slow motion-trailed pass of the Kling clip (single
                         boomerang, no ×N loop).
  Act 3  SETTLE (~2.4s)  motion holds on a labeled end card while particles
                         drift on, easing to a quiet close.

Particles are composited with a screen blend (white-on-black adds only the
specks). Everything is deterministic numpy/PIL/ffmpeg, seeded by the APOD date
— the hook never depends on what the video model generated.
"""
import math, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
PAPER = (250, 250, 248)
N_PARTICLES = 220
HOOK_SEC, FLOW_SEC, END_SEC = 2.6, 25.0, 2.4


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
    except TypeError:
        return ImageFont.load_default()


def _ease(t):
    return t * t * (3 - 2 * t)  # smoothstep


def _draw_label(d, label, font):
    x, y, pad = 40, 40, 14
    tw = d.textlength(label, font=font)
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + font.size + 22],
                        radius=6, fill=(18, 18, 18, 230))
    d.text((x + pad, y + 11), label, font=font, fill=PAPER)


def _split_label(label):
    if "|" in label:
        head, _, val = label.rpartition("|")
        return head + "| ", val.strip()
    return label, ""


def _fmt_like(value, x):
    try:
        dec = len(value.split(".")[1]) if "." in value else 0
        num = float(value.replace(",", "").split()[0])
        unit = value[len(value.split()[0]):]
        return f"{x * num:.{dec}f}{unit}"
    except Exception:
        return value


# ------------------------------------------------------------------ particles
class Particles:
    """One continuous field: converge onto the image, then drift forever."""

    def __init__(self, still, seed, hook_n):
        self.hook_n = hook_n
        rng = np.random.default_rng(abs(hash(seed)) % (2**32))
        g = np.asarray(Image.open(still).convert("L").resize((W // 4, H // 4)),
                       dtype=np.float64)
        # sample targets weighted toward bright regions (particles paint the subject)
        p = (g / max(1.0, g.sum())).ravel()
        idx = rng.choice(p.size, size=N_PARTICLES, p=p)
        ys, xs = np.divmod(idx, W // 4)
        self.tx = (xs + rng.random(N_PARTICLES)) * 4.0
        self.ty = (ys + rng.random(N_PARTICLES)) * 4.0
        # scattered start positions for the reveal
        self.sx = rng.random(N_PARTICLES) * W
        self.sy = rng.random(N_PARTICLES) * H
        # per-particle drift: depth (parallax), amplitude, frequency, phase
        self.depth = 0.35 + 0.65 * rng.random(N_PARTICLES)       # 0.35 near..1 far
        self.ax = (18 + 46 * rng.random(N_PARTICLES)) * self.depth
        self.ay = (26 + 70 * rng.random(N_PARTICLES)) * self.depth
        self.fx = 0.05 + 0.16 * rng.random(N_PARTICLES)          # Hz-ish, irrational mix
        self.fy = 0.04 + 0.14 * rng.random(N_PARTICLES)
        self.phx = rng.random(N_PARTICLES) * math.tau
        self.phy = rng.random(N_PARTICLES) * math.tau
        self.tw = 0.5 + 1.9 * rng.random(N_PARTICLES)            # twinkle rate
        self.twph = rng.random(N_PARTICLES) * math.tau
        self.size = np.where(self.depth < 0.6, 1, 2)             # near=2px, far=1px

    def frame(self, f):
        t = f / FPS
        drift_x = self.ax * np.sin(math.tau * self.fx * t + self.phx)
        drift_y = self.ay * np.sin(math.tau * self.fy * t + self.phy)
        if f < self.hook_n:
            u = _ease(f / max(1, self.hook_n))
            bx = self.sx + (self.tx - self.sx) * u
            by = self.sy + (self.ty - self.sy) * u
            x = bx + drift_x * u
            y = by + drift_y * u
            bright = (0.25 + 0.75 * u)
        else:
            x = self.tx + drift_x
            y = self.ty + drift_y
            bright = 1.0
        x = np.mod(x, W)
        y = np.mod(y, H)
        tw = 0.55 + 0.45 * np.sin(math.tau * self.tw * t + self.twph)
        val = np.clip(bright * tw * (0.55 + 0.45 * self.depth), 0, 1) * 235
        return x.astype(np.int32), y.astype(np.int32), self.size, val

    def render(self, total_n, outdir):
        for f in range(total_n):
            x, y, size, val = self.frame(f)
            arr = np.zeros((H, W), dtype=np.float32)
            np.add.at(arr, (y, x), val)
            near = size == 2                                     # 2px = small cross
            for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                xx = np.clip(x[near] + dx, 0, W - 1)
                yy = np.clip(y[near] + dy, 0, H - 1)
                np.add.at(arr, (yy, xx), val[near] * 0.5)
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")
            img = img.filter(ImageFilter.GaussianBlur(0.7))      # soften -> fine glow
            img.convert("RGB").save(os.path.join(outdir, f"{f:05d}.png"))


# ------------------------------------------------------------------ reveal hook
def render_reveal(still, label, outdir, n):
    """Artwork fades up from black under the particle convergence; label types."""
    base = Image.open(still).convert("RGB").resize((W, H))
    black = Image.new("RGB", (W, H), (0, 0, 0))
    font = load_font(max(22, W // 34))
    head, value = _split_label(label)
    for i in range(n):
        t = _ease(i / max(1, n - 1))
        img = Image.blend(black, base, min(1.0, t * 1.15))
        d = ImageDraw.Draw(img, "RGBA")
        if t < 0.55:
            k = int(len(head) * (t / 0.55))
            txt = head[:k] + ("█" if i % 10 < 5 else "")
        else:
            v = _ease(min(1.0, (t - 0.55) / 0.4))
            txt = head + (_fmt_like(value, v) if value else "")
        _draw_label(d, txt, font)
        img.save(os.path.join(outdir, f"{i:05d}.png"))


# ------------------------------------------------------------------ ffmpeg bits
def _encode_frames(outdir, seg, crf=20):
    subprocess.run([ffmpeg_exe(), "-y", "-framerate", str(FPS),
                    "-i", os.path.join(outdir, "%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf),
                    seg], check=True, capture_output=True)


def _make_flow(boom, out, seconds):
    """Slow the single boomerang to `seconds` with a light motion-trail (tmix),
    so the base reads as one continuous drift, never an N× loop."""
    subprocess.run([ffmpeg_exe(), "-y", "-i", boom,
                    "-vf", f"setpts=6*PTS,tmix=frames=3:weights='1 1 1',fps={FPS}",
                    "-t", str(seconds), "-an",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    out], check=True, capture_output=True)


def _concat(segs, out, tmp):
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        for s in segs:
            fh.write(f"file '{os.path.abspath(s)}'\n")
    subprocess.run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-r", str(FPS), out], check=True, capture_output=True)


def assemble(still_path, motion_mp4, label, out, seed="namecode"):
    """reveal + drifting-flow + settle, with one continuous particle field
    screen-blended over the whole thing."""
    hook_n = round(HOOK_SEC * FPS)
    flow_n = round(FLOW_SEC * FPS)
    end_n = round(END_SEC * FPS)
    total_n = hook_n + flow_n + end_n
    tmp = tempfile.mkdtemp(prefix="reelfx_")
    try:
        # --- content track (no particles) ---
        hookdir = os.path.join(tmp, "hook"); os.makedirs(hookdir)
        render_reveal(still_path, label, hookdir, hook_n)
        seg_hook = os.path.join(tmp, "c_hook.mp4"); _encode_frames(hookdir, seg_hook)

        seg_flow = os.path.join(tmp, "c_flow.mp4"); _make_flow(motion_mp4, seg_flow, FLOW_SEC)

        enddir = os.path.join(tmp, "end"); os.makedirs(enddir)
        still = Image.open(still_path).convert("RGB").resize((W, H))
        for i in range(end_n):
            still.save(os.path.join(enddir, f"{i:05d}.png"))
        seg_end = os.path.join(tmp, "c_end.mp4"); _encode_frames(enddir, seg_end)

        content = os.path.join(tmp, "content.mp4")
        _concat([seg_hook, seg_flow, seg_end], content, tmp)

        # --- particle track (full length, continuous) ---
        pdir = os.path.join(tmp, "parts"); os.makedirs(pdir)
        Particles(still_path, seed, hook_n).render(total_n, pdir)
        particles = os.path.join(tmp, "particles.mp4"); _encode_frames(pdir, particles)

        # --- screen-blend particles over content ---
        # blend in RGB (gbrp): screen on the chroma planes of yuv would tint the
        # grayscale frame magenta (screen(128,128)=192), so keep it in RGB.
        subprocess.run([ffmpeg_exe(), "-y", "-i", content, "-i", particles,
                        "-filter_complex",
                        "[0:v]format=gbrp[c];[1:v]format=gbrp[p];"
                        "[c][p]blend=all_mode=screen:shortest=1,"
                        f"format=yuv420p,fps={FPS}",
                        "-c:v", "libx264", "-crf", "20",
                        "-movflags", "+faststart", "-an", out], check=True)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
