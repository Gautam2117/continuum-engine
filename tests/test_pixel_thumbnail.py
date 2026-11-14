"""Thumbnail is original, readable, and tied to a real rendered stage."""
import pytest
from PIL import Image, ImageDraw

from engine.pixel_thumbnail import pixel_poster
from engine.styles import style_for
from scripts.verify_review import verify


def test_original_poster_uses_story_frame_not_generic_logo(tmp_path):
    source=Image.new('RGB',(540,870),(29,115,83))
    d=ImageDraw.Draw(source)
    d.rectangle((90,330,210,670),fill=(241,120,58))
    d.rectangle((80,250,215,375),fill=(187,146,105))
    d.rectangle((240,490,500,525),fill=(243,190,67))
    spec={'id':'2026-11-17-pixel-s1','channel':'Pixel Fables',
          'format':'short','title':'The Road That Appeared','description':'Original fable',
          'scenes':[]}
    target=tmp_path/'poster.jpg'
    pixel_poster(spec,style_for('Pixel Fables'),target,source)
    with Image.open(target) as output:
        assert output.size==(1280,720)
        assert output.format=='JPEG'
        assert output.getpixel((100,300))!=output.getpixel((880,300))
    assert target.stat().st_size>15_000
    assert target.stat().st_size<2_000_000


def test_poster_rejects_missing_or_inadequate_art(tmp_path):
    with pytest.raises(ValueError,match='real rendered source'):
        pixel_poster({},style_for('Pixel Fables'),tmp_path/'no.jpg',None)
    with pytest.raises(ValueError,match='real rendered source'):
        pixel_poster({},style_for('Pixel Fables'),tmp_path/'no.jpg',Image.new('RGB',(8,8)))
