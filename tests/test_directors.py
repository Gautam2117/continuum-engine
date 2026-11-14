"""The 48 director contracts must be complete and mechanically applied."""
import datetime as dt
import json

import numpy as np
from PIL import Image, ImageDraw
import pytest

from autopilot import daily
from autopilot.directors import DIRECTORS, VERSION, director_for, verify_directors
from autopilot.playbooks import PLAYBOOKS
from engine.scenes import Backdrop
from engine.spec_check import problems
from engine.stage import Captions, Layout, Scene
from engine.styles import STYLES


def test_all_48_are_independent_and_felix_gotz_are_not_automated():
    assert len(PLAYBOOKS) == 48
    verify_directors(set(PLAYBOOKS))
    assert 'Felix' not in DIRECTORS and 'GOTZ' not in DIRECTORS
    assert len({d.visual_world for d in DIRECTORS.values()}) == 48
    assert len({d.shot_sequence for d in DIRECTORS.values()}) == 48
    assert len({d.fingerprint() for d in DIRECTORS.values()}) == 48


def test_original_channel_script_is_the_only_possible_exemplar(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, 'SPECS', tmp_path)
    folder = tmp_path / '2026-11-16'
    folder.mkdir()
    (folder / 'other.json').write_text(json.dumps({
        'id': '2026-11-16-foundbeam-s1', 'channel': 'Foundbeam', 'format': 'short',
        'title': 'Dropbox growth story', 'thumb': 'Case study',
        'scenes': [{'say': 'Example', 'show': {'type': 'title', 'text': 'Founder'}}]}))
    assert daily.exemplar('Counterfactual Atlas', 'short') == ''
    assert 'Dropbox growth story' in daily.exemplar('Foundbeam', 'short')
    assert 'Dropbox' not in daily.Planner._system(daily.Planner.__new__(daily.Planner), 'Counterfactual Atlas')


def test_different_channel_directors_are_in_the_real_planner_prompt():
    planner = daily.Planner.__new__(daily.Planner)
    atlas = planner._system('Counterfactual Atlas')
    pixel = planner._system('Pixel Fables')
    assert 'precision observatory' in atlas
    assert 'isometric voxel-storybook' in pixel
    assert 'isometric voxel-storybook' not in atlas
    assert 'precision observatory' not in pixel


def test_camera_modes_change_rendered_frames_not_just_text():
    style = STYLES['atlas']
    canvas = Image.new('RGB', (260, 400))
    d = ImageDraw.Draw(canvas)
    for i in range(0, 260, 10):
        d.rectangle((i, 0, i + 9, 399), fill=((i*7)%255, (i*3)%255, 50))
    for y in range(0, 400, 17):
        d.line((0, y, 259, y), fill=(255, (y*3)%255, 120), width=2)
    layout = Layout(260, 400, 'long')
    audio = np.zeros(24000, dtype=np.float32)
    renders = {}
    for mode in ('hold', 'snap', 'float', 'push', 'pull', 'drift_left', 'drift_right', 'orbit', 'tilt', 'parallax'):
        scene = Scene(layout, style, 'atlas', 'Counterfactual Atlas', 'number',
                      'Testing camera styles', 2.0, audio, [],
                      {'host': False, 'captions': False, 'camera': mode}, False)
        img = scene.camera(canvas, 0.7)
        assert img.size == canvas.size
        renders[mode] = img.tobytes()
    assert len(set(renders.values())) >= 8
    assert renders['hold'] != renders['push']
    assert renders['drift_left'] != renders['drift_right']


def test_caption_treatments_are_visually_distinct_and_fit():
    style = STYLES['atlas']
    layout = Layout(1080, 1920, 'short', no_host=True)
    images = []
    words = 'Tidal force is not the same as water height'.split()
    for mode in ('minimal', 'impact', 'ledger', 'documentary', 'typewriter', 'soft'):
        cap = Captions(layout, style, words, .18, 3.5, mode=mode)
        picture = Image.new('RGBA', (1080, 1920), (12, 12, 20, 255))
        cap.draw(picture, .75)
        images.append(picture.tobytes())
        assert all(18 <= size <= 160 for _, _, size in cap.chunks)
    assert len(set(images)) == len(images)


def test_modified_or_misrouted_creative_fingerprint_is_rejected():
    director = director_for('Foundbeam')
    spec = {'id':'2026-11-16-foundbeam-s1', 'channel':'Foundbeam', 'format':'short',
            'title':'A real mechanism', 'description':'Source-led explanation',
            'scenes':[{'say':'Example line','show':{'type':'title','text':'A hook'}}],
            'meta': {'creativeDirector': {'id':'Counterfactual Atlas', 'fingerprint':director.fingerprint(),
                                         'version':VERSION, 'camera':director.camera, 'captions':director.captions}}}
    assert any('creative director identity' in x for x in problems(spec, '2026-11-16'))
    spec['meta']['creativeDirector']['id'] = 'Foundbeam'
    assert not any('creative director identity' in x for x in problems(spec, '2026-11-16'))


def test_exported_registry_document_matches_the_live_directors():
    from pathlib import Path
    from scripts.export_directors import render
    root = Path(__file__).resolve().parents[1]
    assert (root / 'docs' / 'CHANNEL_DIRECTORS.md').read_text() == render()
