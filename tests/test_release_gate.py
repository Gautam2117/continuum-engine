"""Offline tests enforce approval provenance without needing GitHub credentials."""
import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest
from scripts import release_gate as gate

NOW = dt.datetime(2026, 11, 14, 6, 0, tzinfo=dt.timezone.utc)


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    root = tmp_path / "specs" / "2026-11-16"
    root.mkdir(parents=True)
    spec = root / "atlas-s1.json"
    sample = {"id": "2026-11-16-atlas-s1", "channel": "Counterfactual Atlas",
              "format": "short", "title": "Earth falls", "description": "Proofed descriptive account",
              "publishAt": "2026-11-16T12:00:00Z", "scenes": []}
    spec.write_text(json.dumps(sample))
    monkeypatch.setattr(gate, "problems", lambda *a, **k: [])
    approval = {"id": sample["id"], "decision": "approved", "specSha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
                "reviewArtifact": gate.review_artifact(spec), "reviewRunId": 43512345678,
                "videoSha256": "a" * 64, "thumbnailSha256": "b" * 64,
                "reviewedAt": "2026-11-14T05:00:00Z", "reviewer": "owner",
                "notes": "I watched every scene with audio and checked source citations and image rights."}
    (tmp_path / "approvals").mkdir()
    path = tmp_path / "approvals" / f'{sample["id"]}.json'
    path.write_text(json.dumps(approval))
    return spec, path, approval


def test_exact_owner_approval_passes(tmp_path, monkeypatch):
    spec, _, approval = fixture(tmp_path, monkeypatch)
    assert gate.approval_for(spec, now=NOW) == approval


def test_modified_spec_cannot_reuse_approval(tmp_path, monkeypatch):
    spec, _, _ = fixture(tmp_path, monkeypatch)
    spec.write_text(spec.read_text().replace('Earth falls', 'Earth rises'))
    with pytest.raises(gate.ReleaseRejected, match="changed"):
        gate.approval_for(spec, now=NOW)


def test_fake_model_approval_is_rejected(tmp_path, monkeypatch):
    spec, path, approval = fixture(tmp_path, monkeypatch)
    approval["reviewer"] = "autopilot"
    path.write_text(json.dumps(approval))
    with pytest.raises(gate.ReleaseRejected, match="owner identity"):
        gate.approval_for(spec, now=NOW)


def test_approval_rejects_missing_video_digest_or_ambiguous_run(tmp_path, monkeypatch):
    spec, path, approval = fixture(tmp_path, monkeypatch)
    approval["reviewRunId"] = 0
    path.write_text(json.dumps(approval))
    with pytest.raises(gate.ReleaseRejected, match="run ID"):
        gate.approval_for(spec, now=NOW)
    approval["reviewRunId"] = 43512345678
    approval["videoSha256"] = "not-a-digest"
    path.write_text(json.dumps(approval))
    with pytest.raises(gate.ReleaseRejected, match="videoSha256"):
        gate.approval_for(spec, now=NOW)


def test_stale_publish_time_fails_closed(tmp_path, monkeypatch):
    spec, _, _ = fixture(tmp_path, monkeypatch)
    now = NOW + dt.timedelta(days=3)
    with pytest.raises(gate.ReleaseRejected, match="schedule"):
        gate.approval_for(spec, now=now)


def test_review_checksums_block_tampering(tmp_path):
    result = tmp_path / "review"
    result.mkdir()
    for name in gate.CHECKSUM_FILES:
        (result / name).write_bytes(name.encode())
    lines = [f"{gate._sha(result / name)}  {name}" for name in sorted(gate.CHECKSUM_FILES)]
    (result / "checksums.txt").write_text("\n".join(lines) + "\n")
    gate.verify_checksums(result)
    (result / "video.mp4").write_bytes(b"tampered")
    with pytest.raises(gate.ReleaseRejected, match="changed"):
        gate.verify_checksums(result)


def test_review_checksums_reject_missing_receipt(tmp_path):
    with pytest.raises(gate.ReleaseRejected, match="Missing review checksums"):
        gate.verify_checksums(tmp_path)


def test_stage_reuses_exact_approved_media_and_marks_pack(tmp_path, monkeypatch):
    spec, approval_path, approval = fixture(tmp_path, monkeypatch)
    result = tmp_path / "reviewed" / approval["id"]
    result.mkdir(parents=True)
    (result / "spec.json").write_bytes(spec.read_bytes())
    for name in gate.CHECKSUM_FILES - {"spec.json"}:
        (result / name).write_bytes(b"original " + name.encode())
    (result / "pack.json").write_text(json.dumps({"id": approval["id"]}))
    (result / "probe.json").write_text(json.dumps({"streams": [], "format": {"duration": 1}}))
    (result / "checksums.txt").write_text("\n".join(
        f"{gate._sha(result / name)}  {name}" for name in sorted(gate.CHECKSUM_FILES)
    ) + "\n")
    approval["videoSha256"] = gate._sha(result / "video.mp4")
    approval["thumbnailSha256"] = gate._sha(result / "thumb.jpg")
    approval_path.write_text(json.dumps(approval))
    seen = []
    monkeypatch.setattr(gate, "verify", lambda *a: seen.append("media metadata"))
    monkeypatch.setattr(gate, "verify_audio", lambda *a: seen.append("audible waveform"))
    assert gate.stage(spec, tmp_path / "reviewed", now=NOW) == result
    pack = json.loads((result / "pack.json").read_text())
    assert pack["editorialApproval"]["specSha256"] == approval["specSha256"]
    assert pack["editorialApproval"]["reviewArtifact"] == approval["reviewArtifact"]
    assert pack["editorialApproval"]["videoSha256"] == approval["videoSha256"]
    assert pack["editorialApproval"]["reviewRunId"] == approval["reviewRunId"]
    assert seen == ["media metadata", "audible waveform"]
    # Original review checksums are frozen, and the staged pack is deliberately
    # different. A second attempt cannot silently re-stage mutated review bytes.
    with pytest.raises(gate.ReleaseRejected, match="Review bytes changed"):
        gate.stage(spec, tmp_path / "reviewed", now=NOW)


def test_stage_refuses_different_video_with_same_script_and_valid_checkums(tmp_path, monkeypatch):
    spec, approval_path, approval = fixture(tmp_path, monkeypatch)
    root = tmp_path / "reviewed"
    result = root / approval["id"]
    result.mkdir(parents=True)
    for name in gate.CHECKSUM_FILES:
        (result / name).write_bytes(spec.read_bytes() if name == "spec.json" else b"new video" + name.encode())
    # The technical receipt is internally valid, but this is NOT the video watched.
    (result / "checksums.txt").write_text("\n".join(
        f"{gate._sha(result / name)}  {name}" for name in sorted(gate.CHECKSUM_FILES)
    ) + "\n")
    with pytest.raises(gate.ReleaseRejected, match="differs from the exact cut"):
        gate.stage(spec, root, now=NOW)


def test_private_stage_binds_worker_provenance_and_exact_media(tmp_path, monkeypatch):
    spec, approval_path, approval = fixture(tmp_path, monkeypatch)
    source = tmp_path / f"{approval['id']}-{approval['specSha256']}-{approval['videoSha256']}"
    source.mkdir()
    (source / "spec.json").write_bytes(spec.read_bytes())
    for name in ("pack.json", "probe.json", "thumb.jpg", "video.mp4"):
        (source / name).write_text("{}")
    approval.pop("reviewRunId")
    approval.update(
        reviewSource="private-worker",
        reviewArtifact=f"private-{approval['id']}-{approval['specSha256']}",
    )
    for key, filename in (("videoSha256", "video.mp4"), ("thumbnailSha256", "thumb.jpg")):
        approval[key] = gate._sha(source / filename)
    exact = tmp_path / f"{approval['id']}-{approval['specSha256']}-{approval['videoSha256']}"
    source.rename(exact)
    (exact / "checksums.txt").write_text("".join(
        f"{gate._sha(exact / filename)}  {filename}\n" for filename in gate.CHECKSUM_FILES
    ))
    approval_path.write_text(json.dumps(approval))
    monkeypatch.setattr(gate, "verify", lambda *args: None)
    monkeypatch.setattr(gate, "verify_audio", lambda *args: None)
    with pytest.raises(gate.ReleaseRejected):
        gate.approval_for(spec, now=NOW)
    result = gate.stage_private(spec, exact, tmp_path / "stage", now=NOW)
    receipt = json.loads((result / "pack.json").read_text())["editorialApproval"]
    assert receipt["reviewSource"] == "private-worker"
    assert receipt["videoSha256"] == approval["videoSha256"]
    assert (exact / "pack.json").read_text() == "{}"
    gate.verify_checksums(result)
    (exact / "video.mp4").write_text("replaced master")
    with pytest.raises(gate.ReleaseRejected, match="bytes changed"):
        gate.stage_private(spec, exact, tmp_path / "another-stage", now=NOW)
