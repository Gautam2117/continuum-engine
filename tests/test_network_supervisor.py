"""Production supervisor contract. No APIs, uploads or actual media rendering."""
from __future__ import annotations

import datetime as dt
import json
import pathlib

import pytest

from scripts import network_supervisor as sup

DAY = dt.date(2026, 11, 14)


def test_exact_daily_48_individual_contracts():
    for offset in range(21):
        date = DAY+dt.timedelta(days=offset)
        plan = sup.target(date)
        assert len(plan) == 48
        assert sum(sum(v.values()) for v in plan.values()) == 50
        assert sum(plan['Counterfactual Atlas'].values()) == 3
        assert all(sum(v.values()) == 1 for name,v in plan.items() if name != 'Counterfactual Atlas')
        assert not any('felix' in x.lower() or 'gotz' in x.lower() for x in plan)


def test_empty_spool_never_claims_made_videos(tmp_path):
    snap = sup.snapshot(tmp_path/'specs', tmp_path/'worker.sqlite3', today=DAY, days=3)
    assert snap['channels']==48
    assert snap['requiredEpisodes']==150
    assert snap['validSpecs']==0 and snap['missingSpecs']==150
    assert len(snap['channelsDetail'])==48
    assert snap['worker']['verifiedEpisodes']==0
    assert snap['publishing']==sup.RELEASE_STATE
    assert not snap['fullyAutonomous'] and not snap['offMacHostProvisioned']


def test_invalid_spec_does_not_satisfy_channel_quota(tmp_path):
    root = tmp_path/'specs'/DAY.isoformat()
    root.mkdir(parents=True)
    (root/'atlas-s1.json').write_text(json.dumps({
        'id':f'{DAY}-atlas-s1', 'channel':'Counterfactual Atlas',
        'format':'short', 'title':'An interesting question', 'scenes':[],
    }))
    snap=sup.snapshot(tmp_path/'specs',tmp_path/'state.db',today=DAY,days=1)
    assert snap['validSpecs']==0 and snap['invalidSpecCount']==1
    assert snap['missingSpecs']==50
    assert snap['invalidSpecs'][0]['file'].endswith('atlas-s1.json')


def test_atomic_report_overwrites_only_complete_documents(tmp_path):
    path=tmp_path/'nested'/'heartbeat.json'
    sup.write_atomic(path,{'first':1})
    assert json.loads(path.read_text())=={'first':1}
    sup.write_atomic(path,{'second':2})
    assert json.loads(path.read_text())=={'second':2}
    assert not list(path.parent.glob('.supervisor-*'))
    assert path.stat().st_mode & 0o077 == 0


def test_supervisor_lock_blocks_second_live_instance(tmp_path):
    with sup.singleton(tmp_path):
        with pytest.raises(RuntimeError,match='already running'):
            with sup.singleton(tmp_path):
                pass


def test_model_use_requires_explicit_spend_safe_gate(monkeypatch):
    monkeypatch.delenv('CONTINUUM_ZERO_COST_LLM_CONFIRMED',raising=False)
    assert sup.allowed_planner()[0] is False
    monkeypatch.setenv('CONTINUUM_ZERO_COST_LLM_CONFIRMED','no')
    assert sup.allowed_planner()[0] is False


def test_report_only_cycle_is_idempotent_and_never_publishes(monkeypatch,tmp_path):
    args=sup.parser().parse_args(['cycle','--state',str(tmp_path/'private'),
        '--db',str(tmp_path/'db.sqlite3'),'--specs',str(tmp_path/'spool'),
        '--reviews',str(tmp_path/'reviews'),'--days','2','--plan'])
    monkeypatch.setattr(sup,'allowed_planner',lambda: (False,'no zero-cost provider'))
    r=sup.cycle(args)
    assert r['requiredEpisodes']==100
    assert r['validSpecs']==0
    assert r['steps']['plan']['status']=='not-run'
    assert json.loads((tmp_path/'private'/'latest.json').read_text())['missingSpecs']==100
    r2=sup.cycle(args)
    assert r2['requiredEpisodes']==100
    assert not list((tmp_path/'reviews').rglob('*.mp4')) if (tmp_path/'reviews').exists() else True


def test_missing_dependency_skips_render_without_fake_video(monkeypatch,tmp_path):
    args=sup.parser().parse_args(['cycle','--state',str(tmp_path/'private'),
        '--db',str(tmp_path/'db.sqlite3'),'--specs',str(tmp_path/'spool'),
        '--reviews',str(tmp_path/'reviews'),'--days','1','--render'])
    from scripts import worker
    monkeypatch.setattr(worker,'preflight',lambda *a,**kw: {'ready':False,'modules':{'PIL':False}})
    result=sup.cycle(args)
    assert result['steps']['render']['status']=='not-run'
    assert result['worker']['verifiedEpisodes']==0
    assert result['publishing']!= 'PUBLIC'


def test_invalid_cli_limits_fail_closed():
    with pytest.raises(SystemExit):
        sup.main(['status','--days','0'])
    with pytest.raises(SystemExit):
        sup.main(['status','--plan'])


def test_disk_reserve_blocks_render_without_deleting_prior_media(monkeypatch,tmp_path):
    from scripts import worker
    monkeypatch.setattr(worker,'preflight',lambda *a,**kw: {'ready':True})
    monkeypatch.setattr(sup.shutil,'disk_usage',lambda path: type('Disk',(),{'free':2*1024**3})())
    args=sup.parser().parse_args(['cycle','--state',str(tmp_path/'private'),
        '--db',str(tmp_path/'db.sqlite3'),'--specs',str(tmp_path/'spool'),
        '--reviews',str(tmp_path/'reviews'),'--days','1','--render'])
    # Preflight ordinarily creates the review directory itself.
    (tmp_path/'reviews').mkdir()
    result=sup.cycle(args)
    assert result['steps']['render']['status']=='not-run'
    assert result['steps']['render']['reason']=='disk space safety reserve'
    assert result['steps']['render']['requiredGiB']==20


def test_structurally_valid_unreviewed_autopilot_spec_does_not_count_as_render_ready(tmp_path):
    from scripts import network_supervisor as module
    src=pathlib.Path(__file__).resolve().parents[1] / 'specs' / '2026-11-14' / '10sec-s1.json'
    folder=tmp_path/'specs'/'2026-11-14'
    folder.mkdir(parents=True)
    (folder/src.name).write_text(src.read_text())
    report=module.snapshot(tmp_path/'specs',tmp_path/'no.db',today=DAY,days=1)
    assert report['validSpecs']==1
    assert report['renderEligibleSpecs']==0
    assert report['editorialHoldCount']==1
    assert report['missingSpecs']==49
    assert report['missingRenderReady']==50
    assert 'editorial score' in report['editorialHolds'][0]['reason']


def test_archive_needs_an_explicit_trusted_mount(monkeypatch,tmp_path):
    args=sup.parser().parse_args(['cycle','--state',str(tmp_path/'private'),
        '--db',str(tmp_path/'db.sqlite3'),'--specs',str(tmp_path/'spool'),
        '--reviews',str(tmp_path/'reviews'),'--days','1'])
    monkeypatch.setenv('CONTINUUM_ARCHIVE_ROOT',str(tmp_path/'otherdisk'))
    monkeypatch.delenv('CONTINUUM_ARCHIVE_MOUNT_ENCRYPTED',raising=False)
    x=sup.cycle(args)
    assert x['steps']['archive']['status']=='not-run'
    assert x['steps']['archive']['reason']=='trusted encrypted mount not confirmed'
    assert not (tmp_path/'otherdisk').exists()
