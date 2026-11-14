"""Replicate exact, verified private render masters to a distinct trusted disk.

No cloud calls, no uploads, and absolutely no deletion. This tool deliberately
refuses the Mac's own disk as its only "backup" in production mode.
"""
from __future__ import annotations

from contextlib import closing

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import tempfile

REQUIRED = {"video.mp4", "thumb.jpg", "pack.json", "spec.json", "probe.json"}
SPEC_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def digest(path: pathlib.Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_package(folder: pathlib.Path, *, expected_id: str | None = None,
                   expected_sha: str | None = None) -> dict:
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Private review folder is absent or a symlink")
    manifest_file = folder / "manifest.json"
    if not manifest_file.is_file() or manifest_file.is_symlink():
        raise ValueError("Missing regular manifest")
    manifest = json.loads(manifest_file.read_text())
    if manifest.get("publicationStatus") != "NOT_APPROVED_FOR_PUBLICATION":
        raise ValueError("Unexpected approval state; archive does not change editorial decisions")
    if not isinstance(manifest.get("id"), str) or not SPEC_ID.fullmatch(manifest["id"]):
        raise ValueError("Invalid spec identity in manifest")
    if not isinstance(manifest.get("specSha256"), str) or not SHA256.fullmatch(manifest["specSha256"]):
        raise ValueError("Invalid source digest in manifest")
    if expected_id and manifest.get("id") != expected_id:
        raise ValueError("Mismatched episode identity")
    if expected_sha and manifest.get("specSha256") != expected_sha:
        raise ValueError("Mismatched source specification digest")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != REQUIRED:
        raise ValueError("Incomplete review manifest")
    if not isinstance(manifest.get("mp4Sha256"), str) or not SHA256.fullmatch(manifest["mp4Sha256"]):
        raise ValueError("Invalid video digest")
    total = 0
    for name in REQUIRED:
        file = folder / name
        if not file.is_file() or file.is_symlink():
            raise ValueError("Review file missing or symlinked: " + name)
        expected = files[name]
        if not isinstance(expected, str) or not SHA256.fullmatch(expected) or digest(file) != expected:
            raise ValueError("Review file checksum mismatch: " + name)
        total += file.stat().st_size
    if files["spec.json"] != manifest["specSha256"]:
        raise ValueError("Source spec checksum differs from review receipt")
    if files["video.mp4"] != manifest["mp4Sha256"]:
        raise ValueError("MP4 checksum differs from review receipt")
    if files["thumb.jpg"] != manifest.get("thumbnailSha256"):
        raise ValueError("Thumbnail checksum differs from review receipt")
    return {"id": manifest["id"], "sourceSha256": manifest["specSha256"], "bytes": total}


def verified_receipts(db: pathlib.Path):
    if not db.is_file():
        raise FileNotFoundError("Private worker database is not configured")
    with closing(sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True, timeout=10)) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT spec_id,spec_sha256,review_path,mp4_sha256 FROM jobs WHERE state='verified' ORDER BY spec_id"):
            if row["review_path"] and row["mp4_sha256"]:
                yield dict(row)


def replicate_one(folder: pathlib.Path, destination: pathlib.Path, *, spec_id: str,
                  spec_sha256: str, expected_video_sha: str | None = None,
                  require_distinct_device: bool = True) -> dict:
    if not SPEC_ID.fullmatch(spec_id) or not SHA256.fullmatch(spec_sha256):
        raise ValueError("Invalid verified worker identity or digest")
    if expected_video_sha is not None and not SHA256.fullmatch(expected_video_sha):
        raise ValueError("Invalid verified worker video checksum")
    original = folder.resolve(strict=True)
    source = verify_package(folder, expected_id=spec_id, expected_sha=spec_sha256)
    if expected_video_sha and digest(original / "video.mp4") != expected_video_sha:
        raise ValueError("Video checksum disagrees with verified worker database")
    archive_root = destination.resolve(strict=True)
    if require_distinct_device and original.stat().st_dev == archive_root.stat().st_dev:
        raise ValueError("Archive must be a distinct mounted filesystem (not the same volume)")
    if archive_root.is_relative_to(original) or original.is_relative_to(archive_root):
        raise ValueError("Archive and source cannot contain each other")
    target = archive_root / f"{spec_id}-{spec_sha256[:12]}"
    if target.exists():
        existing = verify_package(target, expected_id=spec_id, expected_sha=spec_sha256)
        if existing["bytes"] != source["bytes"]:
            raise ValueError("Existing archive differs in byte count")
        return {"status": "already-verified", **existing}
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=".archive-staging-",dir=archive_root))
    try:
        for name in sorted(REQUIRED | {"manifest.json"}):
            with (original / name).open("rb") as reader, (scratch / name).open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
                writer.flush()
                os.fsync(writer.fileno())
        preserved = verify_package(scratch, expected_id=spec_id, expected_sha=spec_sha256)
        if preserved["bytes"] != source["bytes"]:
            raise ValueError("Archive source changed while being copied")
        if verify_package(original, expected_id=spec_id, expected_sha=spec_sha256) != source:
            raise ValueError("Source changed while being archived")
        os.replace(scratch, target)
        fd = os.open(archive_root, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
        return {"status": "archived", **preserved}
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def archive(db: pathlib.Path, reviews: pathlib.Path, destination: pathlib.Path, *,
            require_distinct_device: bool = True) -> dict:
    if not destination.is_dir() or destination.is_symlink():
        raise ValueError("Archive destination must already be a real owned mount")
    if destination.resolve() == reviews.resolve():
        raise ValueError("Source and archive are the same location")
    rows = list(verified_receipts(db))
    report = {"verifiedReceipts": len(rows), "archived": 0, "alreadyVerified": 0,
              "bytes": 0, "errors": [], "sourcePreserved": True}
    root = reviews.resolve(strict=True)
    for row in rows:
        folder = pathlib.Path(row["review_path"])
        # The older worker saved some review paths relative to the Engine repo
        # ("var/reviews/..."). Resolve those relative to the database root,
        # never to an arbitrary shell working directory.
        if not folder.is_absolute():
            repo_root = db.resolve().parent.parent
            folder = repo_root / folder
        try:
            if folder.is_symlink() or not folder.resolve(strict=True).is_relative_to(root):
                raise ValueError("Worker receipt points outside private review storage")
            result = replicate_one(folder,destination, spec_id=row["spec_id"],
                                   spec_sha256=row["spec_sha256"],
                                   expected_video_sha=row["mp4_sha256"],
                                   require_distinct_device=require_distinct_device)
            if result["status"] == "archived":
                report["archived"] += 1
                report["bytes"] += result["bytes"]
            else: report["alreadyVerified"] += 1
        except (ValueError,OSError,KeyError,json.JSONDecodeError) as error:
            report["errors"].append({"id":row["spec_id"],"problem":str(error)[:240]})
    return report


def main():
    from scripts.worker import ROOT
    p=argparse.ArgumentParser(description="Archive private verified masters on a distinct mounted drive without deleting source")
    p.add_argument("--db", type=pathlib.Path,default=ROOT/"var"/"worker.sqlite3")
    p.add_argument("--reviews", type=pathlib.Path,default=ROOT/"var"/"reviews")
    p.add_argument("--destination", type=pathlib.Path, required=True)
    p.add_argument("--confirm-trusted-mount",action="store_true",
                   help="Attest this independent destination is owner-controlled and encrypted at rest")
    a=p.parse_args()
    if not a.confirm_trusted_mount:
        p.error("Confirm an owner-controlled encrypted mount before copying private drafts")
    result=archive(a.db,a.reviews,a.destination)
    print(json.dumps(result,indent=2))
    if result["errors"]: raise SystemExit(2)


if __name__ == "__main__":
    main()
