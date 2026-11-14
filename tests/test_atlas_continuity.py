import datetime as dt
import json
import pytest
from scripts import atlas_continuity

DAY=dt.date(2026,11,15)

def test_runway_reports_three_missing_each_day_without_misreporting_uploads(tmp_path):
    report=atlas_continuity.audit(tmp_path/'specs',tmp_path/'missing.sqlite3',today=DAY,days=8)
    assert len(report['runway'])==8
    assert report['completeSpecDays']==0
    assert report['dailyTarget']=={'short':2,'long':1}
    assert report['plannedEndDate'] is None
    assert all(r['specSlotsMissing']==3 and r['publicYouTubeVideos'] is None for r in report['runway'])
    assert all(r['privateWorkerStates']=={} for r in report['runway'])

def test_runway_cannot_silently_accept_wrong_horizon(tmp_path):
    for days in (-1,0,31):
        with pytest.raises(ValueError):
            atlas_continuity.audit(tmp_path,tmp_path/'missing',today=DAY,days=days)
