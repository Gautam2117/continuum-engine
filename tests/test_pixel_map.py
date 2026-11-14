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
