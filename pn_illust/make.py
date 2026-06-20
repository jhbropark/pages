import requests
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
imgs = {
 1: "https://gen.krea.ai/images/4a3429a3-4e57-42d0-9299-fed7ec36580b.png",
 2: "https://gen.krea.ai/images/30f5aa8f-0a22-4aab-bc1d-3ab97f7f56a1.png",
 3: "https://gen.krea.ai/images/c74aa2e6-4604-4297-a655-a378107a40c9.png",
}
content = {
 1: ("PN 성분 침투 시작",
     "PN(폴리뉴클레오타이드) 성분이 피부 표면에 도포되어\n표피층을 통과하기 시작합니다."),
 2: ("진피층 도달 · 침투",
     "PN 분자가 진피층까지 깊숙이 침투하여\n콜라겐 섬유 사이로 확산됩니다."),
 3: ("피부 재생 유도",
     "진피층에서 콜라겐 생성과 세포 재생이 활성화되어\n탄력 있는 피부로 재생됩니다."),
}
# 공통 레이어 라벨 (위->아래)
layers = [
 ("표피", "Epidermis", (96,165,250)),
 ("진피", "Dermis",    (59,130,246)),
 ("피하", "Subcutaneous", (147,197,253)),
]

W = 1024
HEADER = 150
SIDE = 250          # 오른쪽 레이어 패널
FOOTER = 190
IMG = 1024
TOTAL_W = W + SIDE
TOTAL_H = HEADER + IMG + FOOTER

def F(sz, bold=False):
    return ImageFont.truetype(FONT, sz)

ACCENT = (37, 99, 235)
DARK = (30, 41, 59)
GRAY = (100, 116, 139)

for n,(title,desc) in content.items():
    r = requests.get(imgs[n], timeout=60); 
    open(f"src{n}.png","wb").write(r.content)
    base = Image.open(f"src{n}.png").convert("RGB").resize((IMG,IMG))
    canvas = Image.new("RGB",(TOTAL_W,TOTAL_H),"white")
    # paste image
    canvas.paste(base,(0,HEADER))
    d = ImageDraw.Draw(canvas)
    # ===== Header =====
    d.rectangle([0,0,TOTAL_W,HEADER],fill=(239,246,255))
    d.rectangle([0,HEADER-6,TOTAL_W,HEADER],fill=ACCENT)
    # step badge
    badge_w=150
    d.rounded_rectangle([40,38,40+badge_w,38+74],radius=14,fill=ACCENT)
    bf=F(40); 
    txt=f"STEP {n}"
    bb=d.textbbox((0,0),txt,font=bf)
    d.text((40+(badge_w-(bb[2]-bb[0]))/2, 38+(74-(bb[3]-bb[1]))/2-bb[1]), txt, font=bf, fill="white")
    # title
    tf=F(54)
    d.text((40+badge_w+30, 44), title, font=tf, fill=DARK)
    # ===== Right layer panel =====
    px = W+20
    d.text((px, HEADER+10), "피부 단면", font=F(30), fill=GRAY)
    seg_h = IMG//3
    for i,(ko,en,col) in enumerate(layers):
        cy = HEADER + seg_h*i + seg_h//2
        # color dot
        d.ellipse([px, cy-46, px+34, cy-12], fill=col)
        d.text((px+46, cy-50), ko, font=F(40), fill=DARK)
        d.text((px, cy-2), en, font=F(24), fill=GRAY)
        # connector line to image segment
        d.line([(W, HEADER+seg_h*i+seg_h//2),(px-4, cy-28)], fill=col, width=3)
    # PN highlight note on dermis
    d.text((px, HEADER+IMG-70), "★ PN 작용 부위", font=F(26), fill=ACCENT)
    # ===== Footer description =====
    fy = HEADER+IMG
    d.rectangle([0,fy,TOTAL_W,TOTAL_H],fill=(248,250,252))
    d.rectangle([0,fy,TOTAL_W,fy+6],fill=ACCENT)
    df=F(36)
    yy=fy+34
    for line in desc.split("\n"):
        d.text((46,yy),line,font=df,fill=DARK); yy+=52
    # source caption
    d.text((46, TOTAL_H-34), "PN 성분 피부 재생 메커니즘 · 교육용 일러스트", font=F(22), fill=GRAY)
    out=f"PN_STEP{n}_kr.png"
    canvas.save(out)
    print("saved", out, canvas.size)
print("DONE")
