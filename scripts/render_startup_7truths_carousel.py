#!/usr/bin/env python3
"""
스타트업 7가지 진실 카드뉴스 — Instagram 캐러셀 8장 생성

출력: images/daily/20260619-startup-7truths/instagram-carousel-01.jpg ~ 08.jpg
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).parent.parent
OUT_DIR = REPO_ROOT / "images" / "daily" / "20260619-startup-7truths"

W = H = 1080

# ── 팔레트: 미디어아트 / 크리에이티브 디렉팅 무드 ──────────────────────────
BG_DARK    = (10, 10, 16)       # 거의 검정
BG_CARD    = (18, 20, 34)       # 카드 배경
INDIGO     = (99, 102, 241)     # 인디고 액센트
CORAL      = (249, 115, 22)     # 코럴/오렌지 포인트
TEXT_WHITE = (245, 247, 250)    # 주 텍스트
TEXT_MUTED = (140, 153, 175)    # 보조 텍스트
GOLD       = (251, 191, 36)     # 숫자 강조
LINE_DIM   = (28, 36, 58)       # 구분선

# ── 폰트 로드 ───────────────────────────────────────────────────────────────
FONT_BOLD  = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
FONT_REG   = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_SQ    = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"

def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if Path(path).exists():
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)

def font_sq(size: int) -> ImageFont.FreeTypeFont:
    if Path(FONT_SQ).exists():
        return ImageFont.truetype(FONT_SQ, size)
    return font(size, bold=True)

# ── 공통 유틸 ───────────────────────────────────────────────────────────────
def make_bg() -> Image.Image:
    """그라디언트 배경 생성"""
    img = Image.new("RGB", (W, H), BG_DARK)
    px = img.load()
    for y in range(H):
        for x in range(W):
            # 우측 상단 인디고 광원
            glow = max(0.0, 1.0 - math.hypot(x - W * 0.9, y - H * 0.05) / 650)
            # 좌측 하단 미묘한 코럴 광원
            glow2 = max(0.0, 1.0 - math.hypot(x - W * 0.1, y - H * 0.95) / 550)
            r = min(255, BG_DARK[0] + int(INDIGO[0] * glow * 0.10 + CORAL[0] * glow2 * 0.04))
            g = min(255, BG_DARK[1] + int(INDIGO[1] * glow * 0.10 + CORAL[1] * glow2 * 0.04))
            b = min(255, BG_DARK[2] + int(INDIGO[2] * glow * 0.20 + CORAL[2] * glow2 * 0.02))
            px[x, y] = (r, g, b)
    return img

def wrap_text(draw, text: str, font_obj, max_w: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        bbox = draw.textbbox((0, 0), test, font=font_obj)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines

def brand_bar(draw, page: int, total: int = 8):
    """상단·하단 브랜드 바"""
    draw.rectangle([0, 0, W, 88], fill=(10, 10, 16))
    draw.line([0, 88, W, 88], fill=INDIGO, width=2)
    draw.text((60, 24), "STARTUP REALITY", font=font_sq(22), fill=TEXT_MUTED)
    draw.text((W - 130, 26), f"{page:02d}  /  {total:02d}", font=font(22), fill=TEXT_MUTED)

    draw.rectangle([0, H - 76, W, H], fill=(10, 10, 16))
    draw.line([0, H - 76, W, H - 76], fill=LINE_DIM, width=1)
    draw.text((60, H - 52), "parkjunhyuk", font=font(24, bold=True), fill=TEXT_MUTED)
    dot_x = 60 + draw.textlength("parkjunhyuk", font=font(24, bold=True)) + 14
    draw.text((int(dot_x), H - 52), "·  크리에이티브 디렉터", font=font(22), fill=LINE_DIM)

# ── 카드 렌더러 ──────────────────────────────────────────────────────────────
def render_cover() -> Image.Image:
    """슬라이드 1 — 커버"""
    img = make_bg()
    draw = ImageDraw.Draw(img)

    # 좌측 인디고 세로 바
    draw.rectangle([56, 118, 74, 480], fill=INDIGO)

    # 메인 텍스트
    draw.text((106, 130), "잘 되고", font=font(84, bold=True), fill=TEXT_WHITE)
    draw.text((106, 230), "있다?", font=font(84, bold=True), fill=TEXT_WHITE)
    draw.rectangle([106, 330, 680, 334], fill=CORAL)
    draw.text((106, 350), "그게 가장 위험하다", font=font(52, bold=True), fill=CORAL)

    # 서브타이틀 박스
    draw.rounded_rectangle([56, 490, 860, 590], radius=20,
                            fill=BG_CARD, outline=INDIGO, width=1)
    draw.text((90, 510), "스타트업 7가지 진실", font=font_sq(40), fill=TEXT_WHITE)
    draw.text((90, 560), "쿠팡·배민·토스를 키운 투자자의 관점", font=font(26), fill=TEXT_MUTED)

    # 저장 유도
    draw.text((106, 640), "📌  저장해두고 곱씹어보세요", font=font(34, bold=True), fill=GOLD)

    # 좌우 스와이프 힌트
    draw.rounded_rectangle([56, 720, 300, 762], radius=16,
                            fill=(99, 102, 241, 60), outline=(99, 102, 241, 80), width=1)
    draw.text((76, 729), "오른쪽으로 넘기세요 →", font=font(26), fill=INDIGO)

    brand_bar(draw, 1)
    return img


def render_truth(page: int, num_emoji: str, num_label: str,
                 headline: str, point: str, body: str) -> Image.Image:
    """슬라이드 2~8 — 진실 카드"""
    img = make_bg()
    draw = ImageDraw.Draw(img)

    # 숫자 뱃지
    cx, cy, r = 110, 165, 55
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INDIGO)
    draw.text((cx - 22, cy - 28), num_emoji, font=font(44, bold=True), fill=TEXT_WHITE)

    # 헤드라인 (긴 경우 줄 바꿈)
    h_font = font(54, bold=True)
    h_lines = wrap_text(draw, headline, h_font, W - 220)
    h_y = 118
    for line in h_lines[:2]:
        draw.text((190, h_y), line, font=h_font, fill=TEXT_WHITE)
        h_y += 70

    # 구분선
    div_y = h_y + 14
    draw.rectangle([60, div_y, W - 60, div_y + 3], fill=INDIGO)

    # 포인트 박스
    box_top = div_y + 22
    box_bot = box_top + 100
    draw.rounded_rectangle([60, box_top, W - 60, box_bot], radius=16,
                            fill=BG_CARD, outline=CORAL, width=1)
    p_font = font(34, bold=True)
    p_lines = wrap_text(draw, point, p_font, W - 160)
    p_y = box_top + 18
    for line in p_lines[:2]:
        draw.text((90, p_y), line, font=p_font, fill=GOLD)
        p_y += 46

    # 본문
    b_font = font(28)
    b_lines = wrap_text(draw, body, b_font, W - 140)
    b_y = box_bot + 36
    for line in b_lines[:5]:
        draw.text((70, b_y), line, font=b_font, fill=TEXT_MUTED)
        b_y += 44

    # 하단 페이지 표시 도트
    for i in range(8):
        color = INDIGO if (i + 1) == page else LINE_DIM
        draw.ellipse([W // 2 - 75 + i * 20, H - 100, W // 2 - 60 + i * 20, H - 85], fill=color)

    brand_bar(draw, page)
    return img


# ── 콘텐츠 정의 ─────────────────────────────────────────────────────────────
TRUTHS = [
    (
        "①", "①",
        "창업은 인생의 기회가 아니다",
        "버틸 체질인지 먼저 물어라",
        "화려한 성공 스토리에 끌려 뛰어드는 창업은 위험합니다. "
        "실패를 버텨낼 체력과 심리적 내성이 기회보다 먼저입니다. "
        "나는 몇 년을 무보수로 버틸 수 있는가. 먼저 스스로에게 물어보세요.",
    ),
    (
        "②", "②",
        "창업자가 못 파는 제품은",
        "시장에 필요 없는 제품",
        "세일즈는 CEO의 첫 번째 업무입니다. 팔기 어렵다면 제품이 문제입니다. "
        "'완성되면 팔겠다'는 생각 자체가 시장과 단절된 신호일 수 있습니다.",
    ),
    (
        "③", "③",
        '"너무 잘 된다"는 말이',
        "가장 위험한 신호",
        "성장이 빠를수록 구조의 균열이 보이지 않습니다. "
        "축하할 때가 가장 점검해야 할 순간입니다. "
        "속도에 취하면 방향을 잃습니다.",
    ),
    (
        "④", "④",
        "직원에게 주인의식 심기 =",
        "세상에서 제일 어려운 일",
        "주인의식은 교육이 아닌 경험으로 생깁니다. "
        "책임에 걸맞은 권한과 보상이 먼저입니다. "
        "구조 없는 주인의식 강요는 소진(번아웃)을 만듭니다.",
    ),
    (
        "⑤", "⑤",
        "채용보다 '해고'가",
        "조직 문화를 결정한다",
        "누구를 내보내느냐가 우리가 무엇을 중요시하는지 보여줍니다. "
        "해고는 가장 어렵지만 가장 명확한 문화 메시지입니다. "
        "오래 방치할수록 팀 전체의 신뢰가 무너집니다.",
    ),
    (
        "⑥", "⑥",
        "큰 성공보다 '작은 기적'을",
        "자주 만들어라",
        "소규모 승리가 팀의 믿음을 만들고, 믿음이 쌓여 큰 도전을 가능하게 합니다. "
        "원대한 목표는 작은 기적들의 누적 위에서 달성됩니다.",
    ),
    (
        "⑦", "⑦",
        "AI 시대, 90점은 AI가",
        "'마지막 1%'만 살아남는다",
        "AI가 90점 결과를 순식간에 만들어주는 세상. "
        "인간만의 맥락 판단력과 감각이 나머지 10%를 결정합니다. "
        "그 1%의 밀도가 결국 브랜드와 개인의 가치를 가릅니다.",
    ),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"출력 경로: {OUT_DIR}")

    img = render_cover()
    img.convert("RGB").save(OUT_DIR / "instagram-carousel-01.jpg", quality=95, optimize=True)
    print("  ✓ instagram-carousel-01.jpg (커버)")

    for idx, (emoji, label, headline, point, body) in enumerate(TRUTHS, start=2):
        img = render_truth(idx, emoji, label, headline, point, body)
        fname = f"instagram-carousel-{idx:02d}.jpg"
        img.convert("RGB").save(OUT_DIR / fname, quality=95, optimize=True)
        print(f"  ✓ {fname}")

    print(f"\n총 {len(TRUTHS) + 1}장 생성 완료")


if __name__ == "__main__":
    main()
