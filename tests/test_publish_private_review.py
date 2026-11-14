"""Approved worker package publishing never uploads or overwrites unapproved bytes."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from scripts import publish_private_review as pub
from scripts import release_gate as gate


def test_publisher_refuses_missing_approval_before_any_github_call(tmp_path,monkeypatch):
    spec=tmp_path/'2026-11-16-atlas-s1.json';spec.write_text('{}')
    monkeypatch.setattr(pub,'github',lambda *a,**kw:pytest.fail('must not invoke GitHub'))
    with pytest.raises((gate.ReleaseRejected,OSError,ValueError)):
        pub.release_verified(spec,tmp_path/'none')


def test_dry_run_is_not_an_upload(tmp_path,monkeypatch):
    monkeypatch.setattr(pub,'checked_package',lambda *a:('2026-11-16-atlas-s1','2026-11-16'))
    monkeypatch.setattr(pub,'github',lambda *a,**kw:pytest.fail('dry run must not contact GitHub'))
    result=pub.release_verified(tmp_path/'spec',tmp_path/'staged',dry_run=True)
    assert result['publishedToYouTube'] is False
    assert result['status']=='validated-only'


def test_release_never_clobbers_existing_assets(tmp_path,monkeypatch):
    sid='2026-11-16-atlas-s1'
    monkeypatch.setattr(pub,'checked_package',lambda *a:(sid,'2026-11-16'))
    def fake(*args,**kw):
        if args[:2]==('release','view'):
            class Response:
                returncode=0
                stdout=json.dumps({'assets':[{'name':sid+'-video.mp4'}]})
            return Response()
        pytest.fail('must not upload when the episode already has a release asset')
    monkeypatch.setattr(pub,'github',fake)
    with pytest.raises(gate.ReleaseRejected,match='already exist'):
        pub.release_verified(tmp_path/'spec',tmp_path/'staged')
