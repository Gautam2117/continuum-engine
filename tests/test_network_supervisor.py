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
        assert sum(sum(v.values()) for v in plan.values()) == 47 + sum(plan['Counterfactual Atlas'].values())
        assert sum(plan['Counterfactual Atlas'].values()) == 3 + int(date.weekday() in (0,2,5))
        assert all(sum(v.values()) == 1 for name,v in plan.items() if name != 'Counterfactual Atlas')
        assert not any('felix' in x.lower() or 'gotz' in x.lower() for x in plan)


def test_empty_spool_never_claims_made_videos(tmp_path):
    snap = sup.snapshot(tmp_path/'specs', tmp_path/'worker.sqlite3', today=DAY, days=3)
    assert snap['channels']==48
    assert snap['requiredEpisodes']==152
    assert snap['validSpecs']==0 and snap['missingSpecs']==152
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
    assert snap['missingSpecs']==51
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
    assert r['requiredEpisodes']==101
    assert r['validSpecs']==0
    assert r['steps']['plan']['status']=='not-run'
    assert json.loads((tmp_path/'private'/'latest.json').read_text())['missingSpecs']==101
    r2=sup.cycle(args)
    assert r2['requiredEpisodes']==101
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
    assert report['missingSpecs']==50
    assert report['missingRenderReady']==51
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


def test_cycle_prioritizes_private_render_before_planning(monkeypatch, tmp_path):
    from scripts import worker
    calls = []
    def preflight(*args, **kwargs):
        calls.append('preflight')
        assert kwargs.get('require_blender') is False
        return {'ready': True}
    def command(argv, **kwargs):
        calls.append(pathlib.Path(argv[1]).name)
        return {'exit': 0, 'elapsedSec': 0.0}
    monkeypatch.setattr(worker, 'preflight', preflight)
    monkeypatch.setattr(sup, 'run_command', command)
    monkeypatch.setattr(sup, 'allowed_planner', lambda: (True, 'model ready'))
    args = sup.parser().parse_args(['cycle', '--state', str(tmp_path/'state'),
        '--db', str(tmp_path/'worker.sqlite3'), '--specs', str(tmp_path/'specs'),
        '--reviews', str(tmp_path/'reviews'), '--days', '1', '--plan', '--render',
        '--require-blender', '--min-free-gib', '2'])
    (tmp_path/'reviews').mkdir()
    result = sup.cycle(args)
    assert calls == ['preflight', 'worker.py', 'autopilot.py']
    assert result['steps']['render']['exit'] == 0
    assert result['steps']['plan']['exit'] == 0


def test_blender_probe_only_when_next_eligible_job_is_3d(monkeypatch, tmp_path):
    from scripts import worker
    date = sup.now_utc()
    root = tmp_path/'specs'/'2026-11-16'
    root.mkdir(parents=True)
    monkeypatch.setattr(worker, 'SPEC_ROOT', tmp_path/'specs')
    db_path = tmp_path/'worker.sqlite3'
    with worker.connection(db_path) as db:
        for i, scene_type in enumerate(('say','b3d')):
            filename = f'atlas-s{i+1}'
            path = root/f'{filename}.json'
            path.write_text(json.dumps({'id': f'2026-11-16-{filename}',
                'channel': 'Counterfactual Atlas', 'format': 'short',
                'scenes': [{'say': 'Example', 'show': {'type': scene_type}}]}))
            db.execute("INSERT INTO jobs (job_key,spec_id,spec_path,spec_sha256,channel,format,state,eligible_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (filename, f'2026-11-16-{filename}', str(path), 'a'*64,
                 'Counterfactual Atlas', 'short', 'queued',
                 (date-dt.timedelta(minutes=10-i)).isoformat(), date.isoformat()))
        db.commit()
    assert sup.next_queued_job_needs_blender(db_path) is False
    with worker.connection(db_path) as db:
        db.execute("UPDATE jobs SET state='verified' WHERE job_key='atlas-s1'")
        db.commit()
    assert sup.next_queued_job_needs_blender(db_path) is True
    with worker.connection(db_path) as db:
        db.execute("UPDATE jobs SET eligible_at=? WHERE job_key='atlas-s2'",
                   ((date+dt.timedelta(hours=2)).isoformat(),))
        db.commit()
    assert sup.next_queued_job_needs_blender(db_path) is False


def test_mac_prevents_idle_sleep_only_while_a_work_step_runs(monkeypatch):
    command=['/some/bin/python','script.py','--no-public-upload']
    monkeypatch.setattr(sup.sys,'platform','darwin')
    monkeypatch.setattr(sup.shutil,'which',lambda name: '/usr/bin/caffeinate' if name=='caffeinate' else None)
    assert sup.awake_argv(command)==['/usr/bin/caffeinate','-i',*command]
    assert command==['/some/bin/python','script.py','--no-public-upload']
    monkeypatch.setattr(sup.sys,'platform','linux')
    assert sup.awake_argv(command)==command
    monkeypatch.setattr(sup.sys,'platform','darwin')
    monkeypatch.setattr(sup.shutil,'which',lambda name: None)
    assert sup.awake_argv(command)==command


def test_atlas_focus_file_only_routes_work_not_48_channel_contract(monkeypatch,tmp_path):
    from scripts import worker
    root=tmp_path/'state'
    root.mkdir()
    (root/'focus_channel.txt').write_text('Counterfactual Atlas\n')
    seen=[]
    monkeypatch.setattr(worker,'preflight',lambda *a,**kw:{'ready':True})
    monkeypatch.setattr(sup,'allowed_planner',lambda:(True,'offline local provider'))
    def call(argv,**kw):
        seen.append(list(argv))
        return {'exit':0,'elapsedSec':0.0}
    monkeypatch.setattr(sup,'run_command',call)
    args=sup.parser().parse_args(['cycle','--state',str(root), '--db',str(tmp_path/'worker.sqlite3'),
       '--specs',str(tmp_path/'specs'),'--reviews',str(tmp_path/'reviews'),
       '--days','2','--plan','--render','--min-free-gib','2'])
    (tmp_path/'reviews').mkdir()
    report=sup.cycle(args)
    assert report['productionFocus']=='Counterfactual Atlas'
    assert report['channels']==48 and report['requiredEpisodes']==101
    assert len(seen)==2
    assert seen[0][-2:]==['--channel','Counterfactual Atlas']
    assert seen[1][-2:]==['--only','Counterfactual Atlas']
    assert 'scripts/worker.py' in seen[0][1]
    assert 'scripts/autopilot.py' in seen[1][1]


def test_unknown_focus_file_fails_closed_without_model_calls(monkeypatch,tmp_path):
    state=tmp_path/'state';state.mkdir()
    (state/'focus_channel.txt').write_text('Wrong Channel\n')
    monkeypatch.setattr(sup,'run_command',lambda *_a,**_kw:pytest.fail('Cannot execute unknown channel'))
    args=sup.parser().parse_args(['cycle','--state',str(state),'--db',str(tmp_path/'db.sqlite3')])
    with pytest.raises(ValueError,match='Unknown focus channel'):
        sup.cycle(args)
