#!/usr/bin/env python3
"""Assemble storyboard clips into the final 9:16 reel.

Normalizes each clip to 1080x1920/30fps (+sharpen), crossfades between them,
and overlays the mono namecode label (rendered with PIL, so no ffmpeg/freetype
dependency). Works with the imageio-ffmpeg binary via $FFMPEG, or system ffmpeg.

Usage:  build_story_reel.py clip1.mp4 clip2.mp4 ... out.mp4
Env:    FFMPEG, NAMECODE_FONT, REEL_LABEL, XFADE (sec)
"""
import os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

FF = os.environ.get("FFMPEG", "ffmpeg")
FONT = os.environ.get("NAMECODE_FONT", "/tmp/fnt/JetBrainsMono.ttf")
LABEL = os.environ.get("REEL_LABEL", "namecode - OCCULTATION | 1 hr")
XF = float(os.environ.get("XFADE", "0.6"))
W, H, FPS = 1080, 1920, 30


def probe_dur(path):
    err = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def make_label_png(path):
    im = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 34)
    tw = d.textlength(LABEL, font=f)
    d.rounded_rectangle([40, 40, 40 + tw + 28, 40 + 52], radius=6, fill=(18, 18, 18, 150))
    d.text((54, 51), LABEL, font=f, fill=(245, 245, 243, 245))
    im.save(path)


def main():
    clips, out = sys.argv[1:-1], sys.argv[-1]
    assert len(clips) >= 2, "need >=2 clips"
    tmp = tempfile.mkdtemp()
    label_png = os.path.join(tmp, "label.png")
    make_label_png(label_png)

    durs = [probe_dur(c) for c in clips]
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    inputs += ["-loop", "1", "-i", label_png]
    label_idx = len(clips)

    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},unsharp=5:5:0.6,fps={FPS},setsar=1,format=yuv420p")
    parts = [f"[{i}:v]{vf}[v{i}]" for i in range(len(clips))]

    last, acc = "[v0]", durs[0]
    for i in range(1, len(clips)):
        off = acc - XF
        lbl = f"[x{i}]"
        parts.append(f"{last}[v{i}]xfade=transition=fade:duration={XF}:offset={off:.3f}{lbl}")
        last, acc = lbl, acc + durs[i] - XF
    parts.append(f"{last}[{label_idx}:v]overlay=0:0:format=auto[v]")
    fc = ";".join(parts)

    cmd = [FF, "-y"] + inputs + ["-filter_complex", fc, "-map", "[v]",
           "-t", f"{acc:.3f}", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", str(FPS), out]
    subprocess.run(cmd, check=True)
    print(f"wrote {out}  (~{acc:.1f}s, {len(clips)} shots)")


if __name__ == "__main__":
    main()
