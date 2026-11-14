"""Cryptographic replay and no deletion for the private render archive."""
from __future__ import annotations
import hashlib,json,pathlib,sqlite3
import pytest
from scripts import archive_verified_reviews as a
from scripts.worker import connection,SCHEMA


def fixture(tmp_path):
    folder=tmp_path/'source'/'episode'
    folder.mkdir(parents=True)
    files={}
    for name in a.REQUIRED:
        p=folder/name
        p.write_bytes((name+' original video data').encode())
        files[name]=a.digest(p)
    sid='2026-11-17-pixel-s1'
    spec=files['spec.json']
    (folder/'manifest.json').write_text(json.dumps({
        'id':sid, 'specSha256':spec,
        'publicationStatus':'NOT_APPROVED_FOR_PUBLICATION',
        'files':files,'mp4Sha256':files['video.mp4'],
        'thumbnailSha256':files['thumb.jpg']
    }))
    arch=tmp_path/'archive'
    arch.mkdir()
    return folder,arch,sid,spec


def test_copy_preserves_source_and_is_idempotent(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    r=a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha,require_distinct_device=False)
    assert r['status']=='archived' and r['bytes']>0
    r=a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha,require_distinct_device=False)
    assert r['status']=='already-verified'
    assert (src/'video.mp4').exists()
    assert a.verify_package(arch/f'{sid}-{sha[:12]}',expected_id=sid,expected_sha=sha)['bytes']>0


def test_same_disk_fails_closed_in_production(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    with pytest.raises(ValueError, match='distinct mounted filesystem'):
        a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha)
    assert not list(arch.iterdir())


def test_corrupt_and_symlink_media_refused(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    (src/'video.mp4').write_bytes(b'tampered')
    with pytest.raises(ValueError,match='checksum mismatch'):
        a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha,require_distinct_device=False)
    assert not list(arch.iterdir())
    src,arch,sid,sha=fixture(tmp_path/'fresh')
    (src/'video.mp4').unlink()
    (src/'video.mp4').symlink_to(src/'thumb.jpg')
    with pytest.raises(ValueError,match='symlink'):
        a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha,require_distinct_device=False)


def test_db_video_digest_mismatch_refuses_archive(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    with pytest.raises(ValueError, match="verified worker database"):
        a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha,
                        expected_video_sha='f'*64,require_distinct_device=False)
    assert not list(arch.iterdir())


def test_invalid_id_cannot_escape_archive_directory(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    with pytest.raises(ValueError, match="Invalid verified worker identity"):
        a.replicate_one(src,arch,spec_id='../../unsafe',spec_sha256=sha,
                        require_distinct_device=False)
    assert not list(arch.iterdir())


def test_manifest_spec_hash_cannot_differ_from_reviewed_source(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    manifest=src/'manifest.json'
    data=json.loads(manifest.read_text())
    data['specSha256']='f'*64
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Source spec checksum differs"):
        a.verify_package(src)


def test_existing_copy_corruption_never_gets_overwritten(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha,require_distinct_device=False)
    target=arch/f'{sid}-{sha[:12]}'/'video.mp4'
    target.write_bytes(b'tampered')
    with pytest.raises(ValueError,match='checksum mismatch'):
        a.replicate_one(src,arch,spec_id=sid,spec_sha256=sha,require_distinct_device=False)
    assert target.read_bytes()==b'tampered'


def test_only_database_verified_jobs_qualify(tmp_path):
    src,arch,sid,sha=fixture(tmp_path)
    db=tmp_path/'worker.sqlite3'
    with connection(db) as conn:
        conn.execute("INSERT INTO jobs(job_key,spec_id,spec_path,spec_sha256,channel,format,state,eligible_at,updated_at,mp4_sha256,review_path) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                     (f'{sid}:{sha}',sid,'spec.json',sha,'Pixel Fables','short','verified','2026-11-17','2026-11-17',a.digest(src/'video.mp4'),str(src)))
    report=a.archive(db,tmp_path/'source',arch,require_distinct_device=False)
    assert report['verifiedReceipts']==1 and report['archived']==1 and report['sourcePreserved']
    assert a.archive(db,tmp_path/'source',arch,require_distinct_device=False)['alreadyVerified']==1


def test_relative_worker_paths_resolve_from_repo_not_shell(tmp_path,monkeypatch):
    repo=tmp_path/'repo'
    review=repo/'var'/'reviews'
    src,unused,sid,sha=fixture(review)
    db=repo/'var'/'worker.sqlite3'
    with connection(db) as conn:
        conn.execute("INSERT INTO jobs(job_key,spec_id,spec_path,spec_sha256,channel,format,state,eligible_at,updated_at,mp4_sha256,review_path) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                     (f'{sid}:{sha}',sid,'spec.json',sha,'Pixel Fables','short','verified','2026-11-17','2026-11-17',a.digest(src/'video.mp4'),str(src.relative_to(repo))))
    arch=tmp_path/'actual-external-device-fixture'
    arch.mkdir()
    monkeypatch.chdir(tmp_path)
    report=a.archive(db,review,arch,require_distinct_device=False)
    assert report['archived']==1 and report['errors']==[]
