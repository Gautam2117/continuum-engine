"""Original Foundbeam acquisition storyboard renders, without Dropbox art."""
from itertools import islice
from PIL import Image

from engine.foundbeam import VARIANTS, scene_foundbeam_flow
from engine.scenes import Backdrop, Ctx
from engine.spec_check import problems
from engine.styles import STYLES


def test_all_seven_original_desktop_variants_animate_in_both_aspects():
    style = STYLES['foundbeam']
    for dims in ((480, 270), (300, 460)):
        c = Ctx(style, *dims, Backdrop(style, *dims, seed=8), 'Foundbeam')
        for variant in VARIANTS:
            frames = list(islice(scene_foundbeam_flow(c, 0.6, {'variant':variant}, []), 12))
            assert len(frames) == 12
            assert all(im.size==dims and im.mode=='RGB' for im in frames)
            assert frames[0].tobytes()!=frames[-1].tobytes()


def test_foundbeam_illustration_cannot_be_coopted_by_another_channel():
    s = {'id':'2026-11-16-oddly-s1','channel':'Oddly Proven','format':'short',
         'title':'A test', 'description':'A test narration',
         'scenes':[{'say':'Test','show':{'type':'foundbeam_flow','variant':'folder'}}]}
    assert any('invalid Foundbeam acquisition' in e for e in problems(s, '2026-11-16'))
    s['channel']='Foundbeam'
    assert not any('invalid Foundbeam acquisition' in e for e in problems(s, '2026-11-16'))
    s['scenes'][0]['show']['variant']='unknown'
    assert any('invalid Foundbeam acquisition' in e for e in problems(s, '2026-11-16'))


def test_foundbeam_does_not_receive_generic_emoji_host_overlay():
    from engine.render import NO_MASCOT, NO_STICKERS
    assert 'foundbeam' in NO_MASCOT
    assert 'foundbeam' in NO_STICKERS
    assert 'atlas' in NO_MASCOT
