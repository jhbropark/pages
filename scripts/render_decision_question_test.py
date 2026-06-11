#!/usr/bin/env python3
"""Render channel-specific test cards about decision-question design."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
NAVY = (8, 20, 38)
BEIGE = (248, 246, 242)
AQUA = (14, 165, 233)


def font(size: int, variation: str = "Regular") -> ImageFont.FreeTypeFont:
    result = ImageFont.truetype(str(FONT_PATH), size=size)
    result.set_variation_by_name(variation)
    return result


def background(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), NAVY)
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            glow = max(0.0, 1.0 - (((x - width * 0.73) / width) ** 2 + ((y - height * 0.5) / height) ** 2) * 5)
            pixels[x, y] = (
                round(8 + glow * 8),
                round(20 + glow * 42),
                round(38 + glow * 58),
            )
    return image


def draw_system(image: Image.Image, title: str, subtitle: str, square: bool) -> None:
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    center_x = width * (0.54 if square else 0.68)
    center_y = height * (0.62 if square else 0.54)
    radii = [height * 0.10, height * 0.18, height * 0.27]
    for index, radius in enumerate(radii):
        draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            outline=(*AQUA, 150 - index * 35),
            width=max(2, round(width / 500)),
        )

    labels = ["CHANGE", "MECHANISM", "EVIDENCE", "DECISION"]
    angles = [-90, 0, 90, 180]
    node_radius = height * 0.035
    for label, angle in zip(labels, angles):
        import math

        rad = math.radians(angle)
        x = center_x + math.cos(rad) * radii[-1]
        y = center_y + math.sin(rad) * radii[-1]
        draw.line((center_x, center_y, x, y), fill=(*AQUA, 90), width=2)
        draw.ellipse(
            (x - node_radius, y - node_radius, x + node_radius, y + node_radius),
            fill=(10, 33, 58, 235),
            outline=(*BEIGE, 115),
            width=2,
        )
        label_font = font(max(12, round(height * 0.017)), "Medium")
        box = draw.textbbox((0, 0), label, font=label_font)
        draw.text(
            (x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2 - 2),
            label,
            font=label_font,
            fill=(*BEIGE, 225),
        )

    draw.ellipse(
        (
            center_x - height * 0.07,
            center_y - height * 0.07,
            center_x + height * 0.07,
            center_y + height * 0.07,
        ),
        fill=(*AQUA, 220),
    )
    question_font = font(round(height * 0.075), "Medium")
    q_box = draw.textbbox((0, 0), "?", font=question_font)
    draw.text(
        (center_x - (q_box[2] - q_box[0]) / 2, center_y - (q_box[3] - q_box[1]) / 2 - 8),
        "?",
        font=question_font,
        fill=(*BEIGE, 255),
    )

    panel_right = width * (0.88 if square else 0.56)
    draw.rounded_rectangle(
        (width * 0.055, height * 0.07, panel_right, height * (0.34 if square else 0.42)),
        radius=round(height * 0.025),
        fill=(7, 20, 38, 224),
        outline=(*BEIGE, 40),
        width=1,
    )
    draw.rounded_rectangle(
        (width * 0.055, height * 0.07, width * 0.065, height * (0.34 if square else 0.42)),
        radius=4,
        fill=(*AQUA, 255),
    )
    title_font = font(round(height * (0.055 if square else 0.071)), "Medium")
    subtitle_font = font(round(height * 0.021), "Light")
    draw.text(
        (width * 0.09, height * 0.115),
        title,
        font=title_font,
        fill=(*BEIGE, 255),
        spacing=round(height * 0.018),
    )
    draw.text(
        (width * 0.092, height * (0.28 if square else 0.33)),
        subtitle,
        font=subtitle_font,
        fill=(125, 211, 252, 240),
    )

    footer_y = height * 0.91
    draw.rounded_rectangle(
        (width * 0.055, footer_y, width * 0.945, height * 0.97),
        radius=round(height * 0.018),
        fill=(7, 20, 38, 210),
        outline=(*BEIGE, 35),
        width=1,
    )
    brand_font = font(round(height * 0.019), "Medium")
    tagline_font = font(round(height * 0.016), "Light")
    draw.text((width * 0.085, footer_y + height * 0.018), "bbbb.beauty", font=brand_font, fill=(*BEIGE, 255))
    tagline = "Science to Message, Beauty to Experience."
    tagline_width = draw.textlength(tagline, font=tagline_font)
    draw.text(
        (width * 0.915 - tagline_width, footer_y + height * 0.02),
        tagline,
        font=tagline_font,
        fill=(188, 211, 223, 235),
    )

    blurred = overlay.filter(ImageFilter.GaussianBlur(radius=0.25))
    image.paste(Image.alpha_composite(image.convert("RGBA"), blurred).convert("RGB"))


def render() -> None:
    instagram = background(1080, 1080)
    draw_system(instagram, "질문이 먼저입니다", "DECISION-QUESTION DESIGN", True)
    instagram_path = ROOT / "images" / "post_20260612_decision_question_test.jpg"
    instagram.save(instagram_path, "JPEG", quality=95, optimize=True, progressive=True)

    linkedin = background(1200, 627)
    draw_system(linkedin, "질문이 먼저입니다", "DESIGN THE DECISION BEFORE THE VISUAL", False)
    linkedin_path = ROOT / "images" / "linkedin" / "post_20260612_decision_question_test.jpg"
    linkedin.save(linkedin_path, "JPEG", quality=95, optimize=True, progressive=True)

    print(instagram_path)
    print(linkedin_path)


if __name__ == "__main__":
    render()
