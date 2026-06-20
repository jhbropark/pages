import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
R="/tmp/fnt/JetBrainsMono.ttf"
def F(s): return ImageFont.truetype(R,s)
PAPER=(245,245,243); BLACK=(12,12,12); INK=(26,26,26)
def make(url,val,out,S=1080):
    g=ImageOps.autocontrast(Image.open(BytesIO(requests.get(url,timeout=60).content)).convert("L").resize((S,S)),cutoff=1)
    im=ImageOps.colorize(g,black=BLACK,white=PAPER).convert("RGB")
    d=ImageDraw.Draw(im,"RGBA")
    label=f"namecode - OCCULTATION | {val}"
    f=F(30); tw=d.textlength(label,font=f); x,y=34,34; pad=14
    d.rounded_rectangle([x,y,x+tw+pad*2,y+52],radius=6,fill=(18,18,18,170))
    d.text((x+pad,y+12),label,font=f,fill=PAPER)
    im.save(out); return im
a=make("https://gen.krea.ai/images/1c7510c3-c882-450c-98eb-f850821f7d0f.png","45.992","apod_v1.png")
b=make("https://gen.krea.ai/images/4f7e493c-13f2-4621-9b81-200d2b2538e1.png","45.992","apod_v2.png")
# side by side compare
G=20; cmp=Image.new("RGB",(1080*2+G,1080),INK)
cmp.paste(a.resize((1080,1080)),(0,0)); cmp.paste(b.resize((1080,1080)),(1080+G,0))
cmp=cmp.resize((1080,540)); cmp.save("apod_compare.png")
print("OK")
