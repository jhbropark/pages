import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
FONT="/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
def F(s): return ImageFont.truetype(FONT,s)
PAPER=(245,245,243); INK=(26,26,26); RED=(155,19,19); BLACK=(12,12,12)
GRAY=(120,120,120); LINE=(48,48,48)
# Red used ONLY as a rare accent (<10% area): hero thin frame + hero pill,
# one keyword per message card, one header dot + link. Everything else mono.
cells=[
 ("https://gen.krea.ai/images/0e8fcae5-b3e4-4926-8ed4-f289b778e5cb.png","ARTWORK","CUBE Ⅰ",None,None,True,False),
 ("https://gen.krea.ai/images/4055830a-e741-4e0d-ab68-7af6cfefd6ff.png","MICRO","living data",None,None,True,False),
 (None,"MESSAGE","",("살아있는","데이터","아트"),1,False,False),
 ("https://gen.krea.ai/images/983a978e-eb22-4c8b-9e86-df4ed0929665.png","PROCESS","openFrameworks",None,None,False,False),
 ("https://gen.krea.ai/images/0130532e-332f-4df5-8939-775ba09f61df.png","ARTWORK","CUBE Ⅱ",None,None,True,True),
 ("https://gen.krea.ai/images/b4ed2aea-a0d0-43cb-9f19-fa52f218ec0c.png","MICRO","nature / 006",None,None,False,False),
 ("https://gen.krea.ai/images/1bf56457-eb83-4712-baee-b0d7dd7dcae1.png","WORK","exhibition",None,None,False,False),
 (None,"MESSAGE","",("CUBE","하나의 살아있는","3부작"),0,False,False),
 ("https://gen.krea.ai/images/b44d47e0-f3d5-4b7e-b384-124c691b113c.png","ARTWORK","CUBE Ⅲ",None,None,True,False),
]
T=360; G=10
def fetch(u): return Image.open(BytesIO(requests.get(u,timeout=60).content)).convert("L").resize((T,T))
def duo(u): return ImageOps.colorize(ImageOps.autocontrast(fetch(u),cutoff=1),black=BLACK,white=PAPER).convert("RGB")
def tile(c):
    u,cat,lab,msg,ri,reel,hero=c
    if msg:
        im=Image.new("RGB",(T,T),INK); d=ImageDraw.Draw(im)
        fs=42 if len(msg[0])<5 else 30
        tot=len(msg)*(fs+10); y=(T-tot)//2
        for i,ln in enumerate(msg):
            f=F(fs); w=d.textlength(ln,font=f)
            d.text(((T-w)//2,y),ln,font=f,fill=(RED if i==ri else PAPER)); y+=fs+10
        d.line([(T//2-22,y+8),(T//2+22,y+8)],fill=GRAY,width=1)
    else: im=duo(u)
    d=ImageDraw.Draw(im,"RGBA")
    # category: outline pill, white text (red only on hero)
    f=F(14); w=d.textlength(cat,font=f); pad=8
    if hero:
        d.rounded_rectangle([14,14,14+w+pad*2,40],radius=6,fill=RED); d.text((14+pad,16),cat,font=f,fill=PAPER)
    else:
        d.rounded_rectangle([14,14,14+w+pad*2,40],radius=6,outline=PAPER,width=1); d.text((14+pad,16),cat,font=f,fill=PAPER)
    # bottom strip
    d.rectangle([0,T-30,T,T],fill=INK); d.line([(0,T-30),(T,T-30)],fill=LINE,width=1)
    d.text((12,T-25),"namecode",font=F(16),fill=PAPER)
    if lab:
        w=d.textlength(lab,font=F(13)); d.text((T-w-12,T-23),lab,font=F(13),fill=GRAY)
    if reel:
        cx,cy=T-28,28; r=13; d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=PAPER,width=2)
        d.polygon([(cx-4,cy-6),(cx-4,cy+6),(cx+7,cy)],fill=PAPER)
    d.rectangle([0,0,T-1,T-1],outline=(RED if hero else LINE),width=(2 if hero else 1))
    return im
tiles=[tile(c) for c in cells]; GW=T*3+G*2
HH=470; W=GW; H=HH+GW
cv=Image.new("RGB",(W,H),INK); d=ImageDraw.Draw(cv,"RGBA")
av=tiles[8].resize((150,150)); m=Image.new("L",(150,150),0); ImageDraw.Draw(m).ellipse([0,0,150,150],fill=255)
d.ellipse([38,40,196,198],outline=PAPER,width=2); cv.paste(av,(42,44),m)
# wordmark + tiny red dot (the single signature mark)
d.text((230,52),"namecode_original",font=F(34),fill=PAPER)
ww=d.textlength("namecode_original",font=F(34)); d.ellipse([230+ww+10,66,230+ww+20,76],fill=RED)
for i,(n,l) in enumerate([("148","posts"),("9,210","followers"),("214","following")]):
    x=230+i*180; d.text((x,108),n,font=F(26),fill=PAPER); d.text((x,142),l,font=F(18),fill=GRAY)
by=210; d.text((40,by),"namecode  ·  디지털 크리에이터",font=F(24),fill=PAPER)
lines=["자연 · 우주 · 생명과학을 코드로 번역하는 뉴미디어 아트 스튜디오",
       "▶ CUBE : 살아있는 3부작  ·  Immersive · Generative",
       "✉ namecode@namecode.kr"]
for j,ln in enumerate(lines): d.text((40,by+40+j*33),ln,font=F(20),fill=(205,205,205))
d.text((40,by+40+3*33+4),"namecode.kr",font=F(22),fill=PAPER)
hx=50; hy=388
for nm in ["ABOUT","CUBE","PROCESS","WORK","CONTACT"]:
    d.ellipse([hx,hy,hx+58,hy+58],outline=(90,90,90),width=2)
    w=d.textlength(nm,font=F(13)); d.text((hx+29-w//2,hy+62),nm,font=F(13),fill=(175,175,175)); hx+=120
d.line([(0,HH-2),(W,HH-2)],fill=LINE,width=2)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); cv.paste(t,(c*(T+G),HH+r*(T+G)))
cv.save("namecode_feed_mockup_dark2.png")
g=Image.new("RGB",(GW,GW),INK)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); g.paste(t,(c*(T+G),r*(T+G)))
g.save("namecode_grid_only_dark2.png")
# crude red-area check
from PIL import Image as I
px=g.getdata(); red=sum(1 for r,gg,b in px if abs(r-155)<45 and gg<70 and b<70)
print("red%% of grid:", round(100*red/len(px),2))
print("OK",cv.size)
