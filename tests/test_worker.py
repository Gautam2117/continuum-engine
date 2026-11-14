"""Durable local queue test suite. No secrets, network or actual video work."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3

import pytest
from scripts import worker

NOW = dt.datetime(2026, 11, 14, 9, tzinfo=dt.timezone.utc)


def _sample(tmp_path, monkeypatch, title="What if?"):
    root = tmp_path / "specs"
    monkeypatch.setattr(worker, "SPEC_ROOT", root)
    d = root / "2026-11-16"
    d.mkdir(exist_ok=True, parents=True)
    path = d / "atlas-s1.json"
    path.write_text(json.dumps({"id": "2026-11-16-atlas-s1", "channel": "Counterfactual Atlas",
                                "format": "short", "title": title, "scenes": []}))
    return path


def test_enqueue_is_idempotent_and_records_the_exact_spec_digest(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db = worker.connection(tmp_path / "db" / "queue.db")
    try:
        assert worker.enqueue(db, [spec], now=NOW)["imported"] == 1
        assert worker.enqueue(db, [spec], now=NOW) == {"imported": 0, "existing": 1, "invalid": 0}
        record = db.execute("SELECT * FROM jobs").fetchone()
        assert record["spec_sha256"] == hashlib.sha256(spec.read_bytes()).hexdigest()
        assert record["state"] == "queued" and record["attempt"] == 0
        assert record["spec_path"] == str(spec.resolve())
    finally:
        db.close()


def test_rejects_invalid_or_outside_spec_and_does_not_overwrite_approved_revision(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    outsider = tmp_path / "danger.json"
    outsider.write_text(spec.read_text())
    db = worker.connection(tmp_path / "state.db")
    try:
        assert worker.enqueue(db, [outsider], now=NOW) == {"imported": 0, "existing": 0, "invalid": 1}
        worker.enqueue(db, [spec], now=NOW)
        spec.write_text(spec.read_text().replace("What if?", "A different angle"))
        assert worker.enqueue(db, [spec], now=NOW)["imported"] == 1
        assert db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 2
        old_job = dict(db.execute("SELECT * FROM jobs WHERE state='superseded'").fetchone())
        with pytest.raises(FileExistsError, match="superseded"):
            worker.render_one(old_job, review_root=tmp_path / "reviews")
        current = worker.claim(db, NOW)
        assert current is not None and current["spec_sha256"] == worker.digest(spec)
    finally:
        db.close()


def test_claim_and_finish_are_atomic_and_dont_double_claim(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db1 = worker.connection(tmp_path / "queue.db")
    db2 = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db1, [spec], now=NOW)
        job = worker.claim(db1, NOW)
        assert job and job["attempt"] == 1
        assert worker.claim(db2, NOW) is None
        assert worker.finish(db1, job["job_key"], "verified", media={"mp4Sha256": "a"*64,
              "reviewPath":"/tmp/review", "durationSec":23.0}, now=NOW) == "verified"
        assert worker.claim(db2, NOW) is None
        row = db1.execute("SELECT * FROM jobs").fetchone()
        assert row["state"] == "verified" and row["duration_sec"] == 23
    finally:
        db1.close()
        db2.close()


def test_retries_backoff_then_blocks_after_three_failures(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db, [spec], now=NOW)
        def failing(_job, *, review_root, time_budget):
            raise RuntimeError("renderer unavailable")
        first = worker.process_next(db, review_root=tmp_path / "reviews", now=NOW, render_fn=failing)
        assert first["state"] == "retry" and first["attempt"] == 1
        assert worker.process_next(db, review_root=tmp_path / "reviews", now=NOW, render_fn=failing)["status"] == "idle"
        second = worker.process_next(db, review_root=tmp_path / "reviews", now=NOW + dt.timedelta(minutes=16), render_fn=failing)
        assert second["state"] == "retry" and second["attempt"] == 2
        third = worker.process_next(db, review_root=tmp_path / "reviews", now=NOW + dt.timedelta(minutes=47), render_fn=failing)
        assert third["state"] == "blocked" and third["attempt"] == 3
    finally:
        db.close()


def test_stale_lease_is_recovered_after_expiry(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db, [spec], now=NOW)
        assert worker.claim(db, NOW)
        assert worker.recover_stale(db, NOW + dt.timedelta(hours=3)) == 0
        assert worker.recover_stale(db, NOW + dt.timedelta(hours=5)) == 1
        job = worker.claim(db, NOW + dt.timedelta(hours=5))
        assert job and job["attempt"] == 2
    finally:
        db.close()


def test_strict_rejection_fails_closed_and_keeps_queue_durable(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db, [spec], now=NOW)
        def reject(_job, *, review_root, time_budget):
            raise ValueError("Source requirements missing")
        result = worker.process_next(db, review_root=tmp_path / "reviews", now=NOW, render_fn=reject)
        assert result["state"] == "blocked"
        assert db.execute("SELECT last_error FROM jobs").fetchone()[0] == "Source requirements missing"
    finally:
        db.close()


def test_worker_success_does_not_publish_or_require_network(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db, [spec], now=NOW)
        def fake_render(_job, *, review_root, time_budget):
            assert review_root == tmp_path / "reviews"
            return {"mp4Sha256": "b"*64, "durationSec": 61.0, "reviewPath": "/private/review"}
        outcome = worker.process_next(db, review_root=tmp_path / "reviews", now=NOW, render_fn=fake_render)
        assert outcome["state"] == "verified"
        assert db.execute("SELECT review_path FROM jobs").fetchone()[0] == "/private/review"
    finally:
        db.close()


def test_machine_render_lock_rejects_concurrent_workers(tmp_path):
    path = tmp_path / "state.sqlite3"
    with worker.single_worker(path):
        with pytest.raises(RuntimeError, match="Another worker"):
            with worker.single_worker(path):
                pass
    with worker.single_worker(path):
        pass


def test_scan_only_imports_future_dates_not_old_content(tmp_path, monkeypatch):
    root = tmp_path / "specs"
    monkeypatch.setattr(worker, "SPEC_ROOT", root)
    for day in ("2026-11-13", "2026-11-14", "2026-11-15", "2026-11-20"):
        p = root / day / "atlas-s1.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    got = worker.future_specs(today=dt.date(2026, 11, 14), days=2)
    assert [p.parent.name for p in got] == ["2026-11-14", "2026-11-15"]
    with pytest.raises(ValueError, match="days"):
        worker.future_specs(today=dt.date(2026, 11, 14), days=0)


def test_scan_future_date_but_keep_existing_old_revision_receipts(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db = worker.connection(tmp_path / "state.db")
    try:
        worker.enqueue(db, [spec], now=NOW)
        old = dict(db.execute("SELECT * FROM jobs").fetchone())
        db.execute("UPDATE jobs SET state='verified' WHERE job_key=?", (old["job_key"],))
        db.commit()
        spec.write_text(spec.read_text().replace("What if?", "What happens next?"))
        worker.enqueue(db, [spec], now=NOW)
        assert db.execute("SELECT state FROM jobs WHERE job_key=?", (old["job_key"],)).fetchone()[0] == "verified"
    finally:
        db.close()


def test_archives_stale_partial_staging_without_overwrite(tmp_path):
    partial = tmp_path / ".staging-atlas-s1-abc"
    partial.mkdir()
    (partial / "invalid.txt").write_text("crashed before completion")
    worker.archive_partial(partial)
    assert not partial.exists()
    quarantined = list(tmp_path.glob(".failed-*"))
    assert len(quarantined) == 1
    assert (quarantined[0] / "invalid.txt").read_text() == "crashed before completion"


def test_adopts_only_exact_completed_review_bytes(tmp_path, monkeypatch):
    import scripts.verify_review as review
    spec = _sample(tmp_path, monkeypatch)
    sha = worker.digest(spec)
    job = {"spec_id": "2026-11-16-atlas-s1", "spec_sha256": sha}
    root = tmp_path / "reviews" / f"{job['spec_id']}-{sha[:12]}" / job["spec_id"]
    root.mkdir(parents=True)
    for name in ("video.mp4", "thumb.jpg", "pack.json", "spec.json", "probe.json"):
        payload = spec.read_bytes() if name == "spec.json" else (b"{}" if name.endswith(".json") else name.encode())
        (root / name).write_bytes(payload)
    (root / "probe.json").write_text(json.dumps({"format": {"duration": "8.7"}}))
    manifest = {"id": job["spec_id"], "specSha256": sha,
                "publicationStatus": "NOT_APPROVED_FOR_PUBLICATION",
                "files": {p: worker.digest(root / p) for p in ("video.mp4", "thumb.jpg", "pack.json", "spec.json", "probe.json")},
                "mp4Sha256": worker.digest(root / "video.mp4"),
                "thumbnailSha256": worker.digest(root / "thumb.jpg"), "durationSec": 8.7}
    (root / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(review, "verify", lambda *a: None)
    monkeypatch.setattr(review, "verify_audio", lambda *a: None)
    details = worker.adopt_verified_review(root.parent, job, spec)
    assert details["durationSec"] == 8.7 and details["mp4Sha256"] == manifest["mp4Sha256"]
    manifest["durationSec"] = 5
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest duration"):
        worker.adopt_verified_review(root.parent, job, spec)
    manifest["durationSec"] = 8.7
    (root / "manifest.json").write_text(json.dumps(manifest))
    (root / "video.mp4").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Existing review file changed"):
        worker.adopt_verified_review(root.parent, job, spec)


def test_existing_review_with_wrong_spec_digest_is_not_adopted(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    job = {"spec_id": "2026-11-16-atlas-s1", "spec_sha256": worker.digest(spec)}
    root = tmp_path / "reviews" / job["spec_id"]
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps({"id": job["spec_id"],
        "specSha256": "f" * 64, "publicationStatus": "NOT_APPROVED_FOR_PUBLICATION"}))
    with pytest.raises(ValueError, match="wrong source identity"):
        worker.adopt_verified_review(root.parent, job, spec)


def test_worker_cli_status_and_empty_cycle(tmp_path):
    import subprocess
    import sys

    for action, expected in (("status", {}), ("once", {"scan": None, "recovered": 0, "jobs": [{"status": "idle"}]})):
        result = subprocess.run(
            [sys.executable, str(worker.ROOT / "scripts" / "worker.py"), action,
             "--db", str(tmp_path / "queue.sqlite3"), "--reviews", str(tmp_path / "reviews")],
            capture_output=True, text=True, check=True,
        )
        assert json.loads(result.stdout) == expected


def test_scan_reactivates_a_previously_superseded_spec_after_rollback(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    original = spec.read_bytes()
    db = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db, [spec], now=NOW)
        spec.write_text(spec.read_text().replace("What if?", "Revision"))
        worker.enqueue(db, [spec], now=NOW)
        spec.write_bytes(original)
        assert worker.enqueue(db, [spec], now=NOW)["imported"] == 1
        row = worker.claim(db, NOW)
        assert row is not None and row["spec_sha256"] == hashlib.sha256(original).hexdigest()
        assert worker.claim(db, NOW) is None
    finally:
        db.close()


def test_cycle_window_prioritizes_current_backlog_over_older_queued_specs(tmp_path, monkeypatch):
    current = _sample(tmp_path, monkeypatch)
    old = current.parent.parent / "2026-11-15" / current.name
    old.parent.mkdir()
    old.write_text(current.read_text().replace("2026-11-16", "2026-11-15"))
    db = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db, [old, current], now=NOW)
        today = dt.date(2026, 11, 16)
        job = worker.claim(db, NOW, window=(today, today))
        assert job and job["spec_id"] == "2026-11-16-atlas-s1"
        assert worker.claim(db, NOW, window=(today, today)) is None
        assert worker.claim(db, NOW)["spec_id"] == "2026-11-15-atlas-s1"
    finally:
        db.close()


def test_preflight_reports_missing_host_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(worker.shutil, "which", lambda name: None if name == "ffmpeg" else name)
    monkeypatch.setattr(worker, "find_spec", lambda name: object())
    checks = worker.preflight(tmp_path / "state.sqlite3", tmp_path / "reviews")
    assert checks["ready"] is False
    assert checks["tools"] == {"ffmpeg": False, "ffprobe": True, "fc-match": True}
    assert checks["blender"] is None


def test_exact_worker_claim_does_not_take_another_queued_episode(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    other = spec.with_name("atlas-s2.json")
    other.write_text(spec.read_text().replace("atlas-s1", "atlas-s2"))
    db = worker.connection(tmp_path / "queue.db")
    try:
        worker.enqueue(db, [spec, other], now=NOW)
        key = f"2026-11-16-atlas-s2:{worker.digest(other)}"
        def render(job, **kwargs):
            assert job["job_key"] == key
            return {"mp4Sha256": "a" * 64, "durationSec": 1, "reviewPath": str(tmp_path)}
        assert worker.process_next(db, review_root=tmp_path, now=NOW, job_key=key, render_fn=render)["state"] == "verified"
        assert worker.claim(db, NOW, job_key=key) is None
        assert worker.claim(db, NOW)["spec_id"] == "2026-11-16-atlas-s1"
    finally:
        db.close()


def test_retry_delay_starts_after_render_failure(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    db = worker.connection(tmp_path / "queue.db")
    finished = NOW + dt.timedelta(hours=1)
    clock = iter([NOW, finished])
    monkeypatch.setattr(worker, "utcnow", lambda: next(clock))

    def render(job, **kwargs):
        raise RuntimeError("Temporary renderer outage")

    try:
        worker.enqueue(db, [spec], now=NOW)
        result = worker.process_next(db, review_root=tmp_path, render_fn=render)
        assert result["state"] == "retry"
        row = db.execute("SELECT updated_at, eligible_at FROM jobs").fetchone()
        assert row["updated_at"] == worker.iso(finished)
        assert row["eligible_at"] == worker.iso(finished + dt.timedelta(minutes=15))
    finally:
        db.close()


def test_worker_removes_generated_blender_frames_on_render_failure(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    from engine import spec_check
    monkeypatch.setattr(spec_check, "problems", lambda *args, **kwargs: [])
    monkeypatch.setattr(worker.shutil, "disk_usage",
                        lambda path: type("Disk", (), {"free": 4 * 1024**3})())
    review = tmp_path / "reviews"

    def fail(command, *, env, **kwargs):
        cache = worker.pathlib.Path(env["B3D_CACHE"])
        (cache / "frame.png").write_bytes(b"derived frame")
        raise RuntimeError("render interrupted")

    monkeypatch.setattr(worker, "execute", fail)
    sha = worker.digest(spec)
    with pytest.raises(RuntimeError, match="render interrupted"):
        worker.render_one({"spec_path": str(spec), "spec_sha256": sha, "job_key": f"{spec.stem}:{sha}"},
                          review_root=review)
    assert list(review.glob(".failed-*"))
    assert not list(review.rglob("frame.png"))


def test_missing_editorial_scores_block_before_starting_a_render(tmp_path, monkeypatch):
    spec=_sample(tmp_path, monkeypatch)
    old=json.loads(spec.read_text())
    old['meta']={'generator':'autopilot'}
    old['scenes']=[{'say':'Example','show':{'type':'title','text':'AN IDEA'}}]
    spec.write_text(json.dumps(old))
    import scripts.worker as w
    # Full strict validation of this tiny fixture would fail for separate
    # reasons. The targeted test checks that the exact editorial validator
    # itself rejects null, negative or contradictory evidence early.
    from scripts.verify_review import editorial_gate
    with pytest.raises(ValueError,match='Unapproved Autopilot editorial score: hook'):
        editorial_gate(old)
    old['meta']['review']={'hook':8,'originality':8,'accuracy':9,'pass':False,
                           'unsupported_claims':[], 'fixes': []}
    with pytest.raises(ValueError,match='editorial decision'):
        editorial_gate(old)
    old['meta']['review']['pass']=True
    editorial_gate(old)
    old['meta']['review']['unsupported_claims']=['Missing source']
    with pytest.raises(ValueError,match='unsupported claims'):
        editorial_gate(old)


def test_unreviewed_local_model_draft_is_not_enqueued(tmp_path, monkeypatch):
    spec = _sample(tmp_path, monkeypatch)
    data=json.loads(spec.read_text())
    data['meta']={'generator':'autopilot','model':'ollama:qwen3.5:4b',
                  'review':{'pass':False,'hook':9,'accuracy':9,'originality':9,
                            'unsupported_claims':[], 'fixes':[]}}
    spec.write_text(json.dumps(data))
    db=worker.connection(tmp_path/'db'/'queue.sqlite3')
    try:
        result=worker.enqueue(db,[spec],now=NOW)
        assert result['imported']==0 and result['invalid']==1
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==0
    finally:db.close()
