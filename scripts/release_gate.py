"""Owner-approved, content-addressed promotion of a technical review to release.

Planning, generating and rendering never approve content. Only a separately
committed approval with the exact spec digest and review artifact can promote.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.spec_check import problems  # noqa: E402
from scripts.review_inventory import review_artifact  # noqa: E402
from scripts.verify_review import verify, verify_audio  # noqa: E402

ID = re.compile(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+\Z")
CHECKSUM_FILES = {"video.mp4", "thumb.jpg", "pack.json", "probe.json", "spec.json"}


class ReleaseRejected(ValueError):
    """The exact reviewed bytes have not been approved for release."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approval_for(spec_path: Path, *, now: dt.datetime | None = None) -> dict:
    """Verify owner approval for the exact spec file, never just a matching title."""
    try:
        spec_path = spec_path.resolve(strict=True)
        if spec_path.parent.parent != ROOT / "specs":
            raise ReleaseRejected("Spec must be in the repository specs/<date>/ directory")
        spec = json.loads(spec_path.read_text())
        sid = spec.get("id")
        if not isinstance(sid, str) or not ID.fullmatch(sid) or sid != f"{spec_path.parent.name}-{spec_path.stem}":
            raise ReleaseRejected("Spec identity and repository path do not agree")
        if issues := problems(spec, spec_path.parent.name, strict=True):
            raise ReleaseRejected("Spec failed strict checks: " + "; ".join(issues[:4]))
        expected_name = review_artifact(spec_path)
        path = ROOT / "approvals" / f"{sid}.json"
        approval = json.loads(path.read_text())
        if not isinstance(approval, dict):
            raise ReleaseRejected("Approval is not an object")
        if approval.get("id") != sid or approval.get("decision") != "approved":
            raise ReleaseRejected("Approval decision or spec identity is invalid")
        if approval.get("specSha256") != _sha(spec_path):
            raise ReleaseRejected("Spec changed after owner approval")
        if approval.get("reviewArtifact") != expected_name:
            raise ReleaseRejected("Approved artifact does not match current spec bytes")
        if approval.get("reviewer") != "owner" or len(str(approval.get("notes") or "").strip()) < 30:
            raise ReleaseRejected("Approval requires explicit owner identity and meaningful review notes")
        when = dt.datetime.fromisoformat(str(approval["reviewedAt"]).replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ReleaseRejected("Approval timestamp must include timezone")
        moment = now or dt.datetime.now(dt.timezone.utc)
        if when > moment + dt.timedelta(minutes=5) or when < moment - dt.timedelta(days=60):
            raise ReleaseRejected("Approval time is outside the valid window")
        publish_at = dt.datetime.fromisoformat(str(spec["publishAt"]).replace("Z", "+00:00"))
        if publish_at.tzinfo is None or publish_at < moment + dt.timedelta(minutes=30):
            raise ReleaseRejected("Release schedule must be at least 30 minutes in the future")
        return approval
    except ReleaseRejected:
        raise
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ReleaseRejected("Missing or malformed approval, spec or schedule") from error


def verify_checksums(result: Path):
    """Every reviewed file must match the checksums saved by the render job."""
    checksums = result / "checksums.txt"
    try:
        lines = checksums.read_text().splitlines()
    except OSError as error:
        raise ReleaseRejected("Missing review checksums") from error
    found: set[str] = set()
    for line in lines:
        match = re.fullmatch(r"([a-f0-9]{64})  \*?([\w.]+)", line.strip())
        if not match:
            raise ReleaseRejected("Malformed review checksum receipt")
        expected, name = match.groups()
        if name not in CHECKSUM_FILES or name in found:
            raise ReleaseRejected("Unexpected or repeated review checksum filename")
        found.add(name)
        if _sha(result / name) != expected:
            raise ReleaseRejected(f"Review bytes changed: {name}")
    if found != CHECKSUM_FILES:
        raise ReleaseRejected("Review checksum receipt is incomplete")


def stage(spec_path: Path, artifact_root: Path, now: dt.datetime | None = None) -> Path:
    """Stage the already-rendered, approved media and add an approval receipt to its pack."""
    spec_path = spec_path.resolve()
    approval = approval_for(spec_path, now=now)
    spec = json.loads(spec_path.read_text())
    result = artifact_root / spec["id"]
    if not result.is_dir():
        raise ReleaseRejected("Reviewed render directory not found")
    verify_checksums(result)
    if (result / "spec.json").read_bytes() != spec_path.read_bytes():
        raise ReleaseRejected("Review contains a different source spec")
    pack = json.loads((result / "pack.json").read_text())
    probe = json.loads((result / "probe.json").read_text())
    verify(spec, pack, probe, result / "thumb.jpg")
    verify_audio(result / "video.mp4")
    pack["editorialApproval"] = {
        "status": "approved", "specSha256": approval["specSha256"],
        "reviewArtifact": approval["reviewArtifact"], "reviewedAt": approval["reviewedAt"],
        "reviewer": "owner",
    }
    (result / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["check", "stage"])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--artifact-root", type=Path)
    args = ap.parse_args()
    try:
        approval = approval_for(args.spec)
        if args.action == "check":
            if output := os.environ.get("GITHUB_OUTPUT"):
                with open(output, "a") as fd:
                    fd.write(f"artifact={approval['reviewArtifact']}\n")
            print("Approval validated for exact source and review artifact")
        else:
            if not args.artifact_root:
                raise ReleaseRejected("--artifact-root is required for stage")
            result = stage(args.spec, args.artifact_root)
            print(f"Approved reviewed package staged at {result}")
    except ReleaseRejected as error:
        ap.exit(1, f"RELEASE REJECTED: {error}\n")


if __name__ == "__main__":
    main()
