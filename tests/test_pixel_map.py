from itertools import islice
from engine.scenes import Ctx,Backdrop,SCENES
from engine.styles import style_for
from engine.spec_check import problems
from engine.render import NO_MASCOT,NO_STICKERS


def test_unique_pixel_interludes_render_actually_moving_character_in_both_ratios():
    s=style_for('Pixel Fables')
    for dimensions in ((300,530),(520,300)):
        ctx=Ctx(s,*dimensions,Backdrop(s,*dimensions,seed=7),'Pixel Fables')
        for phase in ('lost','choice'):
            seq=list(islice(SCENES['pixel_map'](ctx,0.5,{'phase':phase},[]),12))
            assert len(seq)==12
            assert all(frame.size==dimensions and frame.mode=='RGB' for frame in seq)
            assert seq[0].tobytes()!=seq[-1].tobytes()
    assert 'pixel' in NO_MASCOT and 'pixel' in NO_STICKERS


def test_pixel_map_cannot_be_misused_by_unrelated_channel():
    s={'id':'2026-11-17-test','channel':'Foundbeam','format':'short','title':'test','description':'something',
       'scenes':[{'say':'One','show':{'type':'pixel_map','phase':'choice'}}]}
    assert any('invalid Pixel Fables' in x for x in problems(s))
    s['channel']='Pixel Fables'
    assert not any('invalid Pixel Fables' in x for x in problems(s))
    s['scenes'][0]['show']['phase']='not-a-phase'
    assert any('invalid Pixel Fables' in x for x in problems(s))


def test_pixel_world_uses_screen_filling_view_but_keeps_caption_position_safe():
    from engine.stage import Layout
    main=Layout(1080,1920,'short',no_host=True,world_focus=True)
    legacy=Layout(1080,1920,'short',no_host=True)
    assert main.view_h > legacy.view_h + 200
    assert 1500 <= main.cap_y < main.view_h - 100
    assert main.view_h <= 1820
    assert Layout(1920,1080,'long',world_focus=True).view_h==1080


def test_pixel_story_has_visual_tell_and_three_separate_act_states():
    import json
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'specs/2026-11-17/pixel-s1.json'
    spec=json.loads(path.read_text())
    kinds=[s['show']['type'] for s in spec['scenes']]
    assert kinds==['b3d','pixel_map','b3d','pixel_map','b3d','end']
    assert [s['show']['params']['act'] for s in spec['scenes'] if s['show']['type']=='b3d']==['warning','bridge','arrival']
    assert spec['meta']['reviewStatus']=='TECHNICAL_QA_ONLY_NOT_APPROVED'
    assert 'NO ROAD AHEAD' in spec['scenes'][0]['say']
    assert 'land rose' in spec['scenes'][2]['say']
    assert 'recording' in spec['scenes'][5]['say']
    assert problems(spec,'2026-11-17',strict=True)==[]


def test_unrecognized_voxel_story_is_rejected_before_rendering():
    source={'id':'2026-11-17-fable','channel':'Pixel Fables','format':'short',
            'title':'Original fable','description':'Fictional fable story',
            'scenes':[{'say':'Walk','show':{'type':'b3d','scene':'voxel','params':{'act':'unknown'},
                                      'fallback':{'type':'title','text':'Failure'}}}]}
    assert any('unsupported voxel narrative act' in x for x in problems(source))
    source['scenes'][0]['show']['params']['act']='bridge'
    assert not any('unsupported voxel narrative act' in x for x in problems(source))
    source['channel']='Foundbeam'
    assert any('Pixel Fables-specific' in x for x in problems(source))


def test_pixel_map_type_and_caption_bands_have_actual_clearance():
    from PIL import ImageDraw, Image
    from engine.fonts import font
    from engine.stage import Layout
    layout=Layout(1080,1920,'short',no_host=True,world_focus=True)
    H=layout.view_h
    s=style_for('Pixel Fables')
    body=font(s.body,max(14,int(min(1080,H)/100*2.4)))
    ink=ImageDraw.Draw(Image.new('RGB',(1080,H)))
    # In portrait the header, grid, closing statement and caption are separate
    # bands. The previous render allowed the grid to cover FABLE 01 and the
    # narrator's captions to paint across ROAD NOT FOUND.
    subtitle_height=ink.textbbox((0,0),'FABLE 01 / MAP SIGNAL: LOST',font=body)[3]
    detail_height=ink.textbbox((0,0),'AN ORIGINAL FICTIONAL PIXEL WORLD',font=body)[3]
    assert H*.215+subtitle_height+10 < H*.24
    assert H*(.24+.47)+25 < H*.76
    assert H*.812+detail_height+50 < layout.cap_y-50


import os
import pytest


@pytest.mark.skipif(os.environ.get('B3D_PIXEL_TEST') != '1', reason='set B3D_PIXEL_TEST=1 for native Blender visual smoke')
def test_real_blender_renders_three_distinct_fable_story_stages(tmp_path, monkeypatch):
    from engine import b3d
    monkeypatch.delenv('B3D_OFF', raising=False)
    monkeypatch.setenv('B3D_CACHE', str(tmp_path))
    b3d.blender_runner.cache_clear()
    assert b3d.available(), 'Native Blender rendering required for Pixel Fables'
    pal = {'bg': '#081321', 'panel': '#18283f', 'ink': '#e8f3ff', 'accent': '#f9bb41'}
    snapshots=[]
    for act in ('warning','bridge','arrival'):
        result=b3d.render_clip('voxel', {'seed': 19, 'act': act, 'hero': '#ec743c'},
                               5, (360,580), pal)
        assert result and len(result)==5, f'Unrendered voxel stage: {act}'
        snapshots.append(b3d.load(result[-1],(360,580)).tobytes())
        evidence=b3d.anchors(result)
        if act=='warning':
            assert any(x['anchor']=='warning_sign' for x in evidence['labels'])
        if act=='arrival':
            assert any(x['anchor']=='goal' for x in evidence['labels'])
    assert len(set(snapshots))==3
