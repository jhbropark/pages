import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
FONT="/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
def F(sz): return ImageFont.truetype(FONT, sz)
PAPER=(250,250,248); INK=(26,26,26)
# FUSE*-informed: main diagonal 1-5-9 = CUBE flagship trilogy (like FUSE* Ljós/Dökk/Sál)
cells=[
 ("https://gen.krea.ai/images/0de469d2-560c-42ff-99ea-8f616d0eb3ce.png","ARTWORK","CUBE Ⅰ",None,True),
 ("https://gen.krea.ai/images/02d763d8-4d35-46ae-b9f5-d7bfd86ae94d.png","MICRO","living data",None,True),
 (None,"MESSAGE","",("살아있는","데이터","아트"),False),
 ("https://gen.krea.ai/images/93a3de7a-bc44-461e-99eb-4c3b78264139.png","PROCESS","openFrameworks",None,False),
 ("https://gen.krea.ai/images/564966eb-5c9f-48b4-9f17-5d1b8fcff929.png","ARTWORK","CUBE Ⅱ",None,True),
 ("https://gen.krea.ai/images/ceba45bc-2370-47ae-acde-b4d8202f90e2.png","MICRO","nature / 006",None,False),
 ("https://gen.krea.ai/images/ae19872b-9970-406e-bf60-60f8b3204472.png","WORK","exhibition",None,False),
 (None,"MESSAGE","",("CUBE","하나의 살아있는","3부작"),False),
 ("https://gen.krea.ai/images/ca2e80bc-0f19-4d99-8dc6-3aa313b0b425.png","ARTWORK","CUBE Ⅲ",None,True),
]
T=360; G=8
def duotone(u):
    im=Image.open(BytesIO(requests.get(u,timeout=60).content)).convert("L").resize((T,T))
    im=ImageOps.autocontrast(im,cutoff=1)
    return ImageOps.colorize(im,black=INK,white=PAPER).convert("RGB")
def pill(d,x,y,t,f,pad=8,h=26):
    w=d.textlength(t,font=f); d.rounded_rectangle([x,y,x+w+pad*2,y+h],radius=6,fill=INK)
    d.text((x+pad,y+(h-f.size)//2-1),t,font=f,fill=PAPER); return w+pad*2
def tile(c):
    u,cat,lab,msg,reel=c
    if msg:
        im=Image.new("RGB",(T,T),PAPER); d=ImageDraw.Draw(im)
        fs=42 if len(msg[0])<5 else 32
        tot=len(msg)*(fs+10); y=(T-tot)//2
        for ln in msg:
            f=F(fs); w=d.textlength(ln,font=f); d.text(((T-w)//2,y),ln,font=f,fill=INK); y+=fs+10
        d.line([(T//2-24,y+8),(T//2+24,y+8)],fill=INK,width=2)
    else: im=duotone(u)
    d=ImageDraw.Draw(im,"RGBA")
    pill(d,14,14,cat,F(14))
    d.rectangle([0,T-30,T,T],fill=PAPER); d.line([(0,T-30),(T,T-30)],fill=INK,width=1)
    d.text((12,T-25),"namecode",font=F(16),fill=INK)
    if lab:
        w=d.textlength(lab,font=F(13)); d.text((T-w-12,T-23),lab,font=F(13),fill=INK)
    if reel:
        cx,cy=T-28,28; r=13; d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=INK)
        d.polygon([(cx-4,cy-6),(cx-4,cy+6),(cx+7,cy)],fill=PAPER)
    d.rectangle([0,0,T-1,T-1],outline=INK,width=1); return im
tiles=[tile(c) for c in cells]; GW=T*3+G*2
HH=470; W=GW; H=HH+GW
cv=Image.new("RGB",(W,H),PAPER); d=ImageDraw.Draw(cv,"RGBA")
av=tiles[8].resize((150,150)); m=Image.new("L",(150,150),0); ImageDraw.Draw(m).ellipse([0,0,150,150],fill=255)
d.ellipse([38,40,196,198],outline=INK,width=3); cv.paste(av,(42,44),m)
d.text((230,52),"namecode_original",font=F(34),fill=INK)
for i,(n,l) in enumerate([("148","posts"),("9,210","followers"),("214","following")]):
    x=230+i*180; d.text((x,108),n,font=F(26),fill=INK); d.text((x,142),l,font=F(18),fill=INK)
by=210; d.text((40,by),"namecode  ·  디지털 크리에이터",font=F(24),fill=INK)
for j,ln in enumerate(["자연 · 우주 · 생명과학을 코드로 번역하는 뉴미디어 아트 스튜디오",
                       "▶ CUBE : 살아있는 3부작  ·  Immersive · Generative",
                       "✉ namecode@namecode.kr"]):
    d.text((40,by+40+j*33),ln,font=F(20),fill=INK)
d.text((40,by+40+3*33+4),"namecode.kr",font=F(22),fill=INK)
hx=50; hy=388
for nm in ["ABOUT","CUBE","PROCESS","WORK","CONTACT"]:
    d.ellipse([hx,hy,hx+58,hy+58],outline=INK,width=2)
    w=d.textlength(nm,font=F(13)); d.text((hx+29-w//2,hy+62),nm,font=F(13),fill=INK); hx+=120
d.line([(0,HH-2),(W,HH-2)],fill=INK,width=2)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); cv.paste(t,(c*(T+G),HH+r*(T+G)))
cv.save("namecode_feed_mockup_fuse.png")
g=Image.new("RGB",(GW,GW),PAPER)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); g.paste(t,(c*(T+G),r*(T+G)))
g.save("namecode_grid_only_fuse.png")
print("OK",cv.size)
