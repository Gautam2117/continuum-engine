"""Pixel Fables original thumbnail, built exclusively from this episode's 3D frames.

No synthetic platform screenshot, stock photo, borrowed game sprite or protected
competitor artwork is used. Original hero and world are captured from the
Blender render that is already being verified for release.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageEnhance

from .fonts import font
from .styles import rgb

W,H=1280,720


def pixel_poster(spec: dict, style, output, source: Image.Image) -> None:
    if source is None or min(source.size)<64:
        raise ValueError('Pixel Fables poster requires a real rendered source frame')
    src=source.convert('RGB')
    canvas=Image.new('RGB',(W,H),(11,17,29))
    # Dedicated action image occupies the right 52% of the 16:9 thumbnail.
    x=608
    region_w=W-x
    iw,ih=src.size
    ratio=max(region_w/iw,H/ih)
    enlarged=src.resize((max(region_w,round(iw*ratio)),max(H,round(ih*ratio))),Image.Resampling.LANCZOS)
    left=max(0,(enlarged.width-region_w)//2)
    top=max(0,round((enlarged.height-H)*.39))
    framed=enlarged.crop((left,top,left+region_w,top+H))
    framed=ImageEnhance.Contrast(framed).enhance(1.13)
    canvas.paste(framed,(x,0))
    # Smooth intentional compositing edge; original voxel actor remains visible
    # rather than being buried under a huge caption box.
    tint=Image.new('RGB',(1,1),(11,17,29))
    strip=ImageDraw.Draw(canvas,'RGBA')
    for dx in range(200):
        t=dx/199
        strip.line(((x-95+dx,0),(x-95+dx,H)),fill=(11,17,29,round(255*(1-t)**2)))
    d=ImageDraw.Draw(canvas,'RGBA')
    gold=(*rgb(style.accent),255)
    pale=(237,246,245,255)
    subdued=(167,191,194,255)
    badge_font=font(style.body,31)
    badge_text='PIXEL FABLES  /  01'
    badge_end=round(78+d.textlength(badge_text,font=badge_font)+23)
    d.rounded_rectangle((60,46,badge_end,100),radius=10,fill=(27,52,57,255),outline=(90,162,150,255),width=2)
    d.text((78,55),badge_text,font=badge_font,fill=pale)
    text=('THE ROAD',"WASN'T",'THERE.')
    heights=(184,314,441)
    for k,(phrase,y) in enumerate(zip(text,heights)):
        fs=104 if k<2 else 119
        f=font(style.display,fs)
        while d.textlength(phrase,font=f)>530 and fs>45:
            fs-=3
            f=font(style.display,fs)
        d.text((56,y),phrase,font=f,fill=gold if k==2 else pale,
               stroke_width=2,stroke_fill=(12,22,30,255))
    # One visual payoff line, not a second competing headline.
    d.text((66,613),'HE WALKED ANYWAY',font=font(style.body,37),fill=subdued)
    # Quiet baseline sits below, never on top of the small payoff text.
    d.rounded_rectangle((66,680,279,686),radius=3,fill=gold)
    canvas.save(output,format='JPEG',quality=91,subsampling=0,optimize=True)
