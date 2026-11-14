"""No network calls in market research tests; observable quota and provenance."""
from __future__ import annotations
import datetime as dt
import pytest
from autopilot import market, insights, daily
from scripts.market_scan import build_plan,main

NOW=dt.datetime(2026,11,14,9,0,tzinfo=dt.timezone.utc)

def test_each_channel_has_unique_audience_query_and_rotates_fairly():
    market.verify()
    assert len(market.QUERY)==48
    assert market.rotate(NOW.date(),0)==[]
    found=[c for d in range(7) for c in market.rotate(NOW.date()+dt.timedelta(days=d),7)]
    assert len(set(found))==48
    assert 'Felix' not in found and 'GOTZ' not in found


def test_reserves_upload_quota_while_defaulting_to_offline_dry_run(capsys):
    assert market.quota_allowed(75,500,48,10000)==19
    assert market.quota_allowed(97,500,48,10000)==0
    assert market.quota_allowed(50,500,48,10000)==44
    assert main(['--date','2026-11-14','--limit','3'])==0
    output=capsys.readouterr().out
    assert 'PLAN_ONLY_NO_NETWORK' in output
    assert 'estimatedQuotaUnits' in output


def test_live_mode_without_credential_is_blocked(capsys,monkeypatch):
    monkeypatch.delenv('YOUTUBE_DATA_API_KEY',raising=False)
    with pytest.raises(SystemExit) as err:
        main(['--live','--limit','1'])
    assert err.value.code==2
    assert 'requires YOUTUBE_DATA_API_KEY' in capsys.readouterr().err


class MockClient:
    def __init__(self):self.calls=[]
    def call(self,endpoint,data):
        self.calls.append((endpoint,data))
        if endpoint=='search':
            return {'items':[{'id':{'videoId':'ABCDEFGHIJK'}},{'id':{'videoId':'BAD'}}]}
        if endpoint=='videos':
            return {'items':[{'id':'ABCDEFGHIJK',
                'snippet':{'title':'Verified public example','publishedAt':'2026-11-10T14:00:00Z',
                           'channelId':'chan1','channelTitle':'Independent creator'},
                'statistics':{'viewCount':'350000','likeCount':'12000'},
                'contentDetails':{'duration':'PT45S'}}]}
        if endpoint=='channels':return {'items':[{'id':'chan1','statistics':{'subscriberCount':'10000'}}]}
        raise AssertionError(endpoint)


def test_single_channel_uses_exact_public_sources_and_separate_denominators():
    fake=MockClient()
    result=market.scan_channel('Counterfactual Atlas',fake,now=NOW)
    assert [c[0] for c in fake.calls]==['search','videos','channels']
    assert fake.calls[0][1]['q']==market.QUERY['Counterfactual Atlas']
    assert result['videos'][0]['url']=='https://www.youtube.com/watch?v=ABCDEFGHIJK'
    assert result['videos'][0]['views']==350000
    assert result['videos'][0]['viewsPerSubscriberProxy']==35.0
    assert result['videos'][0]['engagementRateLikesOnly']==round(12000/350000,4)
    assert 'not a causal' in result['metricWarning']


def test_own_channel_only_uses_mature_public_signals(tmp_path,monkeypatch):
    monkeypatch.setattr(insights,'STATE',tmp_path)
    fake=MockClient()
    snapshot=market.scan_channel('Counterfactual Atlas',fake,now=NOW)
    market.record('Counterfactual Atlas',snapshot)
    a=market.guidance('Counterfactual Atlas',now=NOW+dt.timedelta(days=2))
    assert '350,000 views' in a
    assert 'do NOT reproduce' in a or 'Do NOT reproduce' in a
    assert market.guidance('Foundbeam',now=NOW+dt.timedelta(days=2))==''
    assert market.guidance('Counterfactual Atlas',now=NOW+dt.timedelta(days=23))==''
    assert len(insights.load('market_signals.json',{}).get('channels',{}))==1


def test_topic_generator_includes_only_own_observations(monkeypatch,tmp_path):
    monkeypatch.setattr(insights,'STATE',tmp_path)
    monkeypatch.setattr(daily,'SPECS',tmp_path/'empty')
    market.record('Counterfactual Atlas',market.scan_channel('Counterfactual Atlas',MockClient(),now=NOW))
    planner=daily.Planner.__new__(daily.Planner)
    planner.topics={}
    messages=[]
    def fake_call(system,user,**kwargs):
        messages.append(user)
        return {'topics':[{'topic':'Another original scenario','axis':'moon','wiki_query':'moon'}]}
    planner._call=fake_call
    monkeypatch.setattr(market,'guidance',lambda channel: 'ATLAS-ONLY-SIGNAL' if channel=='Counterfactual Atlas' else '')
    planner.pick_topic('Counterfactual Atlas','short')
    assert 'ATLAS-ONLY-SIGNAL' in messages[0]
    messages.clear()
    planner.pick_topic('Foundbeam','short')
    assert 'ATLAS-ONLY-SIGNAL' not in messages[0]
