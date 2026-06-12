#!/usr/bin/env python3
"""Render a vertical Reel master and four Instagram Story cards."""

from pathlib import Path
import math
import random

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).parent.parent
BASE = ROOT / "images" / "social-formats" / "body-cell-motion"
SOURCE = BASE / "source"
REEL_DIR = BASE / "reel"
STORY_DIR = BASE / "stories"
W, H = 1080, 1920
FPS = 24
DURATION = 16
FONT = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
WHITE = (248, 245, 241)
MUTED = (204, 194, 191)
RED = (238, 48, 54)
AMBER = (255, 171, 71)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def cover(image: Image.Image, size=(W, H), zoom=1.0, x_bias=0.5, y_bias=0.5):
    target_w, target_h = size
    ratio = max(target_w / image.width, target_h / image.height) * zoom
    resized = image.resize(
        (round(image.width * ratio), round(image.height * ratio)),
        Image.Resampling.LANCZOS,
    )
    max_x = max(0, resized.width - target_w)
    max_y = max(0, resized.height - target_h)
    left = round(max_x * x_bias)
    top = round(max_y * y_bias)
    return resized.crop((left, top, left + target_w, top + target_h))


def add_vertical_gradient(image: Image.Image, top=145, bottom=190):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        edge = min(y / 500, (H - y) / 500, 1)
        alpha = round(top * (1 - edge) + bottom * max(0, 1 - edge))
        draw.line((0, y, W, y), fill=(4, 3, 5, alpha))
    return Image.alpha_composite(image.convert("RGBA"), overlay)


def add_header(draw: ImageDraw.ImageDraw, index: str):
    draw.text((64, 70), "bbbb.beauty", font=font(25, True), fill=WHITE)
    draw.text((905, 74), index, font=font(20, True), fill=RED)


def draw_multiline(draw, xy, text, size, fill=WHITE, bold=True, spacing=14):
    draw.multiline_text(xy, text, font=font(size, bold), fill=fill, spacing=spacing)


def reel_text_at(t: float):
    if t < 3.5:
        return "보이지 않는 작용은\n움직임으로 이해됩니다.", "INVISIBLE → UNDERSTANDABLE"
    if t < 7.5:
        return "성분이 도달하고", "01 / ARRIVAL"
    if t < 11.5:
        return "세포가 신호를 주고받고", "02 / SIGNAL & FUSION"
    if t < 14.2:
        return "조직의 반응으로\n이어집니다.", "03 / TISSUE RESPONSE"
    return "설명하기 어려운 기술이\n있으신가요?", "프로필 문의 링크에서 함께 검토하겠습니다."


def scene_index(t: float):
    if t < 5.2:
        return 0, t / 5.2
    if t < 10.4:
        return 1, (t - 5.2) / 5.2
    return 2, (t - 10.4) / 5.6


def make_reel_frame(sources, frame_number):
    t = frame_number / FPS
    index, progress = scene_index(t)
    zoom = 1.02 + 0.10 * progress
    x_biases = (0.43, 0.55, 0.47)
    y_biases = (0.46, 0.50, 0.48)
    image = cover(
        sources[index],
        zoom=zoom,
        x_bias=x_biases[index],
        y_bias=y_biases[index],
    )

    boundary = 5.2 if index == 0 else 10.4
    if index < 2 and 0 < boundary - t < 0.65:
        blend = 1 - ((boundary - t) / 0.65)
        next_image = cover(
            sources[index + 1],
            zoom=1.02,
            x_bias=x_biases[index + 1],
            y_bias=y_biases[index + 1],
        )
        image = Image.blend(image, next_image, blend)

    image = add_vertical_gradient(image)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    random.seed(frame_number // 2)
    for particle in range(18):
        phase = (frame_number * (2.0 + particle % 3) + particle * 73) % (H + 300)
        y = H + 100 - phase
        x = 120 + ((particle * 167 + frame_number * (1 + particle % 2)) % 840)
        radius = 2 + particle % 4
        color = RED if particle % 3 else AMBER
        glow_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, 155))
        glow_draw.line((x, y + 8, x - 3, y + 34), fill=(*color, 70), width=2)
    glow = glow.filter(ImageFilter.GaussianBlur(2.2))
    image = Image.alpha_composite(image, glow)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    add_header(draw, "REEL / 01")
    headline, label = reel_text_at(t)
    fade_in = min(1, (t % 3.8) / 0.35)
    text_fill = (*WHITE, round(255 * fade_in))
    draw_multiline(draw, (64, 240), headline, 58, fill=text_fill, spacing=18)
    draw.line((64, 465, 245, 465), fill=(*RED, round(255 * fade_in)), width=5)
    draw_multiline(
        draw,
        (64, 495),
        label,
        24 if t < 14.2 else 26,
        fill=(*MUTED, round(255 * fade_in)),
        bold=t >= 14.2,
        spacing=10,
    )
    draw.text(
        (64, 1790),
        "Science to Message, Beauty to Experience.",
        font=font(20),
        fill=(*WHITE, 210),
    )
    draw.rounded_rectangle((64, 1835, 330, 1845), radius=5, fill=(*RED, 220))
    return Image.alpha_composite(image, overlay).convert("RGB")


def render_reel(sources):
    REEL_DIR.mkdir(parents=True, exist_ok=True)
    output = REEL_DIR / "body-cell-motion-reel-ko.mp4"
    writer = imageio_ffmpeg.write_frames(
        str(output),
        (W, H),
        fps=FPS,
        codec="libx264",
        macro_block_size=2,
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        output_params=["-crf", "20", "-preset", "medium", "-movflags", "+faststart"],
    )
    writer.send(None)
    for frame_number in range(FPS * DURATION):
        writer.send(np.asarray(make_reel_frame(sources, frame_number)))
    writer.close()

    poster = make_reel_frame(sources, 30)
    poster.save(REEL_DIR / "body-cell-motion-reel-cover.jpg", quality=95, optimize=True)
    return output


def story_base(source, index):
    image = cover(source, zoom=1.05, x_bias=0.5, y_bias=0.48)
    image = ImageEnhance.Contrast(image).enhance(1.05)
    image = add_vertical_gradient(image, 175, 210)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    add_header(draw, f"STORY / {index:02d}")
    return image, overlay, draw


def render_stories(sources):
    STORY_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []

    image, overlay, draw = story_base(sources[0], 1)
    draw_multiline(draw, (64, 220), "귀사의 기술에서\n가장 설명하기 어려운\n단계는 무엇인가요?", 58)
    draw_multiline(
        draw,
        (64, 520),
        "아래 투표에서 현재 과제와\n가장 가까운 항목을 선택해 주세요.",
        28,
        fill=WHITE,
        bold=True,
    )
    draw.rounded_rectangle(
        (105, 1110, 975, 1425),
        radius=30,
        fill=(4, 3, 5, 95),
        outline=(*WHITE, 175),
        width=3,
    )
    draw.text((230, 1200), "A  성분의 이동", font=font(30, True), fill=WHITE)
    draw.line((530, 1170, 530, 1370), fill=(*WHITE, 90), width=2)
    draw.text((595, 1200), "B  세포의 반응", font=font(30, True), fill=WHITE)
    draw.text(
        (250, 1310),
        "가장 가까운 항목을 메시지로 알려주세요.",
        font=font(23),
        fill=(*WHITE, 190),
    )
    draw.text((64, 1775), "성분의 이동  /  세포의 반응", font=font(25, True), fill=WHITE)
    outputs.append(Image.alpha_composite(image, overlay))

    image, overlay, draw = story_base(sources[1], 2)
    draw_multiline(draw, (64, 220), "고객이 이해해야 할 것은\n데이터의 양이 아니라\n변화의 흐름입니다.", 56)
    stages = [("원인", 170), ("이동", 465), ("반응", 760)]
    for label, x in stages:
        draw.ellipse((x, 1180, x + 28, 1208), fill=AMBER)
        draw.text((x - 20, 1230), label, font=font(29, True), fill=WHITE)
    draw.line((200, 1194, 465, 1194), fill=RED, width=5)
    draw.line((495, 1194, 760, 1194), fill=RED, width=5)
    draw_multiline(
        draw,
        (64, 1665),
        "장면의 순서가 보이면\n복잡한 작용 기전도 따라갈 수 있습니다.",
        27,
        fill=MUTED,
        bold=False,
    )
    outputs.append(Image.alpha_composite(image, overlay))

    image, overlay, draw = story_base(sources[2], 3)
    draw_multiline(draw, (64, 220), "정확한 자료에서 시작해\n기억되는 장면으로\n설계합니다.", 58)
    steps = [
        ("01", "원본 R&D 자료 검토"),
        ("02", "세포 이동과 반응 설계"),
        ("03", "활용 채널별 장면 최적화"),
    ]
    for idx, (number, text) in enumerate(steps):
        y = 1030 + idx * 145
        draw.rounded_rectangle((55, y - 30, 865, y + 72), radius=22, fill=(4, 3, 5, 105))
        draw.text((75, y), number, font=font(23, True), fill=RED)
        draw.line((150, y + 17, 245, y + 17), fill=(*WHITE, 120), width=2)
        draw.text((275, y - 4), text, font=font(29, True), fill=WHITE)
    outputs.append(Image.alpha_composite(image, overlay))

    image, overlay, draw = story_base(sources[2], 4)
    draw_multiline(draw, (64, 220), "설명하기 어려운 기술을\n이해 가능한 움직임으로\n바꾸고 싶으신가요?", 56)
    draw_multiline(
        draw,
        (64, 535),
        "프로젝트의 배경과 활용 목적을 남겨주시면\n내용을 먼저 살펴본 뒤 적합한 시각화 방향을\n함께 검토하겠습니다.",
        27,
        fill=WHITE,
        bold=True,
        spacing=13,
    )
    draw.rounded_rectangle(
        (105, 1170, 975, 1395),
        radius=34,
        fill=(4, 3, 5, 95),
        outline=(*WHITE, 180),
        width=3,
    )
    draw.text((250, 1220), "프로필의 문의 링크에서", font=font(31, True), fill=WHITE)
    draw.text(
        (255, 1300),
        "편하신 방식으로 프로젝트를 알려주세요.",
        font=font(24),
        fill=(*WHITE, 200),
    )
    draw.text((64, 1775), "bbbb.beauty  |  프로젝트 문의", font=font(25, True), fill=WHITE)
    outputs.append(Image.alpha_composite(image, overlay))

    for index, output in enumerate(outputs, 1):
        path = STORY_DIR / f"body-cell-story-{index:02d}.jpg"
        output.convert("RGB").save(path, quality=95, optimize=True)
    return outputs


def make_review(stories):
    width = 1080
    thumb_h = 960
    review = Image.new("RGB", (width * 2, thumb_h * 2), (8, 7, 9))
    for index, story in enumerate(stories):
        thumb = story.convert("RGB").resize((width, thumb_h), Image.Resampling.LANCZOS)
        review.paste(thumb, ((index % 2) * width, (index // 2) * thumb_h))
    path = STORY_DIR / "body-cell-stories-review.jpg"
    review.save(path, quality=92, optimize=True)
    return path


def main():
    source_paths = [
        SOURCE / "scene-01-arrival.png",
        SOURCE / "scene-02-signaling-fusion.png",
        SOURCE / "scene-03-tissue-response.png",
    ]
    sources = [Image.open(path).convert("RGB") for path in source_paths]
    print(render_reel(sources))
    stories = render_stories(sources)
    print(make_review(stories))


if __name__ == "__main__":
    main()
