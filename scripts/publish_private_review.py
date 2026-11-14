"""Attach ONLY an exact owner-approved local worker review to the public Engine release.

No model may sign approvals and no media is uploaded unless the source spec,
original video, thumbnail, private-worker receipt, checksum file, owner notes
and FUTURE publishAt all agree. Never clobber an existing release asset.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

from scripts import release_gate as gate

REPO = "Gautam2117/continuum-engine"


def checked_package(spec_path: pathlib.Path, staged: pathlib.Path) -> tuple[str, str]:
    spec_path = spec_path.resolve(strict=True)
    approval = gate.approval_for(spec_path, private=True)
    spec = json.loads(spec_path.read_text())
    sid = spec["id"]
    expected = f"{sid}-{approval['specSha256']}-{approval['videoSha256']}"
    if staged.is_symlink() or not staged.is_dir() or staged.name != expected:
        raise gate.ReleaseRejected("Staged private review directory must match exact approved source and media digests")
    gate.verify_checksums(staged)
    for key in ("video.mp4", "thumb.jpg", "spec.json", "pack.json"):
        f = staged / key
        if f.is_symlink() or not f.is_file():
            raise gate.ReleaseRejected("Unexpected missing or symlinked reviewed file: " + key)
    if (staged / "spec.json").read_bytes() != spec_path.read_bytes():
        raise gate.ReleaseRejected("Private package was rendered from another source spec")
    if gate._sha(staged / "video.mp4") != approval["videoSha256"]:
        raise gate.ReleaseRejected("Unapproved video bytes")
    if gate._sha(staged / "thumb.jpg") != approval["thumbnailSha256"]:
        raise gate.ReleaseRejected("Unapproved thumbnail bytes")
    pack = json.loads((staged / "pack.json").read_text())
    receipt = pack.get("editorialApproval") or {}
    if not isinstance(receipt, dict) or any(
        receipt.get(k) != approval.get(k)
        for k in ("specSha256", "videoSha256", "thumbnailSha256", "reviewArtifact", "reviewSource", "reviewer", "reviewedAt")
    ) or receipt.get("status") != "approved" or receipt.get("reviewSource") != "private-worker":
        raise gate.ReleaseRejected("No exact owner-approved private worker receipt in staged pack")
    expected_date = approval.get("scheduledPublishAt") or spec["publishAt"]
    if pack.get("publishAt") != expected_date:
        raise gate.ReleaseRejected("Owner-approved release time and pack time disagree")
    return sid, spec_path.parent.name


def github(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["gh", *args, "--repo", REPO],
                            capture_output=True, text=True, timeout=120)
    if check and result.returncode:
        raise RuntimeError(f"GitHub release command failed ({result.returncode}): {result.stderr[:240]}")
    return result


def release_verified(spec: pathlib.Path, staged: pathlib.Path, *, dry_run: bool = False) -> dict:
    sid, tag = checked_package(spec, staged)
    expected_names = [f"{sid}-video.mp4",f"{sid}-thumb.jpg",f"{sid}-pack.json"]
    if dry_run:
        return {"status":"validated-only", "id":sid, "tag":tag, "assets":expected_names,
                "publishedToYouTube":False}
    existing = github("release","view",tag,"--json","assets",check=False)
    if existing.returncode:
        # A missing tag is legitimate; all other errors fail if create fails.
        github("release","create",tag,"--title",f"Approved renders {tag}",
               "--notes","Only exactly approved videos are released here. YouTube upload is a separate guarded operation.")
        existing = github("release","view",tag,"--json","assets")
    assets = json.loads(existing.stdout or "{}").get("assets",[])
    present = {a.get("name") for a in assets if isinstance(a,dict)}
    if present.intersection(expected_names):
        raise gate.ReleaseRejected("One or more assets already exist for this episode; refuse overwriting released bytes")
    with tempfile.TemporaryDirectory(prefix=".atlas-release-") as tmp:
        tmpdir = pathlib.Path(tmp)
        for name, original in zip(expected_names,("video.mp4","thumb.jpg","pack.json")):
            shutil.copyfile(staged/original,tmpdir/name)
        # Last-line integrity check after copy and before making it public.
        if gate._sha(tmpdir/expected_names[0]) != gate._sha(staged/"video.mp4") or \
           gate._sha(tmpdir/expected_names[1]) != gate._sha(staged/"thumb.jpg"):
            raise gate.ReleaseRejected("Copied approved media checksum changed before upload")
        # The pack is uploaded LAST. Studio never picks up incomplete video/thumb pairs.
        github("release","upload",tag,str(tmpdir/expected_names[0]),str(tmpdir/expected_names[1]))
        github("release","upload",tag,str(tmpdir/expected_names[2]))
    return {"status":"approved-assets-uploaded", "id":sid, "tag":tag, "assets":expected_names,
            "publishedToYouTube":False}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec",type=pathlib.Path)
    ap.add_argument("staged",type=pathlib.Path)
    ap.add_argument("--dry-run",action="store_true")
    args=ap.parse_args()
    os.umask(0o077)
    print(json.dumps(release_verified(args.spec,args.staged,dry_run=args.dry_run),indent=2))

if __name__ == "__main__":
    main()
