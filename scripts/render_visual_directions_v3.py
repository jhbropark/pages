#!/usr/bin/env python3
"""Create four visually distinct Instagram concepts from generated backgrounds."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).parent.parent
SOURCE_DIR = ROOT / "images" / "concepts" / "visual-directions-v3"
OUT_DIR = SOURCE_DIR / "final"
FONT = Path("C:/Windows/Fonts/NotoSansKR-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
NAVY = (7, 20, 38)
BEIGE = (248, 246, 242)
AQUA = (14, 165, 233)
MUTED = (174, 195, 211)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def cover(path: Path):
    source = Image.open(path).convert("RGB")
    side = min(source.size)
    left = (source.width - side) // 2
    top = (source.height - side) // 2
    return source.crop((left, top, left + side, top + side)).resize((1080, 1080))


def save(image, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / name
    image.convert("RGB").save(output, quality=95, optimize=True)
    return output


def hyper_silico():
    image = cover(SOURCE_DIR / "01-hyper-silico-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.polygon([(0, 0), (620, 0), (445, 1080), (0, 1080)], fill=(4, 15, 31, 226))
    draw.line((72, 92, 305, 92), fill=(*AQUA, 255), width=5)
    draw.text((72, 122), "01  HYPER-SILICO", font=font(18, True), fill=(*AQUA, 255))
    draw.text((72, 214), "보이지 않는\n성분을 어떻게\n믿게 만들까요?", font=font(57, True), fill=(*BEIGE, 255), spacing=18)
    draw.text((72, 520), "투명도는 장식이 아니라\n작용 기전을 이해시키는 언어입니다.", font=font(25), fill=(*MUTED, 255), spacing=10)
    draw.rounded_rectangle((72, 838, 390, 910), radius=36, fill=(*AQUA, 242))
    draw.text((111, 856), "성분 전달  A  /  기전  B", font=font(21, True), fill=(*NAVY, 255))
    draw.text((72, 1002), "bbbb.beauty", font=font(22, True), fill=(*BEIGE, 255))
    return save(Image.alpha_composite(image, overlay), "01-hyper-silico.jpg")


def neo_lab():
    image = cover(SOURCE_DIR / "02-neo-lab-source.png").convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1080, 150), fill=(248, 246, 242, 246))
    draw.text((58, 42), "bbbb.beauty", font=font(22, True), fill=(30, 41, 59, 255))
    draw.text((812, 45), "02 / NEO-LAB", font=font(18), fill=(80, 94, 112, 255))
    draw.rounded_rectangle((58, 710, 758, 1000), radius=8, fill=(248, 246, 242, 242))
    draw.text((98, 752), "과학적 신뢰는\n왜 늘 차가워야 할까요?", font=font(49, True), fill=(30, 41, 59, 255), spacing=12)
    draw.line((98, 906, 215, 906), fill=(14, 165, 233, 255), width=5)
    draw.text((98, 930), "정밀함에는 온도가 필요합니다.", font=font(22), fill=(78, 91, 109, 255))
    return save(image, "02-neo-lab.jpg")


def micro_cinema():
    image = cover(SOURCE_DIR / "03-micro-cinema-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, 1080, 1080), fill=(1, 7, 14, 36))
    draw.rectangle((0, 0, 1080, 220), fill=(1, 7, 14, 175))
    draw.rectangle((0, 835, 1080, 1080), fill=(1, 7, 14, 185))
    draw.text((62, 55), "A BBBB.BEAUTY MICRO FILM", font=font(18, True), fill=(*AQUA, 255))
    draw.text((62, 104), "정확한 영상이\n기억에 남지 않는 이유", font=font(52, True), fill=(*BEIGE, 255), spacing=8)
    draw.text((62, 870), "정보에는 초점이 필요합니다.", font=font(32, True), fill=(*BEIGE, 255))
    draw.text((62, 925), "한 장면, 한 구조, 한 번의 이해.", font=font(23), fill=(*MUTED, 255))
    draw.text((62, 1015), "03  MICRO-CINEMATOGRAPHY", font=font(17, True), fill=(*AQUA, 255))
    return save(Image.alpha_composite(image, overlay), "03-micro-cinema.jpg")


def data_minimal():
    image = cover(SOURCE_DIR / "04-data-minimal-source.png").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((42, 45, 515, 360), radius=28, fill=(7, 20, 38, 225), outline=(14, 165, 233, 110), width=2)
    draw.text((78, 78), "04 / DATA MINIMALISM UX", font=font(17, True), fill=(*AQUA, 255))
    draw.text((78, 139), "데이터를\n더 보여줄수록\n더 이해할까요?", font=font(43, True), fill=(*BEIGE, 255), spacing=8)
    draw.rounded_rectangle((650, 855, 1025, 970), radius=28, fill=(7, 20, 38, 225), outline=(14, 165, 233, 170), width=2)
    draw.text((695, 880), "A 전시·영업", font=font(23, True), fill=(*BEIGE, 255))
    draw.text((695, 924), "B 교육·트레이닝", font=font(23, True), fill=(*AQUA, 255))
    draw.text((55, 1018), "bbbb.beauty  |  필요한 순간에 필요한 정보만", font=font(18), fill=(*BEIGE, 255))
    return save(Image.alpha_composite(image, overlay), "04-data-minimal.jpg")


def contact_sheet(paths):
    sheet = Image.new("RGB", (2200, 2200), (238, 238, 235))
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB").resize((1040, 1040))
        x = 40 + (index % 2) * 1080
        y = 40 + (index // 2) * 1080
        sheet.paste(image, (x, y))
    output = OUT_DIR / "visual-directions-v3-review.jpg"
    sheet.save(output, quality=93, optimize=True)
    return output


def main():
    outputs = [hyper_silico(), neo_lab(), micro_cinema(), data_minimal()]
    outputs.append(contact_sheet(outputs))
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
