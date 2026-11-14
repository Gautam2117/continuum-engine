"""Reject unsourced Foundbeam claims and preserve the authored text/visuals."""
from __future__ import annotations
from collections import Counter
import json

from scripts.build_foundbeam_case import SOURCE, OUT, SECTIONS, sections_from_markdown, build, sentence_groups
from engine.spec_check import problems


def test_all_source_prose_is_preserved_without_model_rewrite():
    sections=sections_from_markdown()
    assert set(sections)==set(SECTIONS)
    source=' '.join(p for paragraphs in sections.values() for p in paragraphs)
    spec=build()
    actual=' '.join(s['say'] for s in spec['scenes'])
    assert source.split()==actual.split()
    assert 1180<=len(actual.split())<=1500
    assert len(spec['scenes'])>=45
    assert problems(spec,'2026-11-17',strict=True)==[]


def test_visuals_use_independent_storyboard_and_verified_numbers():
    spec=build()
    cnt=Counter(s['show']['type'] for s in spec['scenes'])
    assert cnt['foundbeam_flow']>=35
    assert cnt['number']>=1
    assert spec['scenes'][0]['show']['type']=='foundbeam_flow'
    assert spec['scenes'][0]['show']['variant']=='split'
    assert spec['scenes'][-1]['show']['type']=='end'
    from engine.foundbeam import VARIANTS
    assert all(s['show'].get('variant') in VARIANTS for s in spec['scenes'] if s['show']['type']=='foundbeam_flow')
    figures=spec['description']
    assert '2.8 million' in figures and '35%' in figures and '20%' in figures
    assert '100,000' in figures and 'four million' in figures
    assert spec['meta']['reviewStatus']=='EDITORIAL_HOLD_NOT_APPROVED'
    assert '500 MB' not in ' '.join(s['say'] for s in spec['scenes'])
    assert 'first 100,000 users solely' in figures
    assert 'actual Dropbox interface' not in figures.lower()


def test_published_spec_bytes_are_reproducible():
    generated=build()
    saved=json.loads(OUT.read_text())
    assert saved==generated


def test_sentence_splitting_does_not_invent_or_lose_words():
    paragraph='A user shares a folder. Then someone receives an invitation. The rewards apply to both people.'
    groups=sentence_groups(paragraph,max_words=10)
    assert ' '.join(groups)==paragraph
    assert len(groups)>=2
