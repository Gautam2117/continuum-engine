"""Verify and stage a worker package delivered over authenticated file transfer."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.release_gate import CHECKSUM_FILES, verify_checksums
from scripts.worker import adopt_verified_review, digest, spec_file


def import_review(source: Path, spec_path: Path, inbox: Path) -> Path:
    spec_path = spec_file(spec_path)
    spec = json.loads(spec_path.read_text())
    sid = spec["id"]
    spec_hash = digest(spec_path)
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix=".review-", dir=inbox) as temp:
        staging = Path(temp) / sid
        staging.mkdir(mode=0o700)
        for name in CHECKSUM_FILES | {"manifest.json", "checksums.txt"}:
            item = source / name
            if item.is_symlink() or not item.is_file():
                raise ValueError(f"Expected regular review file: {name}")
            shutil.copyfile(item, staging / name)
        verify_checksums(staging)
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(staging / "video.mp4"),
             "-f", "null", "-"],
            timeout=180, check=True,
        )
        details = adopt_verified_review(Path(temp), {"spec_id": sid, "spec_sha256": spec_hash}, spec_path)
        destination = inbox / f"{sid}-{spec_hash}-{details['mp4Sha256']}"
        # Rename within the same filesystem, so operators cannot see half a package.
        try:
            staging.rename(destination)
        except OSError:
            if destination.is_symlink() or not destination.is_dir() or any(
                (destination / name).is_symlink()
                or digest(destination / name) != digest(staging / name)
                for name in CHECKSUM_FILES | {"manifest.json", "checksums.txt"}
            ):
                raise
            verify_checksums(destination)
        return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("spec", type=Path)
    parser.add_argument("inbox", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    print(import_review(args.source, args.spec, args.inbox))
