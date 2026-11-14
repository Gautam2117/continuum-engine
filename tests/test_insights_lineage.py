"""Learning must follow verified platform-to-script lineage, not clickbait titles."""
from __future__ import annotations
import datetime as dt
import pytest
from autopilot import insights

NOW = dt.datetime.now(dt.timezone.utc)
OLD = (NOW - dt.timedelta(days=8)).isoformat()
RECENT = (NOW - dt.timedelta(hours=4)).isoformat()


def seed(tmp_path, monkeypatch, feedback, ledger):
    monkeypatch.setattr(insights, 'STATE', tmp_path)
    insights.save('feedback.json', {'channels': feedback})
    insights.save('ledger.json', ledger)


def row(video_id, spec_id, *, title='Repeatable viral title', published=OLD, views=600, fmt='short'):
    return {'id':video_id,'engineSpecId':spec_id,'title':title,'publishedAt':published,
            'format':fmt,'views':views,'avgPct':72,'subsGained':6,'minutes':200}


def ledger(spec_id, title='Original measured idea'):
    return {'id':spec_id,'channel':'Counterfactual Atlas','format':'short','title':title,
            'axis':'astronomy','slot':'14:00'}


def test_title_edits_and_reused_titles_cannot_misattribute_performance(tmp_path, monkeypatch):
    a = '2026-11-15-atlas-s1'
    b = '2026-11-15-atlas-s2'
    c = '2026-11-15-atlas-s3'
    seed(tmp_path, monkeypatch, [{'title':'Counterfactual Atlas','videos':[
        row('ABCDEFGHIJK',a,title='Renamed after upload'),
        row('KJIHGFEDCBA',None,title='Exact same title',views=999999),
        row('BBBBBBBBBBB',b,title='Exact same title')]}],
        [ledger(a,'Exact same title'),ledger(b,'Exact same title'),ledger(c,'Exact same title')])
    out = insights.joined('Counterfactual Atlas')
    assert {r['id'] for r in out} == {a,b}
    assert {r['youtubeVideoId'] for r in out} == {'ABCDEFGHIJK','BBBBBBBBBBB'}
    assert not any(r['views']==999999 for r in out)


def test_duplicate_reuploads_are_excluded_until_reviewed(tmp_path, monkeypatch):
    sid = '2026-11-15-atlas-s1'
    seed(tmp_path, monkeypatch, [{'title':'Counterfactual Atlas','videos':[
        row('AAAAAAAAAAA',sid),row('BBBBBBBBBBB',sid,views=77777)]}], [ledger(sid)])
    assert insights.joined('Counterfactual Atlas') == []


def test_youtube_analytics_lag_has_a_48_hour_quiet_window(tmp_path, monkeypatch):
    sid = '2026-11-15-atlas-s1'
    seed(tmp_path,monkeypatch,[{'title':'Counterfactual Atlas','videos':[row('AAAAAAAAAAA',sid,published=RECENT)]}],
         [ledger(sid)])
    assert len(insights.joined('Counterfactual Atlas')) == 1
    assert insights.guidance('Counterfactual Atlas','short') == ''
    assert insights.slot_stats('Counterfactual Atlas','short') == {}
    assert not insights.mature({'publishedAt':RECENT})
    assert insights.mature({'publishedAt':OLD})


def test_historical_videos_are_context_not_false_engine_attribution(tmp_path, monkeypatch):
    public = [row(f'{i:011d}',None,title=f'Legacy title {i}',views=(i+1)*1000) for i in range(5)]
    seed(tmp_path,monkeypatch,[{'title':'Counterfactual Atlas','videos':public}],[])
    assert insights.joined('Counterfactual Atlas') == []
    notes = insights.guidance('Counterfactual Atlas','short')
    assert 'OBSERVED HISTORICAL VIDEOS FROM THIS SAME CHANNEL' in notes
    assert 'not controlled experiments' in notes
    assert 'Legacy title 4' in notes
    assert 'Legacy title 0' in notes
    assert insights.axis_weights('Counterfactual Atlas',['astronomy','oceans']) == ['astronomy','oceans']


def test_missing_retention_is_neutral_not_reported_as_zero():
    values = {'views':100,'avgPct':0,'subsGained':0}
    assert insights.score(values,100) > insights.score({'views':5,'avgPct':0,'subsGained':0},100)
    assert insights.score({'views':100,'avgPct':10000,'subsGained':0},100) < 1.1
    assert insights.score({'views':100,'avgPct':50,'subsGained':0},100) > 0
