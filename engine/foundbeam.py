"""Original Foundbeam illustrated desktop acquisition-system stage.

These are fictional users and abstract interface illustrations, not actual
Dropbox screenshots. Distinguishes folder sharing from rewarded referrals.
"""
from __future__ import annotations
import math
from collections.abc import Iterator

from PIL import Image, ImageDraw

from .fonts import font
from .styles import rgb

VARIANTS = frozenset({"split", "folder", "referral", "meter", "milestone", "signup", "return"})


def _rounded(draw, box, fill, radius, outline=None, width=1):
    draw.rounded_rectangle(tuple(int(x) for x in box), radius=max(2, int(radius)), fill=fill,
                           outline=outline, width=max(1, int(width)))


def _label(draw, x, y, txt, f, color, max_width):
    if draw.textlength(txt, font=f) <= max_width:
        draw.text((x, y), txt, font=f, fill=color)
        return
    while len(txt)>1 and draw.textlength(txt + '…',font=f)>max_width:
        txt=txt[:-1]
    draw.text((x,y),txt+'…',font=f,fill=color)


def _screen(draw, rect, *, title, owner, unit, f_body, f_head, ink, muted, accent, secondary):
    x0,y0,x1,y1=rect
    width, height=x1-x0,y1-y0
    radius=max(4,int(unit*1.3))
    _rounded(draw,rect,(25,27,34,255),radius,outline=(113,118,135,255),width=max(2,int(unit*.2)))
    _rounded(draw,(x0+unit*.7,y0+unit*.7,x1-unit*.7,y0+height*.21),(39,41,51,255),unit*.7)
    _label(draw,x0+unit*1.5,y0+unit*1.1,owner.upper(),f_body,accent,width-unit*3)
    _label(draw,x0+unit*1.7,y0+height*.26,title,f_head,ink,width-unit*3.4)
    folder=(x0+width*.18,y0+height*.50,x0+width*.77,y0+height*.70)
    _rounded(draw,folder,secondary,unit*.75)
    _rounded(draw,(folder[0]+unit*.5,folder[1]-unit*.6,folder[0]+width*.30,folder[1]+unit*.25),secondary,unit*.3)
    draw.line([(x0+width*.22,y0+height*.80),(x0+width*.78,y0+height*.80)],fill=(107,111,126),width=max(2,int(unit*.20)))
    return (x0+width*.5,y0+height*.47)


def _letter(draw,x,y,unit,ink,accent,scale=1.0):
    w,h=unit*4.9*scale,unit*3.25*scale
    _rounded(draw,(x-w/2,y-h/2,x+w/2,y+h/2),(243,232,216,255),unit*.43*scale)
    draw.line([(x-w/2+unit*.25*scale,y-h/2+unit*.35*scale),(x,y+unit*.24*scale),
               (x+w/2-unit*.25*scale,y-h/2+unit*.35*scale)],fill=accent,width=max(2,int(unit*.16*scale)))
    return (w,h)


def scene_foundbeam_flow(c, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """Dual-desktop storyboard, geometry and motion all rendered, no external media."""
    variant=p.get("variant","split")
    if variant not in VARIANTS:
        raise ValueError(f"Unknown Foundbeam acquisition-story variant: {variant}")
    W,H=c.W,c.H
    u=c.u
    minx=c.margin
    body=font(c.style.body,max(12,int(u*2.5)))
    strong=font(c.style.display,max(16,int(u*3.4)))
    headline=font(c.style.display,max(18,int(u*5.4)))
    ink=rgb(c.style.ink)
    muted=rgb(c.style.muted)
    accent=rgb(c.style.accent)
    secondary=(95,170,181)
    for k in range(max(1,int(dur*24))):
        t=k/24
        progress=min(1,t/max(.5,dur*.72))
        reveal=progress*progress*(3-2*progress)
        img,d=c.canvas(t)
        c.badge(d)
        headings={
            "split":"TWO WAYS TO INVITE",
            "folder":"SEND A SHARED FOLDER",
            "referral":"INVITE WITH A REWARD",
            "meter":"STORAGE FOR BOTH",
            "milestone":"REPORTED GROWTH",
            "signup":"DIFFERENT STARTING POINTS",
            "return":"TWO REASONS TO CLICK",
        }
        title=str(p.get("title") or headings[variant])
        _label(d,minx,H*.155,title,headline,ink,W-2*minx)
        if variant=="signup":
            # Company-reported share of DAILY SIGNUPS in 2010, not registered
            # users, conversions of invites, or all-time acquisition totals.
            # The 45% "other" category is derived remainder, not a new source.
            breakdown = (("DIRECT REFERRAL",35,accent),
                         ("SHARED FOLDERS + OTHER VIRAL",20,secondary),
                         ("OTHER (REMAINDER)",45,muted))
            small=font(c.style.body,max(11,int(u*2.6)))
            for j,(label,amount,color) in enumerate(breakdown):
                left=W*.13
                y=H*(.35+j*.155)
                _label(d,left,y,label,small,ink,W*.54)
                _label(d,W*.80,y,str(amount)+'%',strong,color,W*.15)
                full=W*.64
                _rounded(d,(left,y+small.size*1.55,left+full,y+small.size*1.55+u*1.2),
                         (65,65,75,255),u*.55)
                _rounded(d,(left,y+small.size*1.55,left+full*amount/100*reveal,
                            y+small.size*1.55+u*1.2),(*color,255),u*.5)
            _label(d,minx,H*.25,"Company-reported 2010 daily signup mix",
                   body,muted,W-2*minx)
        elif variant=="milestone":
            center=W*.5
            yy=H*.53
            xlo=W*.14
            xhi=W*.86
            d.line((xlo,yy,xhi,yy),fill=(*muted,200),width=max(2,int(u*.4)))
            xend=xlo+(xhi-xlo)*reveal
            d.line((xlo,yy,xend,yy),fill=accent,width=max(3,int(u*.63)))
            labels=(("SEP 2008","100,000","registered accounts"),("JAN 2010","4 MILLION","registered accounts"))
            for i,(date,number,unit_label) in enumerate(labels):
                x=(xlo if i==0 else xhi)
                d.ellipse((x-u*1.4,yy-u*1.4,x+u*1.4,yy+u*1.4),fill=accent if reveal>(i*.40) else muted)
                f=font(c.style.display,max(18,int(u*5)))
                xx=x-u*3 if i==0 else x-W*.23
                y=yy-u*15 if i==0 else yy+u*6
                _label(d,xx,y,number,f,ink,W*.35)
                _label(d,xx,y+u*7,date,strong,accent,W*.35)
                _label(d,xx,y+u*11,unit_label,body,muted,W*.35)
        else:
            margin=W*.095
            gap=W*.045
            left_w=(W-2*margin-gap)/2
            row_top=H*.305 if not c.vertical else H*.32
            row_bottom=H*.735 if not c.vertical else H*.67
            left=(margin,row_top,margin+left_w,row_bottom)
            right=(margin+left_w+gap,row_top,W-margin,row_bottom)
            _screen(d,left,title="PROJECT FILE",owner="ALEX",unit=u,f_body=body,f_head=strong,
                    ink=ink,muted=muted,accent=accent,secondary=secondary)
            _screen(d,right,title="PROJECT FILE",owner="SAM",unit=u,f_body=body,f_head=strong,
                    ink=ink,muted=muted,accent=accent,secondary=(147,110,183))
            xstart=left[0]+left_w*.84
            xfinish=right[0]+left_w*.16
            yline=row_top+(row_bottom-row_top)*.40
            d.line((xstart,yline,xfinish,yline),fill=(*muted,150),width=max(2,int(u*.3)))
            xmove=xstart+(xfinish-xstart)*reveal
            message=variant in {"referral","meter","return"}
            if message:
                _letter(d,xmove,yline,u,ink,accent,scale=1.0+0.14*math.sin(t*2))
            else:
                _rounded(d,(xmove-u*2.0,yline-u*1.3,xmove+u*2.0,yline+u*1.3),secondary,u*.4)
            if variant in {"meter","referral"}:
                for box,col in ((left,accent),(right,(158,197,143))):
                    bar_x=box[0]+u*1.8
                    bar_y=box[3]-u*5.6
                    bar_w=max(u*3,box[2]-box[0]-u*3.6)
                    d.line((bar_x,bar_y,bar_x+bar_w,bar_y),fill=muted,width=max(2,int(u*.9)))
                    d.line((bar_x,bar_y,bar_x+bar_w*(.28+.56*reveal),bar_y),fill=col,width=max(2,int(u*.9)))
            bottom_label={"split":"A FOLDER  /  A REFERRAL","folder":"SHARE = USE THE PRODUCT",
                          "referral":"REFERRAL = AN INVITATION TO JOIN",
                          "meter":"ILLUSTRATIVE STORAGE CHANGE","signup":"DIFFERENT ACTIONS. DIFFERENT METRICS.",
                          "return":"FOLDER ACCESS  /  REWARDED JOIN"}[variant]
            _label(d,minx,H*.75,bottom_label,strong,accent,W-2*minx)
        # Bottom 16% is reserved for the actual narration captions. Avoid the
        # old double-deck collision between fine-print and active subtitles.
        _label(d,W*.72,H*.09,"ILLUSTRATED",body,muted,W*.19)
        yield img.convert('RGB')
