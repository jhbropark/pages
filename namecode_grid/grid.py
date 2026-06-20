import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT="/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
def F(sz): return ImageFont.truetype(FONT, sz)
ACCENT=(94,234,212); WHITE=(245,245,245); GRAY=(150,160,170); BG=(8,9,12)

cells=[ # url, category, label, message(None if image), reel(bool)
 ("https://gen.krea.ai/images/065a1b83-be8e-455b-a033-fd7d72e38d17.png","ARTWORK","CUBE / 001",None,True),
 ("https://gen.krea.ai/images/f96ee6b3-0ece-4146-8d08-bbab489f6e5c.png","MICRO","bio · 002",None,True),
 ("https://gen.krea.ai/images/aed9c359-f620-4c9f-a0e4-2343ad3d9aab.png","MESSAGE","",("우리는","메시지를","전달합니다"),False),
 ("https://gen.krea.ai/images/44b9d54a-08ec-41cd-ac56-d9c02b65921f.png","PROCESS","code · 004",None,False),
 ("https://gen.krea.ai/images/356c9d38-d7fd-4fcf-8a04-14dea1d6c6f3.png","ARTWORK","installation",None,True),
 ("https://gen.krea.ai/images/d827ec7f-5ffc-4500-aba6-f5e8b22e0201.png","MICRO","nature · 006",None,False),
 ("https://gen.krea.ai/images/8c0f64c2-07c4-44fe-b5d0-8112b038fa0c.png","WORK","space",None,False),
 ("https://gen.krea.ai/images/8e8b0d4e-b5b4-454f-838a-f14e70830803.png","MESSAGE","",("자연 · 우주","·","생명과학"),False),
 ("https://gen.krea.ai/images/33b79d7f-043f-4578-84ff-1398f384e6e4.png","ARTWORK","CUBE",None,True),
]

T=360; G=6  # tile size, gutter
def fetch(u):
    r=requests.get(u,timeout=60); 
    from io import BytesIO
    return Image.open(BytesIO(r.content)).convert("RGB")

def make_tile(img, cat, label, msg, reel):
    im=img.resize((T,T)).copy()
    # darken slightly for cohesion
    ov=Image.new("RGB",(T,T),(0,0,10)); im=Image.blend(im,ov,0.12)
    d=ImageDraw.Draw(im,"RGBA")
    if msg:
        # darken more + centered korean text
        im=Image.blend(im,Image.new("RGB",(T,T),(5,6,10)),0.45); d=ImageDraw.Draw(im,"RGBA")
        fs=46 if len(msg[0])<6 else 38
        total=len(msg)*(fs+10)
        y=(T-total)//2
        for li,line in enumerate(msg):
            f=F(fs); col=ACCENT if li==len(msg)//2 else WHITE
            w=d.textlength(line,font=f); d.text(((T-w)//2,y),line,font=f,fill=col); y+=fs+10
        d.line([(T//2-26,y+6),(T//2+26,y+6)],fill=ACCENT,width=2)
    # category tag top-left
    f=F(15); d.ellipse([14,16,22,24],fill=ACCENT)
    d.text((28,13),cat,font=f,fill=(225,235,235,235))
    # series label top? put small label bottom-right
    if label:
        f2=F(14); w=d.textlength(label,font=f2)
        d.text((T-w-14,T-26),label,font=f2,fill=(190,200,205,180))
    # namecode watermark bottom-left
    f3=F(16); d.text((14,T-28),"namecode",font=f3,fill=(255,255,255,150))
    # reel play icon top-right
    if reel:
        cx,cy=T-30,30; r=13
        d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=(255,255,255,220),width=2)
        d.polygon([(cx-4,cy-6),(cx-4,cy+6),(cx+7,cy)],fill=(255,255,255,230))
    return im

tiles=[make_tile(fetch(u),cat,lab,msg,reel) for (u,cat,lab,msg,reel) in cells]

GW=T*3+G*2
# ---- profile header ----
HH=470
W=GW; H=HH+GW
canvas=Image.new("RGB",(W,H),BG)
d=ImageDraw.Draw(canvas,"RGBA")
# avatar (circle from cube img) with accent ring
av=tiles[8].resize((150,150))
mask=Image.new("L",(150,150),0); ImageDraw.Draw(mask).ellipse([0,0,150,150],fill=255)
d.ellipse([38,40,38+158,40+158],outline=ACCENT,width=3)
canvas.paste(av,(42,44),mask)
# username + stats
d.text((230,52),"namecode_original",font=F(34),fill=WHITE)
stats=[("132","posts"),("8,540","followers"),("214","following")]
x=230
for num,lab in stats:
    d.text((x,108),num,font=F(26),fill=WHITE)
    d.text((x,142),lab,font=F(19),fill=GRAY); x+=180
# bio
by=210
d.text((40,by),"namecode  ·  디지털 크리에이터",font=F(24),fill=WHITE)
bio=["자연 · 우주 · 생명과학을 코드로 번역하는 뉴미디어 아트 스튜디오",
     "Immersive · Generative · Audiovisual",
     "📍 Seoul   ✉ info@namecode.art"]
yy=by+40
for ln in bio:
    d.text((40,yy),ln,font=F(21),fill=(205,212,218)); yy+=33
d.text((40,yy+4),"namecode.art",font=F(22),fill=ACCENT)
# highlights row
hx=50; hy=388
for name in ["ABOUT","ARTWORK","PROCESS","WORK","CONTACT"]:
    d.ellipse([hx,hy,hx+58,hy+58],outline=(90,100,110),width=2)
    d.text((hx+29-d.textlength("○",font=F(20))//2,hy+16),"◎",font=F(22),fill=GRAY)
    w=d.textlength(name,font=F(14)); d.text((hx+29-w//2,hy+62),name,font=F(14),fill=(190,198,205))
    hx+=120
# divider
d.line([(0,HH-2),(W,HH-2)],fill=(40,44,50),width=2)
# grid icon row hint
# ---- paste grid ----
for i,t in enumerate(tiles):
    r,c=divmod(i,3)
    x=c*(T+G); y=HH+r*(T+G)
    canvas.paste(t,(x,y))
canvas.save("namecode_feed_mockup.png")
# also a clean grid-only version
grid=Image.new("RGB",(GW,GW),BG)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); grid.paste(t,(c*(T+G),r*(T+G)))
grid.save("namecode_grid_only.png")
print("OK", canvas.size, grid.size)
