"""No expiry: Atlas always plans three independent, non-overlapping windows."""
import datetime as dt
import pytest
from autopilot.slots import ATLAS_WINDOWS, atlas_daily_slots
UTC=dt.timezone.utc

def test_every_day_through_end_2027_has_three_nonoverlapping_exploration_slots():
    start=dt.date(2026,11,15)
    finish=dt.date(2027,12,31)
    seen_long_windows=set()
    for index in range((finish-start).days+1):
        day=start+dt.timedelta(days=index)
        before=dt.datetime.combine(day-dt.timedelta(days=1),dt.time(0),tzinfo=UTC)
        slots=atlas_daily_slots(day,before,{}, {})
        assert len(slots['short'])==2 and len(slots['long'])==1,day
        all_times=sorted(slots['short']+slots['long'])
        assert len({x.date() for x in all_times})==1
        assert all(x>before+dt.timedelta(hours=4.5) for x in all_times)
        assert all(b-a>=dt.timedelta(hours=3) for a,b in zip(all_times,all_times[1:]))
        for when in slots['long']:
            for i,(_,values) in enumerate(ATLAS_WINDOWS):
                if any(abs(when.hour*60+when.minute-(int(v[:2])*60+int(v[3:])))<=7 for v in values):
                    seen_long_windows.add(i)
    assert seen_long_windows=={0,1,2}

def test_resumption_preserves_existing_and_rejects_close_times():
    day=dt.date(2026,11,17)
    before=dt.datetime(2026,11,16,tzinfo=UTC)
    slots=atlas_daily_slots(day,before,{}, {})
    already=(slots['short'][0],)
    leftover=atlas_daily_slots(day,before,{}, {},existing=already,need_short=1,need_long=1)
    assert len(leftover['short'])==1 and len(leftover['long'])==1
    assert all(abs((x-already[0]).total_seconds())>=3*3600 for x in leftover['short']+leftover['long'])
    with pytest.raises(ValueError):
        atlas_daily_slots(day,dt.datetime(2026,11,16),{}, {})
    with pytest.raises(ValueError):
        atlas_daily_slots(day,before,{}, {},need_short=3)

def test_real_mature_winner_gets_preferred_without_claiming_best_global_time():
    day=dt.date(2027,3,13);before=dt.datetime(2027,3,12,tzinfo=UTC)
    stats={v:(12,0.35) for _,region in ATLAS_WINDOWS for v in region}
    stats['20:30']=(12,1.0)
    results=atlas_daily_slots(day,before,stats,stats)
    assert any(abs(t.hour*60+t.minute-(20*60+30))<=7 for t in results['long']+results['short'])

def test_expired_slots_are_not_backfilled_as_immediate_public_uploads():
    day=dt.date(2027,1,14)
    now=dt.datetime(2027,1,14,22,0,tzinfo=UTC)
    result=atlas_daily_slots(day,now,{}, {})
    assert result['short']==[] and result['long']==[]
