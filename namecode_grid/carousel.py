#!/usr/bin/env python3
"""Build an Instagram explainer carousel — 8 slides, 4:5 (1080x1350).

Format role (Instagram 2026): carousels = deep engagement (8-10 slides sweet
spot). Same dark monochrome + JetBrains Mono identity as the feed.
"""
import io, os, requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

R = "/tmp/fnt/JetBrainsMono.ttf"
B = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
def F(s, b=False): return ImageFont.truetype(B if b else R, s)
PAPER = (245, 245, 243); INK = (26, 26, 26); BLACK = (12, 12, 12); GRAY = (150, 150, 150)
W, H = 1080, 1350

# (image_url | None, kind, headline, sub)
G = "https://gen.krea.ai/images/{}.png".format
SLIDES = [
    (None, "title", "TRANSLATING\nTHE SKY\nINTO CODE", "namecode // daily generative studio"),
    (G("4e8f0515-ba75-4d1b-8356-3c1f205fbbca"), "step", "01  PICK THE DAY'S\n    COSMIC EVENT", "Sourced from NASA APOD, every day."),
    (G("983a978e-eb22-4c8b-9e86-df4ed0929665"), "step", "02  EXTRACT THE\n    REAL DATA", "Magnitude, distance, geometry."),
    (G("ce4cc011-a64e-43c9-87aa-daafccfb329e"), "step", "03  TRANSLATE INTO\n    PARTICLES", "Code turns physics into form."),
    (G("0130532e-332f-4df5-8939-775ba09f61df"), "step", "04  RENDER IN\n    MONOCHROME", "One palette. Black & light."),
    (G("b44d47e0-f3d5-4b7e-b384-124c691b113c"), "step", "05  LABEL WITH THE\n    REAL FIGURE", "namecode - NAME | mag -4.2"),
    (G("1bf56457-eb83-4712-baee-b0d7dd7dcae1"), "step", "FROM SCREEN\nTO SPACE", "Built for immersive installation."),
    (None, "cta", "A NEW SKY,\nEVERY DAY", "Follow  @namecode_original"),
]


def duo_cover(url):
    g = ImageOps.autocontrast(Image.open(io.BytesIO(requests.get(url, timeout=60).content)).convert("L"), cutoff=1)
    g = ImageOps.fit(g, (W, H), method=Image.LANCZOS)
    return ImageOps.colorize(g, black=BLACK, white=PAPER).convert("RGB")


def text_slide(headline, sub, center=True):
    im = Image.new("RGB", (W, H), INK); d = ImageDraw.Draw(im)
    lines = headline.split("\n")
    fs = 96
    th = len(lines) * (fs + 14)
    y = (H - th) // 2 - 40
    for ln in lines:
        f = F(fs, True); w = d.textlength(ln, font=f)
        x = (W - w) // 2 if center else 80
        d.text((x, y), ln, font=f, fill=PAPER); y += fs + 14
    fsub = F(30); ws = d.textlength(sub, font=fsub)
    d.text(((W - ws) // 2 if center else 80, y + 20), sub, font=fsub, fill=GRAY)
    return im


def step_slide(url, idx, total, headline, sub):
    im = duo_cover(url); d = ImageDraw.Draw(im, "RGBA")
    # index top-right
    f = F(26, True); tag = f"{idx:02d}/{total:02d}"
    tw = d.textlength(tag, font=f)
    d.text((W - tw - 40, 44), tag, font=f, fill=PAPER)
    # namecode mark top-left
    d.text((40, 44), "namecode", font=F(26, True), fill=PAPER)
    # bottom gradient for legibility
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        grad.putpixel((0, yy), int(235 * max(0, (yy - H * 0.55) / (H * 0.45))))
    grad = grad.resize((W, H))
    shade = Image.new("RGB", (W, H), (8, 8, 8))
    im.paste(shade, (0, 0), grad)
    d = ImageDraw.Draw(im, "RGBA")
    # headline + sub bottom-left
    lines = headline.split("\n"); fs = 60
    y = H - 250
    for ln in lines:
        f = F(fs, True); d.text((60, y), ln, font=f, fill=PAPER); y += fs + 8
    d.text((60, y + 14), sub, font=F(28), fill=(210, 210, 210))
    return im


def main():
    os.makedirs("carousel", exist_ok=True)
    imgs = []
    total = len(SLIDES)
    for i, (url, kind, head, sub) in enumerate(SLIDES, 1):
        if kind == "title":
            im = text_slide(head, sub)
        elif kind == "cta":
            im = text_slide(head, sub)
        else:
            im = step_slide(url, i - 1, total - 1, head, sub)
        im.save(f"carousel/slide_{i:02d}.png")
        imgs.append(im)
    # preview contact sheet (4 cols x 2 rows, scaled)
    cols, sw = 4, 270; sh = int(sw * H / W); gap = 12
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * sw + (cols + 1) * gap, rows * sh + (rows + 1) * gap), (0, 0, 0))
    for i, im in enumerate(imgs):
        r, c = divmod(i, cols)
        sheet.paste(im.resize((sw, sh)), (gap + c * (sw + gap), gap + r * (sh + gap)))
    sheet.save("carousel_preview.png")
    print("OK 8 slides + carousel_preview.png")


if __name__ == "__main__":
    main()
