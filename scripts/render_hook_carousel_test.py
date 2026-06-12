#!/usr/bin/env python3
"""Render a hook-led Instagram single image and six-card carousel."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont


ROOT = Path(__file__).parent.parent
OUT = ROOT / "images" / "tests" / "data-trust"
SOURCE = ROOT / "images" / "revisions" / "post_20260612_style_01_v2.jpg"
W = H = 1080
NAVY = "#071426"
NAVY_2 = "#10243C"
BEIGE = "#F8F6F2"
AQUA = "#16B8F3"
MUTED = "#9DB0C5"


def font(size: int, bold: bool = False):
    name = "malgunbd.ttf" if bold else "NotoSansKR-VF.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def gradient():
    image = Image.new("RGB", (W, H), NAVY)
    pixels = image.load()
    for y in range(H):
        for x in range(W):
            glow = max(0, 1 - ((x - 900) ** 2 + (y - 180) ** 2) ** 0.5 / 800)
            pixels[x, y] = (
                int(7 + 9 * glow),
                int(20 + 45 * glow),
                int(38 + 66 * glow),
            )
    return image


def add_brand(draw, page):
    draw.text((70, 52), "bbbb.beauty", font=font(25, True), fill=BEIGE)
    draw.text((870, 55), f"{page:02d} / 06", font=font(20), fill=MUTED)
    draw.line((70, 1008, 1010, 1008), fill="#29415D", width=1)
    draw.text(
        (70, 1023),
        "SCIENCE TO MESSAGE, BEAUTY TO EXPERIENCE.",
        font=font(16),
        fill=MUTED,
    )


def fit_text(draw, text, box, max_size, min_size=30, bold=True, spacing=12):
    x, y, width, height = box
    for size in range(max_size, min_size - 1, -2):
        selected = font(size, bold)
        words = text.split()
        lines, current = [], ""
        for word in words:
            trial = f"{current} {word}".strip()
            if draw.textlength(trial, font=selected) <= width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        line_height = size + spacing
        if len(lines) * line_height <= height:
            for index, line in enumerate(lines):
                draw.text((x, y + index * line_height), line, font=selected, fill=BEIGE)
            return y + len(lines) * line_height
    return y


def save(image, name):
    OUT.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT / name, quality=95, optimize=True)


def hook_visual(name):
    source = Image.open(SOURCE).convert("RGB").resize((1320, 1320))
    source = source.crop((120, 180, 1200, 1260))
    source = ImageEnhance.Contrast(source).enhance(1.08)
    source = ImageEnhance.Color(source).enhance(0.82)
    veil = Image.new("RGBA", (W, H), (5, 17, 32, 0))
    vd = ImageDraw.Draw(veil)
    vd.rectangle((0, 0, 555, H), fill=(5, 17, 32, 235))
    vd.rectangle((525, 0, 610, H), fill=(5, 17, 32, 150))
    source = Image.alpha_composite(source.convert("RGBA"), veil)
    draw = ImageDraw.Draw(source)

    draw.rectangle((0, 0, W, 125), fill=(5, 17, 32, 245))
    draw.text((72, 48), "bbbb.beauty", font=font(24, True), fill=BEIGE)
    draw.text((880, 50), "01 / 06", font=font(19), fill=MUTED)
    for i, value in enumerate([88, 180, 126, 252, 196, 318, 260]):
        x = 84 + i * 58
        draw.rounded_rectangle(
            (x, 795 - value, x + 24, 795),
            radius=8,
            fill=AQUA if i == 5 else "#36516B",
        )
    draw.line((72, 804, 500, 804), fill="#7890A8", width=2)
    draw.text((72, 825), "MORE DATA", font=font(18, True), fill=MUTED)
    draw.text((72, 190), "47 PAGE", font=font(28, True), fill=AQUA)
    draw.text((72, 232), "CLINICAL REPORT", font=font(18), fill=MUTED)
    draw.text((72, 326), "데이터가 많을수록", font=font(48, True), fill=BEIGE)
    draw.text((72, 392), "더 믿을까요?", font=font(64, True), fill=BEIGE)
    draw.rounded_rectangle((72, 900, 467, 962), radius=31, fill=(22, 184, 243, 235))
    draw.text((113, 916), "그래프  A  /  경험  B", font=font(24, True), fill=NAVY)
    draw.text((720, 760), "UNDERSTAND", font=font(18, True), fill=BEIGE)
    draw.line((695, 750, 1010, 750), fill=AQUA, width=3)
    draw.rounded_rectangle((80, 989, 1000, 1064), radius=26, fill=(5, 17, 32, 245))
    draw.text((465, 1005), "bbbb.beauty", font=font(22, True), fill=BEIGE)
    save(source, name)


def card(page, eyebrow, headline, body, visual):
    image = gradient()
    draw = ImageDraw.Draw(image)
    add_brand(draw, page)
    draw.text((70, 150), eyebrow, font=font(20, True), fill=AQUA)
    bottom = fit_text(draw, headline, (70, 200, 900, 250), 62)
    draw.multiline_text(
        (70, bottom + 30),
        body,
        font=font(29),
        fill=MUTED,
        spacing=14,
    )
    visual(draw)
    return image


def chart_visual(draw):
    draw.rounded_rectangle((70, 650, 1010, 920), radius=30, fill=NAVY_2)
    for i, value in enumerate([120, 190, 260, 330, 395]):
        x = 145 + i * 150
        draw.rounded_rectangle((x, 865 - value / 2, x + 55, 865), 14, fill="#274765")
    draw.line((120, 865, 945, 865), fill=MUTED, width=2)
    draw.text((120, 885), "정보량", font=font(18), fill=MUTED)
    draw.line((760, 710, 930, 840), fill=AQUA, width=8)
    draw.text((730, 660), "이해도", font=font(20, True), fill=AQUA)


def three_steps(draw):
    for i, (number, label) in enumerate([("01", "변화"), ("02", "기전"), ("03", "근거")]):
        x = 70 + i * 315
        draw.rounded_rectangle((x, 650, x + 275, 860), 28, fill=NAVY_2)
        draw.text((x + 30, 685), number, font=font(24, True), fill=AQUA)
        draw.text((x + 30, 760), label, font=font(42, True), fill=BEIGE)


def before_after(draw):
    draw.rounded_rectangle((70, 620, 500, 900), 30, fill=NAVY_2)
    draw.rounded_rectangle((580, 620, 1010, 900), 30, fill="#0A304A")
    draw.text((105, 655), "BEFORE", font=font(20, True), fill=MUTED)
    draw.text((615, 655), "AFTER", font=font(20, True), fill=AQUA)
    for i in range(8):
        draw.line((110, 725 + i * 18, 450, 725 + i * 18), fill="#52677C", width=5)
    draw.ellipse((690, 705, 875, 890), fill="#164D69", outline=AQUA, width=5)
    draw.ellipse((745, 760, 820, 835), fill=AQUA)
    draw.line((645, 798, 920, 798), fill=BEIGE, width=3)


def decision_visual(draw):
    draw.rounded_rectangle((70, 630, 1010, 900), 30, fill=NAVY_2)
    draw.text((125, 690), "정확성", font=font(30, True), fill=BEIGE)
    draw.text((443, 690), "+", font=font(42, True), fill=AQUA)
    draw.text((565, 690), "시각적 이해", font=font(30, True), fill=BEIGE)
    draw.line((130, 795, 895, 795), fill="#34536F", width=3)
    draw.polygon([(865, 775), (920, 795), (865, 815)], fill=AQUA)
    draw.text((365, 830), "신뢰와 선택", font=font(38, True), fill=AQUA)


def cta_visual(draw):
    draw.rounded_rectangle((70, 610, 1010, 765), 32, fill=AQUA)
    draw.text((118, 652), "댓글  A 그래프  /  B 경험", font=font(32, True), fill=NAVY)
    draw.rounded_rectangle((70, 795, 1010, 930), 32, fill=NAVY_2, outline=AQUA, width=2)
    draw.text((118, 835), "DM 'MOA' → 시각화 진단 질문", font=font(30, True), fill=BEIGE)


def main():
    hook_visual("single-data-trust.jpg")
    hook_visual("carousel-01.jpg")
    cards = [
        card(
            2,
            "THE PROBLEM",
            "읽히지 않는 근거는 설득이 아닙니다.",
            "그래프가 늘어날수록 고객은 무엇을 봐야 할지\n결정하기 어려워집니다.",
            chart_visual,
        ),
        card(
            3,
            "THE TRANSLATION",
            "고객은 세 가지 순서로 이해합니다.",
            "무엇이 변하는가. 어떻게 작동하는가.\n왜 믿을 수 있는가.",
            three_steps,
        ),
        card(
            4,
            "BEFORE / AFTER",
            "숫자를 지우지 말고 장면으로 바꿉니다.",
            "임상 근거는 유지하고, 흡수·전달·반응의 흐름을\n한눈에 보이는 경험으로 재구성합니다.",
            before_after,
        ),
        card(
            5,
            "BBBB.BEAUTY METHOD",
            "정확성과 아름다움은 같은 목표를 향합니다.",
            "의학적 고증과 시네마틱 3D/MoA를 결합해\n기술을 고객의 신뢰와 선택으로 연결합니다.",
            decision_visual,
        ),
        card(
            6,
            "YOUR TURN",
            "당신의 고객에게 필요한 것은 무엇인가요?",
            "A 더 많은 그래프   B 더 빠른 이해\n댓글 또는 DM으로 현재 과제를 알려주세요.",
            cta_visual,
        ),
    ]
    for index, image in enumerate(cards, start=2):
        save(image, f"carousel-{index:02d}.jpg")


if __name__ == "__main__":
    main()
