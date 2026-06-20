import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
FONT="/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
def F(s): return ImageFont.truetype(FONT,s)
PAPER=(250,250,248); INK=(26,26,26); RED=(155,19,19); BLACK=(12,12,12)
# url, category, label, message(tuple or None), redline_idx, reel, hero(red tritone)
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
def duo(u,hero=False):
    g=ImageOps.autocontrast(fetch(u),cutoff=1)
    if hero:
        return ImageOps.colorize(g,black=BLACK,white=PAPER,mid=RED).convert("RGB")
    return ImageOps.colorize(g,black=BLACK,white=PAPER).convert("RGB")
def pill(d,x,y,t,f,col=RED,tc=PAPER,pad=8,h=26):
    w=d.textlength(t,font=f); d.rounded_rectangle([x,y,x+w+pad*2,y+h],radius=6,fill=col)
    d.text((x+pad,y+(h-f.size)//2-1),t,font=f,fill=tc); return w+pad*2
def tile(c):
    u,cat,lab,msg,ri,reel,hero=c
    if msg:
        im=Image.new("RGB",(T,T),INK); d=ImageDraw.Draw(im)
        fs=42 if len(msg[0])<5 else 30
        tot=len(msg)*(fs+10); y=(T-tot)//2
        for i,ln in enumerate(msg):
            f=F(fs); w=d.textlength(ln,font=f)
            d.text(((T-w)//2,y),ln,font=f,fill=(RED if i==ri else PAPER)); y+=fs+10
        d.line([(T//2-24,y+8),(T//2+24,y+8)],fill=RED,width=2)
    else: im=duo(u,hero)
    d=ImageDraw.Draw(im,"RGBA")
    pill(d,14,14,cat,F(14))
    d.rectangle([0,T-30,T,T],fill=INK); d.line([(0,T-30),(T,T-30)],fill=RED,width=1)
    d.text((12,T-25),"namecode",font=F(16),fill=PAPER)
    if lab:
        w=d.textlength(lab,font=F(13)); d.text((T-w-12,T-23),lab,font=F(13),fill=RED)
    if reel:
        cx,cy=T-28,28; r=13; d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=RED)
        d.polygon([(cx-4,cy-6),(cx-4,cy+6),(cx+7,cy)],fill=PAPER)
    d.rectangle([0,0,T-1,T-1],outline=(RED if hero else (50,50,50)),width=(2 if hero else 1))
    return im
tiles=[tile(c) for c in cells]; GW=T*3+G*2
HH=470; W=GW; H=HH+GW
cv=Image.new("RGB",(W,H),INK); d=ImageDraw.Draw(cv,"RGBA")
av=tiles[8].resize((150,150)); m=Image.new("L",(150,150),0); ImageDraw.Draw(m).ellipse([0,0,150,150],fill=255)
d.ellipse([38,40,196,198],outline=RED,width=3); cv.paste(av,(42,44),m)
d.text((230,52),"namecode_original",font=F(34),fill=PAPER)
for i,(n,l) in enumerate([("148","posts"),("9,210","followers"),("214","following")]):
    x=230+i*180; d.text((x,108),n,font=F(26),fill=PAPER); d.text((x,142),l,font=F(18),fill=(150,150,150))
by=210; d.text((40,by),"namecode  ·  디지털 크리에이터",font=F(24),fill=PAPER)
lines=["자연 · 우주 · 생명과학을 코드로 번역하는 뉴미디어 아트 스튜디오",
       "▶ CUBE : 살아있는 3부작  ·  Immersive · Generative",
       "✉ namecode@namecode.kr"]
for j,ln in enumerate(lines): d.text((40,by+40+j*33),ln,font=F(20),fill=(210,210,210))
d.text((40,by+40+3*33+4),"namecode.kr",font=F(22),fill=RED)
hx=50; hy=388
for nm in ["ABOUT","CUBE","PROCESS","WORK","CONTACT"]:
    ring=RED if nm=="CUBE" else (90,90,90)
    d.ellipse([hx,hy,hx+58,hy+58],outline=ring,width=2)
    w=d.textlength(nm,font=F(13)); d.text((hx+29-w//2,hy+62),nm,font=F(13),fill=(PAPER if nm=="CUBE" else (170,170,170)))
    hx+=120
d.line([(0,HH-2),(W,HH-2)],fill=(50,50,50),width=2)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); cv.paste(t,(c*(T+G),HH+r*(T+G)))
cv.save("namecode_feed_mockup_dark.png")
g=Image.new("RGB",(GW,GW),INK)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); g.paste(t,(c*(T+G),r*(T+G)))
g.save("namecode_grid_only_dark.png")
print("OK",cv.size)
