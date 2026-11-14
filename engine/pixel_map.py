"""Original Pixel Fables 2D playable-map illustration between voxel 3D shots.

No external art, no random mascot. Uses the actual channel story: a route is
revealed as the original protagonist commits to each step. Scenes explicitly
label the content as fictional and preserve a lower-safe caption region.
"""
from __future__ import annotations

import math
from collections.abc import Iterator
from PIL import Image, ImageDraw
from .fonts import font
from .styles import rgb

PHASES=frozenset({'lost','choice'})
GRID=(9,12)


def _route(phase: str):
    if phase=='lost':
        return ((1,10),(2,10),(2,9),(3,9),(3,8),(3,7),(4,7),(4,6),(5,6),(5,5),(6,5),(6,4),(7,4),(7,3))
    return ((1,10),(2,10),(3,10),(3,9),(4,9),(4,8),(5,8),(5,7),(5,6),(6,6),(6,5),(6,4),(7,4),(7,3))


def scene_pixel_map(c,dur:float,p:dict,words:list[str])->Iterator[Image.Image]:
    phase=p.get('phase')
    if phase not in PHASES:
        raise ValueError('Pixel Fables map requires phase lost or choice')
    W,H=c.W,c.H
    cols,rows=GRID
    margin=W*.11
    # The map must stop above its footer and the YouTube caption zone.
    cell=min((W-2*margin)/cols,(H*.35)/rows)
    x0=(W-cols*cell)/2
    y0=H*.27
    fhead=font(c.style.display,max(22,int(c.u*5.0)))
    fbody=font(c.style.body,max(14,int(c.u*2.4)))
    fg=rgb(c.style.ink)
    accent=rgb(c.style.accent)
    blue=(25,55,79,255)
    soil=(39,87,70,255)
    tile_edge=(62,119,96,255)
    path=_route(phase)
    label=str(p.get('title') or ('THE MAP NEVER KNEW' if phase=='lost' else 'ONE STEP AT A TIME'))[:55]
    for i in range(max(1,round(dur*24))):
        prog=i/max(1,round(dur*24)-1)
        progressed=prog*prog*(3-2*prog)
        img,d=c.canvas(i/24)
        d.rounded_rectangle((W*.075,H*.215,W*.925,H*.825),radius=W*.018,
                            fill=(12,26,37,252),outline=(82,123,112,255),width=max(2,int(W*.003)))
        d.text((W*.12,H*.239),label,font=fhead,fill=fg)
        d.text((W*.12,H*.297-fbody.size*.2),'ORIGINAL VOXEL JOURNEY / LEVEL 01',
               font=fbody,fill=accent)
        for y in range(rows):
            for x in range(cols):
                px=x0+x*cell
                py=y0+y*cell+H*.105
                # Staggered tiles create depth and a navigable space rather than
                # another static slide of unrelated decorative rectangles.
                outline=tile_edge if ((x+y)%4!=0) else (85,140,114,255)
                face=(31,72,58,255) if ((x*7+y*11)%5) else soil
                d.rectangle((px+1,py+1,px+cell-3,py+cell-3),fill=face,outline=outline,width=max(1,round(cell*.04)))
                if (x*13+y*3)%17==0 and (x,y) not in path:
                    d.rectangle((px+cell*.26,py+cell*.16,px+cell*.74,py+cell*.64),
                                fill=(20,45,56,255),outline=(60,106,93,255),width=2)
        reveal=max(1,round(progressed*(len(path)-1)))
        points=[]
        for j,(tx,ty) in enumerate(path):
            xx=x0+(tx+.5)*cell
            yy=y0+(ty+.5)*cell+H*.105
            points.append((xx,yy))
            if j<=reveal:
                d.rectangle((xx-cell*.22,yy-cell*.22,xx+cell*.22,yy+cell*.22),
                            fill=(249,187,65,255) if phase=='choice' else (114,198,186,255))
        for j in range(min(reveal,len(path)-1)):
            d.line((points[j],points[j+1]),fill=accent,width=max(3,round(cell*.13)),joint='curve')
        pos=progressed*(len(path)-1)
        index=min(int(pos),len(path)-2)
        frac=pos-index
        hx=points[index][0]*(1-frac)+points[index+1][0]*frac
        hy=points[index][1]*(1-frac)+points[index+1][1]*frac
        d.rectangle((hx-cell*.27,hy-cell*.35,hx+cell*.27,hy+cell*.21),fill=(236,127,63,255),
                    outline=(24,33,41,255),width=max(2,int(cell*.08)))
        d.rectangle((hx-cell*.16,hy-cell*.45,hx+cell*.16,hy-cell*.31),fill=(48,37,37,255))
        d.line((hx-cell*.18,hy+cell*.3,hx+cell*.18,hy+cell*.3),fill=(27,42,59,255),width=max(2,int(cell*.1)))
        d.text((W*.14,H*.751),'UNKNOWN ROUTE' if phase=='lost' else 'CHOOSE A REAL STEP',
               font=fhead,fill=accent)
        d.text((W*.14,H*.788),'FICTIONAL STORY  •  ORIGINAL GAME WORLD',
               font=fbody,fill=fg)
        yield img.convert('RGB')
