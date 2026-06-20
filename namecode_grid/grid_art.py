import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
R="/tmp/fnt/JetBrainsMono.ttf"; B="/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
def F(s,b=False): return ImageFont.truetype(B if b else R,s)
PAPER=(245,245,243); INK=(26,26,26); RED=(155,19,19); BLACK=(12,12,12); GRAY=(120,120,120); LINE=(48,48,48)
# url, work name, sim value, hero
cells=[
 ("https://gen.krea.ai/images/0e8fcae5-b3e4-4926-8ed4-f289b778e5cb.png","ORIGIN","60.512",False),
 ("https://gen.krea.ai/images/4055830a-e741-4e0d-ab68-7af6cfefd6ff.png","BIOSIGNAL","24.301",False),
 ("https://gen.krea.ai/images/ce4cc011-a64e-43c9-87aa-daafccfb329e.png","DATA.FLOW","88.140",False),
 ("https://gen.krea.ai/images/983a978e-eb22-4c8b-9e86-df4ed0929665.png","SOURCE","12.007",False),
 ("https://gen.krea.ai/images/0130532e-332f-4df5-8939-775ba09f61df.png","CUBE","45.992",True),
 ("https://gen.krea.ai/images/b4ed2aea-a0d0-43cb-9f19-fa52f218ec0c.png","MINERAL","31.408",False),
 ("https://gen.krea.ai/images/1bf56457-eb83-4712-baee-b0d7dd7dcae1.png","ROOM","07.255",False),
 ("https://gen.krea.ai/images/4e8f0515-ba75-4d1b-8356-3c1f205fbbca.png","COSMOS","99.018",False),
 ("https://gen.krea.ai/images/b44d47e0-f3d5-4b7e-b384-124c691b113c.png","LATTICE","53.677",False),
]
T=360; G=10
def fetch(u): return Image.open(BytesIO(requests.get(u,timeout=60).content)).convert("L").resize((T,T))
def duo(u): return ImageOps.colorize(ImageOps.autocontrast(fetch(u),cutoff=1),black=BLACK,white=PAPER).convert("RGB")
def tile(c):
    u,name,val,hero=c
    im=duo(u); d=ImageDraw.Draw(im,"RGBA")
    label=f"namecode - {name} | {val}"
    f=F(14); tw=d.textlength(label,font=f)
    x,y=12,12; pad=7; bx2=x+tw+pad*2; by2=y+24
    d.rounded_rectangle([x,y,bx2,by2],radius=3,fill=(18,18,18,170))
    d.text((x+pad,y+4),label,font=f,fill=PAPER)
    return im
tiles=[tile(c) for c in cells]; GW=T*3+G*2
# grid only
g=Image.new("RGB",(GW,GW),INK)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); g.paste(t,(c*(T+G),r*(T+G)))
g.save("namecode_grid_only_art.png")
# profile mockup
HH=470; W=GW; H=HH+GW
cv=Image.new("RGB",(W,H),INK); d=ImageDraw.Draw(cv,"RGBA")
av=tiles[4].resize((150,150)); m=Image.new("L",(150,150),0); ImageDraw.Draw(m).ellipse([0,0,150,150],fill=255)
d.ellipse([38,40,196,198],outline=PAPER,width=2); cv.paste(av,(42,44),m)
d.text((230,55),"namecode_original",font=F(30,True),fill=PAPER)
ww=d.textlength("namecode_original",font=F(30,True)); d.ellipse([230+ww+12,64,230+ww+22,74],fill=RED)
for i,(n,l) in enumerate([("148","posts"),("9,210","followers"),("214","following")]):
    x=230+i*185; d.text((x,108),n,font=F(24,True),fill=PAPER); d.text((x,140),l,font=F(15),fill=GRAY)
by=212; d.text((40,by),"namecode // New Media Art Studio",font=F(21,True),fill=PAPER)
for j,ln in enumerate(["Translating nature, cosmos & life science into code",
                       "CUBE - a living trilogy . Immersive . Generative",
                       "namecode@namecode.kr"]):
    d.text((40,by+38+j*30),ln,font=F(16),fill=(205,205,205))
d.text((40,by+38+3*30+4),"namecode.kr",font=F(18,True),fill=PAPER)
hx=50; hy=392
for nm in ["ABOUT","CUBE","PROCESS","WORK","CONTACT"]:
    d.ellipse([hx,hy,hx+56,hy+56],outline=(90,90,90),width=2)
    w=d.textlength(nm,font=F(11)); d.text((hx+28-w//2,hy+60),nm,font=F(11),fill=(175,175,175)); hx+=118
d.line([(0,HH-2),(W,HH-2)],fill=LINE,width=2)
for i,t in enumerate(tiles):
    r,c=divmod(i,3); cv.paste(t,(c*(T+G),HH+r*(T+G)))
cv.save("namecode_feed_mockup_art.png")
print("OK",cv.size)
